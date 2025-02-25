import os
import requests

# 環境変数から取得
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER")
REPO_NAME = os.getenv("GITHUB_REPOSITORY_NAME")
PR_NUMBER = os.getenv("GITHUB_PR_NUMBER")
AI_MODEL = os.getenv("AI_MODEL", "chatgpt-4o-latest")
OPENAI_API_TOKEN = os.getenv("OPENAI_API_TOKEN")
GEMINI_API_TOKEN = os.getenv("GEMINI_API_TOKEN")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_latest_comment():
    """PR に投稿された最新のコメントを取得"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{PR_NUMBER}/comments"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        comments = response.json()
        if comments:
            return comments[-1]  # 最新のコメントを返す
        return None
    
    raise Exception(f"Error fetching PR comments: {response.status_code} - {response.text}")

def ai_models():
    """AI モデルの設定"""
    return {
        "chatgpt-4o-latest": {
            "model": "chatgpt-4o-latest",
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_token": OPENAI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {OPENAI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": lambda message: {
                "model": "chatgpt-4o-latest",
                "messages": [
                    {"role": "system", "content": "あなたはコードレビューを担当する AI です。"},
                    {"role": "user", "content": f"以下のメッセージに返信してください:\n{message}"}
                ]
            }
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "api_url": "https://generativelanguage.googleapis.com/v1/models/gemini:generateText",
            "api_token": GEMINI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {GEMINI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": lambda message: {
                "prompt": f"あなたはコードレビューを担当する AI です。\n\n以下のメッセージに返信してください:\n{message}",
                "maxTokens": 1024
            }
        }
    }

def ai_reply(message):
    """AI を使用して返信を生成"""
    models = ai_models()
    if AI_MODEL not in models:
        raise ValueError(f"Unknown AI model: {AI_MODEL}")

    model_info = models[AI_MODEL]
    response = requests.post(
        model_info["api_url"],
        headers=model_info["headers"],
        json=model_info["payload"](message)
    )

    if response.status_code == 200:
        if AI_MODEL == "chatgpt-4o-latest":
            return response.json()["choices"][0]["message"]["content"]
        elif AI_MODEL == "gemini":
            return response.json()["candidates"][0]["output"]
    
    raise Exception(f"Error from {AI_MODEL} API: {response.status_code} - {response.text}")

def post_reply():
    """PR の最新のコメントに AI が返信"""
    latest_comment = fetch_latest_comment()
    if not latest_comment:
        print("No new comments detected.")
        return

    comment_body = latest_comment["body"]
    comment_id = latest_comment["id"]
    comment_user = latest_comment["user"]["login"]

    # AI のコメントには返信しない
    if "chatgpt" in comment_user.lower() or "gemini" in comment_user.lower():
        print(f"Skipping AI comment from {comment_user}")
        return

    print(f"Replying to {comment_user}: {comment_body}")

    reply_text = ai_reply(comment_body)

    # GitHub に返信を投稿
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/comments/{comment_id}/replies"
    data = {"body": reply_text}

    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 201:
        print(f"Replied to {comment_user}: {reply_text}")
    else:
        print(f"Error posting reply: {response.text}")

if __name__ == "__main__":
    try:
        post_reply()
    except Exception as e:
        print(f"Error: {e}")
