import asyncio
import aiohttp
import json
import os
from typing import Optional

# --- 配置 ---
# 设置您的API令牌，可以硬编码或从环境变量读取
API_TOKEN = os.getenv("API_TOKEN", "1246g2i2365b4cbc9u40a9fa5ctwa471")
API_URL = "https://llm-fy-legal.fuyuncc.com/aodesai-pulomixiusi-heidee/plux"
MODEL_NAME = "legal_llm"


async def get_llm_response(input_str: str) -> str:
    """
    与目标LLM API进行通信。
    仅处理单轮对话。
    """
    print("--- 正在调用目标模型 ---")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 仅使用当前输入构建对话
    dialogue = [{"role": "user", "content": input_str}]

    payload = {
        "dialogue": dialogue,
        "model": MODEL_NAME,
        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        try:
            print("正在发送请求...")
            async with session.post(API_URL, headers=headers, json=payload) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    print("请求成功！")
                    try:
                        # 尝试解析JSON并提取模型回复
                        result_json = json.loads(response_text)
                        # **重要**: 以下访问路径需要根据实际API返回的JSON结构进行调整
                        # 根据实际API返回的JSON结构，我们知道内容在'content'字段中
                        return result_json['content']
                    except (json.JSONDecodeError, KeyError, IndexError):
                        # 如果解析失败或结构不对，返回原始文本
                        print("无法解析JSON或结构不匹配，返回原始响应。")
                        return response_text
                else:
                    error_message = f"错误: API返回状态码 {response.status}, 消息: {response_text}"
                    print(error_message)
                    return error_message
        except Exception as e:
            error_message = f"错误: 请求失败 - {str(e)}"
            print(error_message)
            return error_message

async def chat_loop():
    """
    主聊天循环。
    """
    print("--- LLM 对话客户端 (单轮模式) ---")
    print('输入 "exit" 或 "quit" 退出程序。')
    
    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if user_input.lower() in ["exit", "quit"]:
            print("再见！")
            break

        if not user_input.strip():
            continue
        
        # 调用LLM
        response_content = await get_llm_response(user_input)
        
        # 打印结果
        print(f"LLM: {response_content}")
        print("-" * 20)

if __name__ == "__main__":
    try:
        asyncio.run(chat_loop())
    except Exception as e:
        print(f"发生未处理的异常: {e}")
