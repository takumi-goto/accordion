FROM python:3.12
WORKDIR /app

# 依存関係のインストール
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
