#!/usr/bin/env python3
"""
openclaw-skill-twitter-digest
用法：python run.py --user elonmusk
输出：直接打印总结到 stdout，供 OpenClaw 返回给用户
"""

import os
import sys
import json
import argparse
import requests
from bs4 import BeautifulSoup
import anthropic

# ===== 填写你的 API Key =====
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
# ============================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def resolve_user(query, config):
    """
    把用户的自然语言（"马斯克"、"musk"）映射到 Twitter handle。
    直接传 handle 也可以（如 "elonmusk"）。
    """
    query = query.lower().strip()
    for user in config["tracked_users"]:
        if query == user["handle"].lower():
            return user
        if query in [a.lower() for a in user["aliases"]]:
            return user
    return None


def fetch_tweets(handle, nitter_instances):
    """从 Nitter 抓取指定用户的最新原创推文"""
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    for instance in nitter_instances:
        try:
            url = f"{instance}/{handle}"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            tweets = []

            for item in soup.select(".timeline-item"):
                # 跳过转推
                if item.select_one(".retweet-header"):
                    continue

                time_elem = item.select_one(".tweet-date a")
                if not time_elem:
                    continue
                tweet_time = time_elem.get("title", "")

                content_elem = item.select_one(".tweet-content")
                if not content_elem:
                    continue
                content = content_elem.get_text(strip=True)
                if not content:
                    continue

                href = time_elem.get("href", "")
                link = f"https://twitter.com{href}" if href else ""

                tweets.append({
                    "time": tweet_time,
                    "content": content,
                    "link": link,
                })

            if tweets:
                return tweets, instance

        except Exception:
            continue

    return [], None


def summarize(tweets, display_name):
    """调用 Claude Haiku 总结并翻译"""
    if not tweets:
        return f"⚠️ 抓取失败，所有 Nitter 镜像均无响应。请稍后再试。"

    tweets_text = "\n\n".join([
        f"[{t['time']}]\n{t['content']}"
        for t in tweets
    ])

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""以下是 {display_name} 最近在 Twitter/X 上的发言（按时间倒序，不含转推）：

{tweets_text}

请你：
1. 按话题分类，用简洁中文总结（每类2-3句）
2. 挑出最值得关注的1-3条，附原文和翻译
3. 格式适合直接在聊天里阅读，用 emoji 分类

格式参考：
📅 {display_name} 最新动态

🚀 [话题一]
...

🏛️ [话题二]
...

⭐ 重点
原文："..."
翻译：...
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Twitter digest skill for OpenClaw")
    parser.add_argument("--user", required=True, help="Twitter handle 或别名，如 elonmusk / 马斯克")
    args = parser.parse_args()

    config = load_config()

    # 解析用户
    user_info = resolve_user(args.user, config)
    if not user_info:
        # 如果不在追踪列表里，直接用传入的值当 handle
        user_info = {
            "handle": args.user,
            "display_name": f"@{args.user}",
        }

    handle = user_info["handle"]
    display_name = user_info["display_name"]

    # 抓取
    tweets, source = fetch_tweets(handle, config["nitter_instances"])

    # 总结
    result = summarize(tweets, display_name)
    print(result)


if __name__ == "__main__":
    main()
