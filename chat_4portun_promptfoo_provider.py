import json
import aiohttp
import asyncio
import urllib3
import uuid
import logging
from typing import Optional, List, Dict, Any

# ================= 配置区域 =================
DEFAULT_BASE_URL = "https://prod-ai.4portun.com/ai/api/route/chat/graph"
DEFAULT_TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJjMTIwNTA2Nzk4MDM0MWQ5OTgwN2Y2NDJhYzU5MTE5ZiIsImlhdCI6MTc2NjU0MTUwNSwiZXhwIjoxNzY3MTQ2MzA1fQ.NsVgVISa7aZo_SoSp1B0Z6taxIfG6rXjTbp5Q62mWpU"
DEFAULT_PROXY = None 

# 禁用 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FortunProvider")
# ===========================================

class FortunApiClient:
    """
    支持多轮对话状态保持的客户端
    """
    def __init__(self, base_url: str, auth_token: str, chat_id: str, proxy_url: str = None):
        self.base_url = base_url
        self.headers = {
            "Authorization": auth_token,
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        self.proxy = proxy_url
        self.chat_id = chat_id # 使用传入的固定 ID 保持会话

    async def chat(self, input_str: str) -> str:
        # 如果 prompt 是 JSON 格式（Promptfoo 多轮模式常见），提取最后一条消息的内容
        try:
            prompt_data = json.loads(input_str)
            if isinstance(prompt_data, list):
                input_str = prompt_data[-1].get('content', input_str)
            elif isinstance(prompt_data, dict):
                input_str = prompt_data.get('content', input_str)
        except:
            # 说明是普通字符串，直接使用
            pass

        params = {
            "message": input_str,
            "chatId": self.chat_id,
            "feekback": "false" 
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url, headers=self.headers, params=params, 
                    proxy=self.proxy, ssl=False
                ) as response:
                    response.raise_for_status()
                    
                    full_answer = ""
                    final_answer_from_node = ""
                    
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith("data:"):
                                json_str = line_str[len("data:"):].strip()
                                if not json_str: continue
                                try:
                                    data = json.loads(json_str)
                                    msg_type = data.get("type")
                                    if msg_type == "text":
                                        full_answer += data.get("msg", "")
                                    elif msg_type == "nodeInfo":
                                        node_data = data.get("data", {})
                                        final_answer_from_node = node_data.get("user_intent_stream", "")
                                    elif msg_type == "end":
                                        break
                                except json.JSONDecodeError:
                                    continue
                    
                    return final_answer_from_node if final_answer_from_node else full_answer
                    
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
    
    # --- 核心逻辑：获取或生成会话 ID ---
    # 1. 优先尝试从 context 提取 testCase 的 ID (这能保证同一个测试用例的多轮对话 chatId 一致)
    # 2. 如果没有，则使用 Promptfoo 提供的 vars 里的唯一标识
    # 3. 最后才降级使用随机 ID
    vars = context.get('vars', {})
    session_id = vars.get('uuid') or vars.get('chatId') or context.get('uuid')
    
    if not session_id:
        # 如果是单轮测试且没提供 ID，则生成一个
        session_id = str(uuid.uuid4())
    
    # 打印日志方便调试多轮追踪
    # logger.info(f"Session ID: {session_id} | Prompt length: {len(prompt)}")

    client = FortunApiClient(base_url, token, chat_id=session_id, proxy_url=proxy)

    try:
        output = asyncio.run(client.chat(prompt))
        return {
            "output": output
        }
    except Exception as e:
        return {
            "error": str(e)
        }

# ================= 本地测试代码 =================
if __name__ == "__main__":
    print("正在模拟多轮对话测试...")
    
    # 模拟第一轮
    ctx1 = {"uuid": "test-session-123"}
    res1 = call_api("你好，我是小明", {"config": {}}, ctx1)
    print(f"Round 1: {res1}")

    # 模拟第二轮（使用相同的 uuid）
    res2 = call_api("你还记得我叫什么名字吗？", {"config": {}}, ctx1)
    print(f"Round 2: {res2}")