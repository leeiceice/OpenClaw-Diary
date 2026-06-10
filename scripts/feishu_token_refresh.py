#!/usr/bin/env python3
"""
飞书 Bot Token 自动刷新脚本
每2小时运行一次，自动刷新 tenant_access_token 并写入 .env
"""
import os, json, urllib.request
from pathlib import Path

APP_ID = "cli_a9544fc759f81cb1"
APP_SECRET = "8JwZHTL66WVOD16Lb9b69gJHh3CCt7Wf"
ENV_FILE = Path("~/.openclaw/.env").expanduser()
LOG_FILE = "/tmp/feishu_token_refresh.log"

def log(msg):
    print(msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(msg + '\n')

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    log("=== 飞书 Token 刷新开始 ===")
    result = get_token()
    if result.get("code") != 0:
        log(f"❌ 获取 Token 失败: {result.get('msg')}")
        return
    
    token = result.get("tenant_access_token", "")
    expire = result.get("expire", 7200)
    
    # 读取现有 .env
    env_content = ""
    if ENV_FILE.exists():
        env_content = ENV_FILE.read_text()
    
    # 更新或添加 FEISHU_BOT_TOKEN
    lines = env_content.split('\n')
    found = False
    new_lines = []
    for line in lines:
        if line.startswith('FEISHU_BOT_TOKEN='):
            new_lines.append(f'FEISHU_BOT_TOKEN={token}')
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f'FEISHU_BOT_TOKEN={token}')
    
    ENV_FILE.write_text('\n'.join(new_lines))
    log(f"✅ Token 已写入 .env (有效期 {expire} 秒)")
    log(f"Token: {token[:20]}...")

if __name__ == "__main__":
    main()