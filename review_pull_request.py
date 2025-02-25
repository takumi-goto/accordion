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
PR_COMMENT_BODY = os.getenv("PR_COMMENT_BODY")
PR_COMMENT_ID = os.getenv("PR_COMMENT_ID")
PR_COMMENT_USER = os.getenv("PR_COMMENT_USER")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_all_comments():
    """PR のすべてのコメントを取得"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{PR_NUMBER}/comments"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()

    raise Exception(f"Error fetching PR comments: {response.status_code} - {response.text}")

def format_conversation(comments):
    """AI に渡すためのコメント履歴をフォーマット"""
    conversation = []
    for comment in comments:
        user = comment["user"]["login"]
        body = comment["body"]
        conversation.append(f"{user}: {body}")

    return "\n".join(conversation)

def ai_models():
    """AI モデルの設定"""
    return {
        "chatgpt-4o-latest": {
            "model": "chatgpt-4o-latest",
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_token": OPENAI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {OPENAI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": lambda message, context: {
                "model": "chatgpt-4o-latest",
                "messages": [
                    {"role": "system", "content": "あなたはコードレビューを担当する AI です。"},
                    {"role": "user", "content": f"以下の会話履歴を考慮して、最新のメッセージに返信してください:\n\n{context}\n\n【新しいコメント】\n{message}"}
                ]
            }
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "api_url": "https://generativelanguage.googleapis.com/v1/models/gemini:generateText",
            "api_token": GEMINI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {GEMINI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": lambda message, context: {
                "prompt": f"あなたはコードレビューを担当する AI です。\n\n以下の会話履歴を考慮して、最新のメッセージに返信してください:\n\n{context}\n\n【新しいコメント】\n{message}",
                "maxTokens": 1024
            }
        }
    }

def ai_reply(message, context):
    """AI を使用して返信を生成"""
    models = ai_models()
    if AI_MODEL not in models:
        raise ValueError(f"Unknown AI model: {AI_MODEL}")

    model_info = models[AI_MODEL]
    response = requests.post(
        model_info["api_url"],
        headers=model_info["headers"],
        json=model_info["payload"](message, context)
    )

    if response.status_code == 200:
        if AI_MODEL == "chatgpt-4o-latest":
            return response.json()["choices"][0]["message"]["content"]
        elif AI_MODEL == "gemini":
            return response.json()["candidates"][0]["output"]

    raise Exception(f"Error from {AI_MODEL} API: {response.status_code} - {response.text}")

def post_reply():
    """PR のコメントに AI が返信"""
    if not PR_COMMENT_BODY or not PR_COMMENT_ID or not PR_COMMENT_USER:
        print("No new comment detected.")
        return

    # AI のコメントには返信しない
    if "chatgpt" in PR_COMMENT_USER.lower() or "gemini" in PR_COMMENT_USER.lower():
        print(f"Skipping AI comment from {PR_COMMENT_USER}")
        return

    print(f"Replying to {PR_COMMENT_USER}: {PR_COMMENT_BODY}")

    # すべての過去コメントを取得し、コンテキストとして AI に渡す
    comments = fetch_all_comments()
    conversation_context = format_conversation(comments)

    # AI で返信を生成
    reply_text = ai_reply(PR_COMMENT_BODY, conversation_context)

    # GitHub に返信を投稿
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/comments/{PR_COMMENT_ID}/replies"
    data = {"body": reply_text}

    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 201:
        print(f"Replied to {PR_COMMENT_USER}: {reply_text}")
    else:
        print(f"Error posting reply: {response.text}")

if __name__ == "__main__":
    try:
        post_reply()
    except Exception as e:
        print(f"Error: {e}")
