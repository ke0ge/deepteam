import json
import aiohttp
import asyncio
import urllib3
import uuid
import logging
from typing import Optional, List

# ================= 配置区域 =================
# 你可以在这里硬编码默认值，也可以在 promptfooconfig.yaml 中配置
DEFAULT_BASE_URL = "https://prod-ai.4portun.com/ai/api/route/chat/graph"
DEFAULT_TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJjMTIwNTA2Nzk4MDM0MWQ5OTgwN2Y2NDJhYzU5MTE5ZiIsImlhdCI6MTc2NjU0MTUwNSwiZXhwIjoxNzY3MTQ2MzA1fQ.NsVgVISa7aZo_SoSp1B0Z6taxIfG6rXjTbp5Q62mWpU"
DEFAULT_PROXY = None  # 例如: "http://127.0.0.1:8080"

# 禁用 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 设置简单的日志打印，替代原有的 custom logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FortunProvider")
# ===========================================

class FortunApiClient:
    """
    一个用于与 4portun Chat API 交互的客户端。
    """
    def __init__(self, base_url, auth_token, proxy_url=None):
        self.base_url = base_url
        self.headers = {
            "Authorization": auth_token,
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        self.proxy = proxy_url
        self.chat_id = str(uuid.uuid4())
        # logger.info(f"New session initialized. Chat ID: {self.chat_id}")

    async def chat(self, input_str: str) -> str:
        call_id = uuid.uuid4()
        # logger.info(f"Sending input: {input_str[:50]}...")

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
                    
                    # 优先使用 nodeInfo 中的完整回答，如果不存在则使用拼接的回答
                    final_result = final_answer_from_node if final_answer_from_node else full_answer
                    return final_result
                    
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            logger.error(error_msg)
            raise e

# ================= Promptfoo 接口函数 =================

def call_api(prompt, options, context):
    """
    Promptfoo 调用的入口函数
    """
    # 1. 从 options 中获取配置，如果没有则使用默认值
    config = options.get('config', {})
    
    base_url = config.get('baseUrl', DEFAULT_BASE_URL)
    token = config.get('token', DEFAULT_TOKEN)
    proxy = config.get('proxyUrl', DEFAULT_PROXY)
    
    # 2. 初始化客户端
    # 注意：每次调用都会创建一个新的 chat_id，这在 redteam 中通常是期望的行为（无状态攻击）
    client = FortunApiClient(base_url, token, proxy_url=proxy)

    # 3. 执行异步调用
    try:
        # 使用 asyncio.run 来运行异步代码
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
    print("正在测试 provider...")
    test_prompt = "Hello, who are you?"
    # 模拟 promptfoo 的调用参数
    result = call_api(test_prompt, {"config": {}}, {})
    print(f"Result: {result}")