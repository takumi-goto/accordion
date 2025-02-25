import os
import requests
import jwt
import time

# 環境変数から取得
PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY").replace("\\n", "\n")
REPO_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER")
REPO_NAME = os.getenv("GITHUB_REPOSITORY_NAME")
PR_NUMBER = os.getenv("GITHUB_PR_NUMBER")
AI_MODEL = os.getenv("AI_MODEL", "gpt")
OPENAI_API_TOKEN = os.getenv("OPENAI_API_TOKEN")
GEMINI_API_TOKEN = os.getenv("GEMINI_API_TOKEN")
REVIEW_PROMPT = os.getenv("REVIEW_PROMPT", "コードレビューをしてください。")

def generate_jwt():
    """GitHub App の JWT を生成"""
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),  # 10分間有効
        "iss": "123456",  # ← 固定値を使わずに削除してもOK
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

def get_installation_id():
    """指定したリポジトリの Installation ID を取得"""
    jwt_token = generate_jwt()
    headers = {"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github.v3+json"}

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/installation"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()["id"]
    else:
        raise Exception(f"Error fetching Installation ID: {response.text}")

INSTALLATION_ID = get_installation_id()

def get_installation_token():
    """Installation Token を取得（リポジトリ単位）"""
    jwt_token = generate_jwt()
    headers = {"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github.v3+json"}

    url = f"https://api.github.com/app/installations/{INSTALLATION_ID}/access_tokens"
    response = requests.post(url, headers=headers)

    if response.status_code == 201:
        return response.json()["token"]
    else:
        raise Exception(f"Error fetching installation token: {response.text}")

GITHUB_TOKEN = get_installation_token()

def fetch_pr_files():
    """PR の変更部分（diff_hunk）を取得"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{PR_NUMBER}/files"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    raise Exception("Error fetching PR files:", response.text)

if __name__ == "__main__":
    pr_files = fetch_pr_files()
    for file in pr_files:
        print(f"Filename: {file['filename']}")
        print(f"Patch:\n{file['patch']}\n")
