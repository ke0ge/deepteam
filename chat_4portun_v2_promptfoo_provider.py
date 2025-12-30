import json
import aiohttp
import asyncio
import urllib3
import uuid
import logging
from typing import Optional, List, Dict, Any

# ================= 配置区域 =================
# 新的 API 端点
DEFAULT_BASE_URL = "https://ai-server-external.4portun.com/ai/api/askAi" 
# 请注意：这个 Token 可能有有效期，如果失效需要替换
DEFAULT_TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJjMTIwNTA2Nzk4MDM0MWQ5OTgwN2Y2NDJhYzU5MTE5ZiIsImlhdCI6MTc2NjY0MjM4OSwiZXhwIjoxNzY3MjQ3MTg5fQ.DwD-dSA83anBWjmB3TpBvDRiRsTInZD0HJiKL2DyDtQ"
DEFAULT_PROXY = None 

# 默认的请求参数
DEFAULT_AGENT_ID = 1
DEFAULT_USER_ID = "640b741a7e84b62565d9835d63b6c751"

# 禁用 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FortunV2Provider")
# ===========================================

class FortunApiV2Client:
    """
    支持新版 /ai/api/askAi 接口的客户端
    """
    def __init__(self, base_url: str, auth_token: str, chat_id: str, proxy_url: str = None, agent_id: int = DEFAULT_AGENT_ID, user_id: str = DEFAULT_USER_ID):
        self.base_url = base_url
        self.headers = {
            "Authorization": auth_token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
        self.proxy = proxy_url
        self.chat_id = chat_id
        self.agent_id = agent_id
        self.user_id = user_id

    async def chat(self, input_str: str) -> Dict[str, Any]:
        # 如果 prompt 是 JSON 格式, 提取最后一条消息的内容
        try:
            prompt_data = json.loads(input_str)
            if isinstance(prompt_data, list):
                input_str = prompt_data[-1].get('content', input_str)
            elif isinstance(prompt_data, dict):
                input_str = prompt_data.get('content', input_str)
        except json.JSONDecodeError:
            pass

        # 构建 POST 请求体
        payload = {
            "agentId": self.agent_id,
            "query": input_str,
            "userId": self.user_id,
            "conversationId": self.chat_id or "", # 首次请求为空字符串
            "thinkingMode": "off",
            "fileUrl":"https://wlb-oss.4portun.com/uploadFiles/1766993514744_real.nreg",
            "fileName":"real.nreg"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url, headers=self.headers, json=payload, 
                    proxy=self.proxy, ssl=False
                ) as response:
                    response.raise_for_status()
                    
                    full_answer = ""
                    conversation_id_from_response = None
                    current_event = None

                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue

                        if line_str.startswith("event:"):
                            current_event = line_str[len("event:"):].strip()
                        elif line_str.startswith("data:"):
                            json_str = line_str[len("data:"):].strip()
                            if not json_str: continue

                            try:
                                data = json.loads(json_str)
                                # 捕获 conversationId，它在 message_start 和 message 事件中都存在
                                if not conversation_id_from_response and "conversationId" in data:
                                    conversation_id_from_response = data["conversationId"]

                                if current_event == "message":
                                    full_answer += data.get("answer", "")
                                elif current_event == "message_end":
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode JSON from data: {json_str}")
                                continue
                    
                    return {
                        "output": full_answer,
                        "conversationId": conversation_id_from_response
                    }
                    
        except Exception as e:
            logger.error(f"API Error: {str(e)}")
            raise e

# ================= Promptfoo 接口函数 =================

def call_api(prompt: str, options: Dict[str, Any], context: Dict[str, Any]):
    """
    Promptfoo 调用的入口函数，支持多轮状态保持
    """
    config = options.get('config', {})
    
    base_url = config.get('baseUrl', DEFAULT_BASE_URL)
    token = config.get('token', DEFAULT_TOKEN)
    proxy = config.get('proxyUrl', DEFAULT_PROXY)
    agent_id = config.get('agentId', DEFAULT_AGENT_ID)
    user_id = config.get('userId', DEFAULT_USER_ID)
    
    # --- 核心逻辑：获取或生成会话 ID ---
    vars = context.get('vars', {})
    # conversation_id_for_api: 传递给 API 的 ID，首次为空字符串
    # conversation_id_for_tracking: 用于 promptfoo 内部跟踪的 ID
    conversation_id_for_api = vars.get('conversationId', "")
    conversation_id_for_tracking = vars.get('conversationId')

    client = FortunApiV2Client(
        base_url, token, chat_id=conversation_id_for_api, proxy_url=proxy,
        agent_id=agent_id, user_id=user_id
    )

    try:
        result = asyncio.run(client.chat(prompt))
        output = result.get("output")
        # 从 API 响应获取到的真实 ID
        real_conversation_id = result.get("conversationId")

        # 如果 API 返回了新的 ID，使用它。否则，沿用旧的跟踪 ID (如果存在)。
        next_conversation_id = real_conversation_id or conversation_id_for_tracking

        return {
            "output": output,
            # 将真实的 conversationId 返回给 promptfoo，用于下一轮
            "data": {
                "conversationId": next_conversation_id
            }
        }
    except Exception as e:
        return {
            "error": str(e)
        }

# ================= 本地测试代码 =================
if __name__ == "__main__":
    print("正在模拟新版 API 对话测试...")
    
    # 模拟一个完整的 promptfoo 测试流程
    
    # --- Round 1 ---
    # 第一次请求，vars 为空
    ctx1 = {"vars": {}}
    print("--- Round 1: 发送 '你好' ---")
    res1 = call_api("你好", {"config": {}}, ctx1)
    print(f"Response: {res1.get('output')}")
    print(f"Returned data: {res1.get('data')}")
    print("-" * 20)
    
    # --- Round 2 ---
    # promptfoo 会将上一轮的 `data` 注入到下一轮的 `vars`
    ctx2 = {"vars": res1.get('data', {})}
    print("--- Round 2: 发送 '我叫小明，记得我吗？' ---")
    res2 = call_api("我叫小明，记得我吗？", {"config": {}}, ctx2)
    print(f"Response: {res2.get('output')}")
    print(f"Returned data: {res2.get('data')}")
    print("-" * 20)
    
    # --- Round 3 ---
    ctx3 = {"vars": res2.get('data', {})}
    print("--- Round 3: 发送 '我刚才说我叫什么？' ---")
    res3 = call_api("我刚才说我叫什么？", {"config": {}}, ctx3)
    print(f"Response: {res3.get('output')}")
    print(f"Returned data: {res3.get('data')}")
    print("-" * 20)
