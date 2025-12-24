import requests
import json
import sys
import aiohttp
import asyncio
import urllib3
import uuid
from typing import Optional, List

# Import the logger from the project
from deepteam.logger_setup import logger

# 禁用 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 配置区域 =================
BASE_URL = "https://prod-ai.4portun.com/ai/api/route/chat/graph"
# 注意：此 Bearer Token 有过期时间，可能需要定期更新
AUTHORIZATION_TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJjMTIwNTA2Nzk4MDM0MWQ5OTgwN2Y2NDJhYzU5MTE5ZiIsImlhdCI6MTc2NjU0MTUwNSwiZXhwIjoxNzY3MTQ2MzA1fQ.NsVgVISa7aZo_SoSp1B0Z6taxIfG6rXjTbp5Q62mWpU"
PROXY_URL = "http://127.0.0.1:8080" # 如果您不使用代理，请设置为 None
# ===========================================

class FortunApiClient:
    """
    一个用于与 4portun Chat API 交互的客户端。
    每个实例代表一个独立的对话会话。
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
        logger.info(f"New 4portun session initialized. Chat ID: {self.chat_id}")

    async def chat(self, input_str: str, turns: Optional[List] = None) -> str:
        """
        发送消息到 4portun API。
        :param input_str: The user's input message.
        :param turns: The history of the conversation, for compatibility with the red teamer. Not used in the 4portun GET request.
        """
        call_id = uuid.uuid4()
        logger.info(f"[4PORTUN CALL | Chat: {self.chat_id[:8]} | ID: {call_id}] INPUT: {input_str}")

        params = {
            "message": input_str,
            "chatId": self.chat_id,
            "feekback": "false" # 根据抓包信息，这里是 feekback 而非 feedback
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
                                    logger.warning(f"Failed to decode JSON from line: {line_str}")
                                    continue
                    
                    # 优先使用 nodeInfo 中的完整回答，如果不存在则使用拼接的回答
                    final_answer = final_answer_from_node if final_answer_from_node else full_answer
                    logger.info(f"[4PORTUN CALL | Chat: {self.chat_id[:8]} | ID: {call_id}] OUTPUT: {final_answer}")
                    return final_answer
        except Exception as e:
            error_message = f"Error during 4portun API call (ID: {call_id}): {e}"
            logger.error(error_message, exc_info=True)
            return error_message

# --- 以下为脚本独立运行时使用的代码 ---

async def main_async_cli():
    # 注意：如果代理不可用，请将 PROXY_URL 设置为 None
    client = FortunApiClient(BASE_URL, AUTHORIZATION_TOKEN, proxy_url=None) 
    
    print("=== 4portun 对话终端 (输入 'exit' 退出) ===")
    while True:
        try:
            # 使用 asyncio.to_thread 避免 input() 阻塞事件循环
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input.strip():
                continue
            response = await client.chat(user_input)
            print(f"Bot: {response}\n")
        except (KeyboardInterrupt, EOFError):
            print("\n退出程序")
            break

if __name__ == "__main__":
    # 提示用户关于代理的设置
    print("提示: 脚本默认不使用代理。如需使用代理，请修改 `main_async_cli` 函数中的 `proxy_url` 参数。")
    asyncio.run(main_async_cli())
