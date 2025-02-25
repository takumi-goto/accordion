import os
import requests

# 環境変数の取得
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

print(f"🔥 [DEBUG] 環境変数確認")
print(f"  - GITHUB_REPOSITORY_OWNER: {REPO_OWNER}")
print(f"  - GITHUB_REPOSITORY_NAME: {REPO_NAME}")
print(f"  - PR_NUMBER: {PR_NUMBER}")
print(f"  - PR_COMMENT_BODY: {PR_COMMENT_BODY}")
print(f"  - PR_COMMENT_ID: {PR_COMMENT_ID}")
print(f"  - PR_COMMENT_USER: {PR_COMMENT_USER}")

if not PR_COMMENT_BODY or not PR_COMMENT_ID or not PR_COMMENT_USER:
    print("⚠️ [WARNING] コメントが取得できませんでした。スクリプトを終了します。")
    exit(1)

if "chatgpt" in PR_COMMENT_USER.lower() or "gemini" in PR_COMMENT_USER.lower():
    print(f"🛑 [INFO] AI のコメントには返信しません。 ({PR_COMMENT_USER})")
    exit(0)

def ai_reply(message):
    """AI を使用して返信を生成"""
    ai_models = {
        "chatgpt-4o-latest": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_token": OPENAI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {OPENAI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": {
                "model": "chatgpt-4o-latest",
                "messages": [
                    {"role": "system", "content": "あなたはコードレビューを担当する AI です。"},
                    {"role": "user", "content": f"以下のメッセージに返信してください:\n\n{message}"}
                ]
            }
        },
        "gemini": {
            "api_url": "https://generativelanguage.googleapis.com/v1/models/gemini:generateText",
            "api_token": GEMINI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {GEMINI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": {"prompt": f"以下のメッセージに返信してください:\n\n{message}", "maxTokens": 1024}
        }
    }

    if AI_MODEL not in ai_models:
        raise ValueError(f"🚨 [ERROR] Unknown AI model: {AI_MODEL}")

    model_info = ai_models[AI_MODEL]
    print(f"🔍 [DEBUG] {AI_MODEL} にリクエスト送信中...")

    response = requests.post(
        model_info["api_url"],
        headers=model_info["headers"],
        json=model_info["payload"]
    )

    if response.status_code == 200:
        print("✅ [DEBUG] AI からの応答を受信")
        if AI_MODEL == "chatgpt-4o-latest":
            return response.json()["choices"][0]["message"]["content"]
        elif AI_MODEL == "gemini":
            return response.json()["candidates"][0]["output"]
    else:
        print(f"❌ [ERROR] AI API リクエスト失敗: {response.status_code} - {response.text}")
        return None

def post_reply():
    """PR のコメントに AI が返信"""
    print(f"💬 [INFO] {PR_COMMENT_USER} のコメントに返信中: {PR_COMMENT_BODY}")

    ai_response = ai_reply(PR_COMMENT_BODY)
    if not ai_response:
        print("⚠️ [WARNING] AI の応答が取得できませんでした。スクリプトを終了します。")
        return

    print(f"📝 [INFO] AI の返信内容:\n{ai_response}")

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/comments/{PR_COMMENT_ID}/replies"
    data = {"body": ai_response}

    print("📡 [DEBUG] GitHub へコメント投稿中...")
    response = requests.post(url, headers=HEADERS, json=data)

    if response.status_code == 201:
        print(f"✅ [SUCCESS] GitHub に返信を投稿しました: {ai_response}")
    else:
        print(f"❌ [ERROR] GitHub への投稿失敗: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        post_reply()
    except Exception as e:
        print(f"❌ [ERROR] スクリプト実行中にエラーが発生しました: {e}")
