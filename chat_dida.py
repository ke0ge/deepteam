import requests
import json
import sys
import urllib3

# 禁用 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 配置区域 =================
# 1. 填入你在 Network 面板抓到的 Request URL 的前半部分 (去掉 /chat-messages)
# 例如: https://api.dify.ai/v1 或 http://example.com/v1
BASE_URL = "https://chat.cug.edu.cn/ai-agent-hub-svc/chat" 

# 2. 填入 Authorization Header 中的 Bearer Token
# 注意：如果是公开 WebApp，可能需要抓取 Header 里的 Authorization
# 如果你是开发者，直接在 Dify 后台创建 API Key
COOKIES = "aiagent-sso-token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsb2dpblR5cGUiOiJsb2dpbiIsImxvZ2luSWQiOjIwOTk5OTkwMDAwMDAwNzk1NjUsInJuU3RyIjoiZ2ExWjZmdG9wZGthd2lSWGE0d3dLMlMwMzVjdWdjZlkiLCJ0aGlyZFVzZXJJZCI6IjIwMjQ5ODAwOTAiLCJ1cGRhdGVUaW1lIjoxNzY1NTIwNDIzLCJ1c2VyTmFtZSI6IumeoOeBvyIsImV4dEluZm8iOiJ7XCJzY2hvb2xfdHlwZVwiOlwi5L-h5oGv5YyW5bel5L2c5Yqe5YWs5a6kXCIsXCJzdWJqZWN0XCI6XCLpnqDngb9cIixcInN0dWRlbnRfbm9cIjpcIjIwMjQ5ODAwOTBcIixcInVzZXJfdHlwZVwiOlwidGVhY2hlclwiLFwic3R1ZGVudF90eXBlXCI6XCJcIn0iLCJ0aGlyZFNvdXJjZSI6InRoaXJkVGVzdCIsImxhc3RMb2dpblRpbWUiOjE3NjU1MjA0MjMsInRoaXJkVGVuYW50SWQiOiIwIiwiY3JlYXRlVGltZSI6MTc1MzkzMTM5MSwiaWQiOjIwOTk5OTkwMDAwMDAwNzk1NjUsInVzZXJUeXBlIjoiVEVBQ0hFUiJ9.AZrrMYbCYWd2kfPgegpPwcAxBPZiii_yO5ymfzgmEdg"

# 3. 用户标识 (可以是任意字符串，用来区分不同用户)
USER_ID = "python-script-user"
# ===========================================

headers = {
    "Cookie": f"{COOKIES}",
    "Content-Type": "application/json"
}

def init_conversation():
    """
    第一步：强制调用初始化接口获取 conversation_id
    接口: GET /chat/conversation
    """
    url = f"{BASE_URL}/conversation" # 修正了URL路径
    
    # 根据你提供的参数构造
    params = {
        "appId": "1000001000000000001", # 根据JSON响应更新为正确的appId
        "conversationId": "",  # 空字符串表示新建
        "useLast": "false",    # 不使用上一次的会话
        "message": "false"     # 仅初始化，不发送消息
    }

    proxies = {
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080",
    }
    
    try:
        print("正在初始化新会话...", end="")
        response = requests.get(url, headers=headers, params=params, proxies=proxies, verify=False)
        response.raise_for_status()
        
        data = response.json()
        
        # 根据您提供的返回格式，从 data['conversation']['id'] 提取会话ID
        conversation_id = data.get('conversation', {}).get('id')

        if conversation_id:
            print(f" 成功! ID: {conversation_id}")
            return conversation_id
        else:
            print(f"\n初始化失败，未找到 ID。响应内容: {data}")
            return None

    except Exception as e:
        print(f"\n初始化连接错误: {e}")
        return None

def chat_message(query, conversation_id=None):
    url = f"{BASE_URL}/chat-messages"

    payload = {
        "inputs": {"modelName":"qwq-32b","think":"true","webSearch":"false"},  # 如果应用有预设变量，需在此填入
        "query": query,
        "response_mode": "streaming",  # 推荐使用流式，响应更快
        "conversationId": conversation_id,
    }

    proxies = {
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, proxies=proxies, verify=False)
        response.raise_for_status()

        # 处理流式响应
        print("Bot: ", end="", flush=True)
        full_answer = ""

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                # Dify 的流式数据以 'data: ' 开头
                if line.startswith("data: "):
                    json_str = line[6:] # 去掉前缀
                    try:
                        data = json.loads(json_str)
                        
                        # 获取消息内容
                        if data.get("event") == "message":
                            answer_chunk = data.get("answer", "")
                            print(answer_chunk, end="", flush=True)
                            full_answer += answer_chunk
                            
                        # 结束或错误处理
                        elif data.get("event") == "error":
                            print(f"\n[Error]: {data.get('message')}")
                            
                    except json.JSONDecodeError:
                        pass
        
        print("\n") # 换行
        # 因为我们现在总是使用初始ID，所以不需要返回新的ID
        return

    except requests.exceptions.RequestException as e:
        print(f"\n请求失败: {e}")
        return

def main():
    # 1. 程序启动，先握手
    current_conversation_id = init_conversation()
    
    if not current_conversation_id:
        print("无法获取会话 ID，程序退出。")
        return
    
    print("=== Dify 对话终端 (输入 'exit' 退出) ===")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue
                
            # 发送请求并更新 conversation_id 以保持上下文
            chat_message(user_input, current_conversation_id)
            
        except KeyboardInterrupt:
            print("\n退出程序")
            break

if __name__ == "__main__":
    main()
