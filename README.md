# openclaw-skill-twitter-digest

OpenClaw skill：实时抓取 Twitter/X 用户的最新推文，用 Claude 总结翻译成中文。

## 触发方式

对 OpenClaw 说：
- "今天马斯克说了啥"
- "帮我看看 musk 最近发了什么"
- "elon musk twitter"

## 使用方法

```bash
python run.py --user elonmusk
python run.py --user 马斯克      # 别名也支持
```

## 添加更多追踪对象

编辑 `config.json`，在 `tracked_users` 里加一个条目：

```json
{
  "handle": "sama",
  "display_name": "Sam Altman",
  "aliases": ["奥特曼", "sam altman", "sama"]
}
```

## 安装依赖

```bash
pip3 install requests beautifulsoup4 anthropic
```

## 配置

在 `run.py` 顶部填写：
```python
ANTHROPIC_API_KEY = "YOUR_API_KEY_HERE"
```
或设置环境变量 `ANTHROPIC_API_KEY`。

## 技术说明

- 通过 **Nitter**（Twitter 开源镜像）抓取，无需 Twitter API
- 自动跳过转推，只看原创内容
- 多个 Nitter 实例自动备用，一个挂了换下一个
- 用 **Claude Haiku** 总结翻译（省钱且速度快）
