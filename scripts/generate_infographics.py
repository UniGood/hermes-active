#!/usr/bin/env python3
"""Generate 6 infographic images for hermes-active README.zh-CN.md using Seedream 5.0 pro"""

import os
import json
import time
import requests
from pathlib import Path

API_KEY = os.environ.get("ARK_API_KEY", "")
if not API_KEY:
    raise SystemExit("Set ARK_API_KEY environment variable first")
API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
MODEL = "doubao-seedream-5-0-pro-260628"
OUTPUT_DIR = Path("/home/ubuntu/.hermes/hermes-active/docs/images")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGES = [
    {
        "filename": "zh-hero-banner.png",
        "prompt": "一张宽幅现代风格的开源AI项目主视觉横幅，项目名Hermes Active。深靛蓝到紫罗兰的暗色渐变背景，一条发光的心跳脉冲线横贯画面并逐渐演变成对话气泡，背景点缀神经网络星点，扁平化设计风格，主标题Hermes Active用粗体白色无衬线字体，副标题让AI助手拥有主动意识。不要写实照片风，不要文字乱码。",
        "size": "3136x1344",  # 21:9 @ 2K
    },
    {
        "filename": "zh-problem-statement.png",
        "prompt": "一张左右对比的信息图，标题无状态Cron对比持久化意识。左侧冷灰色调：一个机器人在空荡荡的白色房间里醒来，房间标注全新隔离会话，旁边是断裂的链条图标，对话气泡写着你是哪位来着。右侧暖紫青色调：同一个机器人身处温馨房间，四周环绕着过往对话时间线、爱心图标和记忆光球，对话气泡写着我刚才还在想你呢。扁平矢量风格，文字精简。",
        "size": "2816x1584",  # 16:9 @ 2K
    },
    {
        "filename": "zh-architecture.png",
        "prompt": "一张简洁的等距视角系统架构信息图。中央：一个FastAPI后端方盒，内含三个发光的齿轮，分别标注心跳沉思调度器。顶部：一块Vue3 Web控制台面板，用标注JWT REST API的箭头连接。右侧：Hermes Agent方盒网关加LLM，连线标注仅公开API。左侧：一个插件形状的方盒pre llm call钩子，指向后端。底部：两个数据库圆柱体标注state.db只读和active.db读写，外加两朵云图标标注Hindsight记忆和天气API。深色背景、霓虹连接线、扁平风格。",
        "size": "2816x1584",
    },
    {
        "filename": "zh-four-systems.png",
        "prompt": "一张2x2网格信息图展示四个系统。左上主动意识：一颗带脉搏线的心脏和决策仪表。右上被动意识：一个信封接收发光的上下文注入流。左下自由意识：一个冥想中的机器人头部，环绕思维光环，底部有沉淀层。右下定时任务：一个日历时钟和流水线箭头。统一的扁平图标风格，紫青配色，深色背景，文字精简。",
        "size": "2816x1584",
    },
    {
        "filename": "zh-deployment.png",
        "prompt": "一张自托管AI系统的部署拓扑信息图。一个服务器方盒内含四张进程卡片：hermes-active后端端口18720、Hermes Agent网关、Hindsight端口8888和一个插件目录。服务器外：一部手机图标微信飞书用户和一个浏览器图标管理控制台。箭头展示消息流向和HTTP调用。深色蓝图风格、霓虹连接线、文字精简。",
        "size": "2816x1584",
    },
    {
        "filename": "zh-footer-banner.png",
        "prompt": "一条极简的开源README页脚缎带：一条细渐变线靛蓝到青色，中央有一个小小的心跳脉冲，配优雅的小号无衬线文字Hermes Active为Hermes Agent社区用心构建，深色背景。",
        "size": "2048x512",  # 4:1
    },
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

for i, img in enumerate(IMAGES):
    print(f"\n[{i+1}/{len(IMAGES)}] Generating: {img['filename']} ({img['size']})")
    payload = {
        "model": MODEL,
        "prompt": img["prompt"],
        "size": img["size"],
        "response_format": "url",
        "watermark": False,
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            print(f"  ERROR: {data['error']}")
            continue

        if data.get("data") and len(data["data"]) > 0:
            url = data["data"][0].get("url", "")
            if url:
                dl = requests.get(url, timeout=60)
                dl.raise_for_status()
                out_path = OUTPUT_DIR / img["filename"]
                out_path.write_bytes(dl.content)
                size_kb = len(dl.content) / 1024
                print(f"  ✓ Saved: {out_path} ({size_kb:.0f} KB)")
                if "usage" in data:
                    u = data["usage"]
                    print(f"  Tokens: {u.get('total_tokens', '?')}, Generated: {u.get('generated_images', '?')}")
            else:
                print(f"  No URL in response: {json.dumps(data, ensure_ascii=False)[:300]}")
        else:
            print(f"  Unexpected response: {json.dumps(data, ensure_ascii=False)[:300]}")

    except requests.exceptions.HTTPError as e:
        print(f"  HTTP Error: {e}")
        print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # Rate limit: wait between requests
    if i < len(IMAGES) - 1:
        print("  Waiting 3s...")
        time.sleep(3)

print("\nDone!")
