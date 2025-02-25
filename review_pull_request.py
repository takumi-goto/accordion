import os
import requests
import time

# 環境変数から取得
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER")
REPO_NAME = os.getenv("GITHUB_REPOSITORY_NAME")
PR_NUMBER = os.getenv("GITHUB_PR_NUMBER")
AI_MODEL = os.getenv("AI_MODEL", "chatgpt-4o-latest")
OPENAI_API_TOKEN = os.getenv("OPENAI_API_TOKEN")
GEMINI_API_TOKEN = os.getenv("GEMINI_API_TOKEN")
REVIEW_PROMPT = os.getenv("REVIEW_PROMPT", "コードレビューをしてください。")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_pr_comments():
    """PR に投稿されたコメントを取得"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{PR_NUMBER}/comments"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()

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

def reply_to_comments():
    """PR の AI コメントに対する返信を監視し、AI も返信する"""
    processed_comments = set()  # 既に返信したコメントを管理

    while True:
        try:
            comments = fetch_pr_comments()

            for comment in comments:
                comment_id = comment["id"]
                comment_body = comment["body"]
                user = comment["user"]["login"]

                # AI のコメントかどうかを判定（適当なフラグを追加できる）
                if "chatgpt" in user.lower() or "gemini" in user.lower():
                    continue  # AI のコメントには返信しない

                # すでに処理済みならスキップ
                if comment_id in processed_comments:
                    continue

                print(f"Replying to: {comment_body}")

                # AI で返信を生成
                reply_text = ai_reply(comment_body)

                # GitHub に返信を投稿
                url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/comments/{comment_id}/replies"
                data = {"body": reply_text}

                response = requests.post(url, headers=HEADERS, json=data)
                if response.status_code == 201:
                    print(f"Replied: {reply_text}")
                    processed_comments.add(comment_id)
                else:
                    print(f"Error posting reply: {response.text}")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(30)  # 30秒ごとにチェック

if __name__ == "__main__":
    try:
        # PR のコメントを監視して AI が返信
        reply_to_comments()

    except Exception as e:
        print(f"Error: {e}")
