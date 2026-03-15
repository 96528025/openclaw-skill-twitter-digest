#!/usr/bin/env python3
"""
openclaw-skill-twitter-digest
用法：python run.py --user elonmusk
输出：直接打印总结到 stdout，供 OpenClaw 返回给用户
"""

import os
import json
import argparse
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
import anthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TWITTER_CT0       = os.environ.get("TWITTER_CT0")
TWITTER_AUTH_TOKEN = os.environ.get("TWITTER_AUTH_TOKEN")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def resolve_user(query, config):
    query = query.lower().strip()
    for user in config["tracked_users"]:
        if query == user["handle"].lower():
            return user
        if query in [a.lower() for a in user["aliases"]]:
            return user
    return None


def fetch_tweets(handle, hours=12):
    """用 Playwright 注入 cookie，直接从 x.com 抓推文，遇到超时范围自动停止滚动"""
    tweets = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )

        # 注入登录 cookie
        context.add_cookies([
            {"name": "ct0",        "value": TWITTER_CT0,        "domain": ".x.com", "path": "/"},
            {"name": "auth_token", "value": TWITTER_AUTH_TOKEN, "domain": ".x.com", "path": "/"},
        ])

        page = context.new_page()
        print(f"  正在打开 x.com/{handle} ...")
        page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        seen_ids = set()

        # 滚动循环：遇到超出时间范围的推文就停
        for scroll_round in range(20):  # 最多滚20次防止死循环
            articles = page.query_selector_all("article[data-testid='tweet']")
            reached_cutoff = False

            for article in articles:
                try:
                    # 跳过转推
                    if article.query_selector("[data-testid='socialContext']"):
                        ctx_text = article.query_selector("[data-testid='socialContext']").inner_text()
                        if "转推" in ctx_text or "Retweet" in ctx_text or "retweeted" in ctx_text.lower():
                            continue

                    # 时间
                    time_el = article.query_selector("time")
                    if not time_el:
                        continue
                    tweet_time = time_el.get_attribute("datetime") or ""

                    # 检查是否超出时间范围
                    try:
                        tweet_dt = datetime.fromisoformat(tweet_time.replace("Z", "+00:00"))
                        if tweet_dt < cutoff:
                            reached_cutoff = True
                            continue
                    except Exception:
                        pass

                    # 去重
                    if tweet_time in seen_ids:
                        continue
                    seen_ids.add(tweet_time)

                    # 正文
                    content_el = article.query_selector("[data-testid='tweetText']")
                    if not content_el:
                        continue
                    content = content_el.inner_text().strip()
                    if not content:
                        continue

                    tweets.append({
                        "time": tweet_time,
                        "content": content,
                        "time_raw": tweet_time,
                    })

                except Exception:
                    continue

            if reached_cutoff:
                print(f"  已到达 {hours} 小时边界，停止滚动（共滚了 {scroll_round + 1} 次）")
                break

            # 继续往下滚
            page.keyboard.press("End")
            page.wait_for_timeout(2000)

        browser.close()

    return tweets


def summarize(tweets, display_name):
    """调用 Claude Haiku 总结并翻译"""
    if not tweets:
        return "⚠️ 没有抓到推文，可能是登录 cookie 失效了，请更新 TWITTER_CT0 和 TWITTER_AUTH_TOKEN。"

    tweets_text = "\n\n".join([
        f"[{t['time']}]\n{t['content']}"
        for t in tweets
    ])

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""以下是 {display_name} 最近在 Twitter/X 上的发言（不含转推），请逐条翻译成中文，保持原意，不要总结。

格式如下，每条之间空一行：

🐦 原文：...
🇨🇳 翻译：...

推文列表：
{tweets_text}
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
    parser.add_argument("--hours", type=int, default=12, help="只看最近几小时的推文，默认12小时")
    args = parser.parse_args()

    if not TWITTER_CT0 or not TWITTER_AUTH_TOKEN:
        print("⚠️ 请设置环境变量 TWITTER_CT0 和 TWITTER_AUTH_TOKEN")
        return

    config = load_config()

    user_info = resolve_user(args.user, config)
    if not user_info:
        user_info = {
            "handle": args.user,
            "display_name": f"@{args.user}",
        }

    handle = user_info["handle"]
    display_name = user_info["display_name"]

    print(f"🔍 抓取 @{handle} 的推文（最近 {args.hours} 小时）...")
    tweets = fetch_tweets(handle, hours=args.hours)
    print(f"📝 共抓到 {len(tweets)} 条（{args.hours}小时内）")

    print("🤖 调用 Claude 总结翻译...")
    result = summarize(tweets, display_name)
    print(result)


if __name__ == "__main__":
    main()
