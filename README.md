# openclaw-skill-twitter-digest

OpenClaw skill：实时抓取 Twitter/X 用户的最新推文，逐条翻译成中文。

## 触发方式

对 OpenClaw 说：
- "今天马斯克说了啥"
- "帮我看看 musk 最近发了什么"
- "elon musk twitter"

## 使用方法

```bash
python run.py --user elonmusk              # 默认12小时，不含转推
python run.py --user elonmusk --hours 24   # 过去24小时
python run.py --user elonmusk --retweets   # 包含转推
python run.py --user 马斯克                # 别名也支持
```

## 安装

```bash
pip install playwright anthropic
playwright install chromium
sudo apt-get install -y libatk1.0-0t64 libatspi2.0-0t64 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0
```

## 配置（环境变量）

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export TWITTER_CT0="..."        # 从浏览器 x.com 的 Cookie 里取
export TWITTER_AUTH_TOKEN="..." # 从浏览器 x.com 的 Cookie 里取
```

Cookie 获取方法：浏览器打开 x.com → 开发者工具（F12）→ Application → Cookies → 找 `ct0` 和 `auth_token`。

> ⚠️ Cookie 会过期，需要定期更新。

## 添加追踪对象

编辑 `config.json`，在 `tracked_users` 里加一个条目：

```json
{
  "handle": "sama",
  "display_name": "Sam Altman",
  "aliases": ["奥特曼", "sam altman", "sama"]
}
```

## 技术说明

- 用 **Playwright** 模拟真实 Chromium 浏览器，注入 Cookie 登录，直接抓取 x.com
- **智能滚动**：发现超出时间范围的推文自动停止，不浪费时间
- 逐条输出原文 + 中文翻译，用 **Claude Haiku** 翻译（省钱且速度快）
- 支持 `--retweets` 参数选择是否包含转推

---

## 项目复盘

### 最初目标
每天自动抓取 Elon Musk 的 Twitter，总结翻译成中文，发到 Telegram。

### 方向变化：定时推送 → OpenClaw Skill
最初设计成每天晚上8点 cron job 自动跑、发 Telegram。后来发现做成 OpenClaw skill 更自然——你问小龙虾"马斯克今天说了啥"它马上回答，按需触发。

### 三次技术失败

**失败一：Nitter**
- 方案：用 Nitter（Twitter 的开源免费镜像）抓推文
- 问题：所有实例返回 `000`，连接失败
- 原因：Twitter/X 持续封锁 Nitter，基本全军覆没
- 结论：放弃 Nitter

**失败二：twscrape**
- 方案：用 `twscrape` 库，通过浏览器 Cookie 登录抓取
- 问题：`Failed to parse scripts`，无法解析 Twitter 当前的 JS 结构
- 原因：twscrape 和当前版本 Twitter 不兼容
- 结论：放弃 twscrape

**失败三：系统依赖缺失**
- 方案：换成 Playwright 直接模拟浏览器
- 问题：树莓派缺少浏览器运行库
- 解决：`sudo apt-get install` 装依赖，搞定

### 功能迭代

| 版本 | 改动 |
|------|------|
| v1 | 基础抓取，固定等待4秒 |
| v2 | 加滚动加载（固定滚5次） |
| v3 | 智能滚动：看到超出时间范围的推文自动停止 |
| v4 | 输出改为逐条翻译（原文 + 中文），不再总结 |
| v5 | 加 `--retweets` 参数，可选是否包含转推 |

### 核心经验
1. Twitter 是个封闭生态，免费工具随时可能失效，需要有备用方案
2. Playwright 模拟真实浏览器是目前最稳的方式
3. Cookie 会过期，是这个方案最大的软肋，需要定期更新
