import os
import requests

# 環境変数から取得
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # 🔥 `GITHUB_PRIVATE_KEY` なしで認証
REPO_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER")
REPO_NAME = os.getenv("GITHUB_REPOSITORY_NAME")
PR_NUMBER = os.getenv("GITHUB_PR_NUMBER")
AI_MODEL = os.getenv("AI_MODEL", "chatgpt-4o-latest")  # 🔥 デフォルトを ChatGPT-4o に
OPENAI_API_TOKEN = os.getenv("OPENAI_API_TOKEN")
GEMINI_API_TOKEN = os.getenv("GEMINI_API_TOKEN")
REVIEW_PROMPT = os.getenv("REVIEW_PROMPT", "コードレビューをしてください。")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_pr_files():
    """PR の変更部分（diff_hunk）を取得"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/files"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()

    raise Exception(f"Error fetching PR files: {response.status_code} - {response.text}")

def ai_models():
    """AI モデルの設定"""
    return {
        "chatgpt-4o-latest": {
            "model": "chatgpt-4o-latest",
            "api_url": "https://api.openai.com/v1/chat/completions",
            "api_token": OPENAI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {OPENAI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": lambda diff_hunk: {
                "model": "chatgpt-4o-latest",
                "messages": [
                    {"role": "system", "content": REVIEW_PROMPT},
                    {"role": "user", "content": f"以下のコード変更をレビューしてください:\n{diff_hunk}"}
                ]
            }
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "api_url": "https://generativelanguage.googleapis.com/v1/models/gemini:generateText",
            "api_token": GEMINI_API_TOKEN,
            "headers": {"Authorization": f"Bearer {GEMINI_API_TOKEN}", "Content-Type": "application/json"},
            "payload": lambda diff_hunk: {
                "prompt": f"{REVIEW_PROMPT}\n\n変更されたコード:\n{diff_hunk}",
                "maxTokens": 1024
            }
        }
    }

def review_code_with_ai(diff_hunk):
    """AI を使用してコードレビューを実行"""
    models = ai_models()
    if AI_MODEL not in models:
        raise ValueError(f"Unknown AI model: {AI_MODEL}")

    model_info = models[AI_MODEL]
    response = requests.post(
        model_info["api_url"],
        headers=model_info["headers"],
        json=model_info["payload"](diff_hunk)
    )

    if response.status_code == 200:
        if AI_MODEL == "chatgpt-4o-latest":
            return response.json()["choices"][0]["message"]["content"]
        elif AI_MODEL == "gemini":
            return response.json()["candidates"][0]["output"]
    
    raise Exception(f"Error from {AI_MODEL} API: {response.status_code} - {response.text}")

def post_review_comment(filename, diff_hunk, review_text):
    """GitHub PR にレビューコメントを投稿"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/comments"

    position = count_hunk_lines(diff_hunk)  # diff_hunk 内の変更行数を基に位置を決定

    data = {
        "body": review_text,
        "commit_id": get_latest_commit_id(),
        "path": filename,
        "position": position
    }

    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code != 201:
        raise Exception(f"Error posting review comment: {response.text}")

def get_latest_commit_id():
    """PR の最新の commit ID を取得"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/commits"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        commits = response.json()
        return commits[-1]["sha"]  # 最新のコミット SHA
    else:
        raise Exception("Error fetching latest commit ID:", response.text)

def count_hunk_lines(diff_hunk):
    """diff_hunk から変更行数をカウントし、インラインコメントの位置を決定"""
    lines = diff_hunk.split("\n")
    return sum(1 for line in lines if line.startswith("+")) // 2  # 変更の中央あたり

if __name__ == "__main__":
    try:
        pr_files = fetch_pr_files()
        for file in pr_files:
            filename = file["filename"]
            diff_hunk = file["patch"]

            print(f"Reviewing {filename} using {AI_MODEL}")
            review_text = review_code_with_ai(diff_hunk)

            print("Review Generated:")
            print(review_text)

            post_review_comment(filename, diff_hunk, review_text)

    except Exception as e:
        print(f"Error: {e}")
