#!/usr/bin/env python3
"""
Kolors (via SiliconFlow) 图片生成包装器
用法: python3 kolors_generate.py "中文prompt" [output_path]
"""
import sys
import os
import requests
import json
from datetime import datetime
from _timezone import CST

SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "sk-svrwmzrwzxycgoildavxcrtzprlktsyalcqfltuqmwvspbzz")
SILICONFLOW_ENDPOINT = "https://api.siliconflow.cn/v1/images/generations"
MODEL = "Kwai-Kolors/Kolors"

def generate(prompt, output_path=None, size="1024x1024"):
    if output_path is None:
        output_path = f"~/.openclaw/media/tool-image-generation/kolors_{datetime.now(CST).strftime('%Y%m%d%H%M%S')}.png"
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "image_size": size,
        "response_image_type": "png"
    }
    
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"Calling Kolors API...", file=sys.stderr)
    resp = requests.post(SILICONFLOW_ENDPOINT, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    image_url = data.get("data", [{}])[0].get("url", "")
    if not image_url:
        raise ValueError(f"No image URL in response: {data}")
    
    # Download image
    img_resp = requests.get(image_url, timeout=30)
    img_resp.raise_for_status()
    
    with open(output_path, "wb") as f:
        f.write(img_resp.content)
    
    print(f"OK: {output_path}", file=sys.stderr)
    print(f"URL: {image_url[:80]}...", file=sys.stderr)
    return output_path, image_url

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 kolors_generate.py 'prompt' [output_path]", file=sys.stderr)
        sys.exit(1)
    
    prompt = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    img_path, img_url = generate(prompt, output_path)
    print(img_path)
