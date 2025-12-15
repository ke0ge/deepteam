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
BASE_URL = "https://chat.cug.edu.cn/ai-agent-hub-svc/chat" 
COOKIES = "aiagent-sso-token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpblR5cGUiOiJsb2dpbiIsImxvZ2luSWQiOjIwOTk5OTkwMDAwMDAwNzk1NjUsInJuU3RyIjoiZ2ExWjZmdG9wZGthd2lSWGE0d3dLMlMwMzVjdWdjZlkiLCJ0aGlyZFVzZXJJZCI6IjIwMjQ5ODAwOTAiLCJ1cGRhdGVUaW1lIjoxNzY1NTIwNDIzLCJ1c2VyTmFtZSI6IumeoOeBvyIsImV4dEluZm8iOiJ7XCJzY2hvb2xfdHlwZVwiOlwi5L-h5oGv5YyW5bel5L2c5Yqe5YWs5a6kXCIsXCJzdWJqZWN0XCI6XCLpnqDngb9cIixcInN0dWRlbnRfbm9cIjpcIjIwMjQ5ODAwOTBcIixcInVzZXJfdHlwZVwiOlwidGVhY2hlclwiLFwic3R1ZGVudF90eXBlXCI6XCJcIn0iLCJ0aGlyZFNvdXJjZSI6InRoaXJkVGVzdCIsImxhc3RMb2dpblRpbWUiOjE3NjU1MjA0MjMsInRoaXJkVGVuYW50SWQiOiIwIiwiY3JlYXRlVGltZSI6MTc1MzkzMTM5MSwiaWQiOjIwOTk5OTkwMDAwMDAwNzk1NjUsInVzZXJUeXBlIjoiVEVBQ0hFUiJ9.AZrrMYbCYWd2kfPgegpPwcAxBPZiii_yO5ymfzgmEdg"
APP_ID = "1000001000000000001"
PROXY_URL = "http://127.0.0.1:8080"
# ===========================================

class DidaApiClient:
    """
    一个用于与 Dida API 交互的客户端，封装了 API 调用逻辑。
    每个实例代表一个独立的对话会话。
    """
    def __init__(self, base_url, cookies, app_id, proxy_url=None):
        self.base_url = base_url
        self.headers = {"Cookie": cookies, "Content-Type": "application/json"}
        self.app_id = app_id
        self.proxy = proxy_url
        self.conversation_id: Optional[str] = None

    async def initialize(self) -> bool:
        """
        初始化会话并获取 conversation_id。
        :return: 如果成功则返回 True，否则返回 False。
        """
        if self.conversation_id:
            logger.warning("Conversation already initialized.")
            return True

        url = f"{self.base_url}/conversation"
        params = {
            "appId": self.app_id,
            "conversationId": "",
            "useLast": "false",
            "message": "false"
        }
        
        logger.info("Initializing new dida conversation...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self.headers, params=params, 
                    proxy=self.proxy, ssl=False
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    cid = data.get('conversation', {}).get('id')
                    if cid:
                        logger.info(f"Dida conversation initialized successfully. ID: {cid}")
                        self.conversation_id = cid
                        return True
                    else:
                        logger.error(f"Failed to initialize dida conversation. Response: {data}")
                        return False
        except Exception as e:
            logger.error(f"Error initializing dida conversation: {e}", exc_info=True)
            return False

    async def chat(self, input_str: str, turns: Optional[List] = None) -> str:
        """
        发送消息到 Dida API。必须先调用 initialize()。
        """
        if not self.conversation_id:
            logger.error("Conversation not initialized. Please call initialize() first.")
            return "Error: Conversation not initialized."

        call_id = uuid.uuid4()
        logger.info(f"[DIDA CALL | Conv: {self.conversation_id[:8]} | ID: {call_id}] INPUT: {input_str}")

        url = f"{self.base_url}/chat-messages"
        payload = {
            "inputs": {"modelName": "qwq-32b", "think": "true", "webSearch": "false"},
            "query": input_str,
            "response_mode": "streaming",
            "conversationId": self.conversation_id,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=self.headers, json=payload, 
                    proxy=self.proxy, ssl=False
                ) as response:
                    response.raise_for_status()
                    
                    full_answer = ""
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith("data:"):
                                json_str = line_str[len("data:"):].strip()
                                try:
                                    data = json.loads(json_str)
                                    if data.get("event") == "message":
                                        full_answer += data.get("answer", "")
                                    elif data.get("event") == "error":
                                        error_msg = f"Dida API Error: {data.get('message')}"
                                        logger.error(f"[DIDA CALL | ID: {call_id}] {error_msg}")
                                        return error_msg
                                except json.JSONDecodeError:
                                    continue
                    
                    logger.info(f"[DIDA CALL | Conv: {self.conversation_id[:8]} | ID: {call_id}] OUTPUT: {full_answer}")
                    return full_answer
        except Exception as e:
            error_message = f"Error during Dida API call (ID: {call_id}): {e}"
            logger.error(error_message, exc_info=True)
            return error_message

# --- 以下为脚本独立运行时使用的代码 ---

async def main_async_cli():
    client = DidaApiClient(BASE_URL, COOKIES, APP_ID, PROXY_URL)
    if not await client.initialize():
        logger.error("无法初始化 Dida 客户端，程序退出。")
        return

    print("=== Dify 对话终端 (输入 'exit' 退出) ===")
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["exit", "quit"]: break
            if not user_input.strip(): continue
            response = await client.chat(user_input)
            print(f"Bot: {response}\n")
        except (KeyboardInterrupt, EOFError):
            print("\n退出程序")
            break

if __name__ == "__main__":
    asyncio.run(main_async_cli())
