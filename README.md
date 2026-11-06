# cn2kr — 中国信息 → 韩文内容 pipeline

把「中国当下热门/值得买」的一手信息，自动加工成韩国读者能用的韩文内容，发布到 WordPress，最终靠海淘联盟变现。

## 架构

```
[信息源] 百度热搜 / 今日头条热榜 / 什么值得买 RSS
    ↓  抓取（已验证可直接访问）
[LLM] DeepSeek：翻译 + 解读 + 韩文本土化 + SEO 标题
    ↓
[发布] WordPress REST API（默认草稿，人工确认后发）
    ↓
韩国流量 → Temu/AliExpress/Coupang 联盟变现
```

## 快速开始

```bash
# 1. 配置
cp config.example.json config.json
# 编辑 config.json：填 DeepSeek 密钥 + WordPress 地址/账号/应用密码

# 2. 测试（只抓取+生成，不发布）
python pipeline.py --dry-run

# 3. 正式跑（存草稿，人工审核后手动发布）
python pipeline.py

# 4. 直接发布（慎用）
python pipeline.py --publish
```

## 你需要准备的三样东西

1. **DeepSeek API Key** — https://platform.deepseek.com 申请
2. **WordPress 站点** — 域名 + 主机（Cloudways / 韩国主机），装好 WordPress
3. **WordPress 应用密码** — WP 后台 → 用户 → 个人资料 → 应用程序密码，生成一个填进 config.json

## 三个信息源（已验证可用）

| 源 | 地址 | 内容 |
|----|------|------|
| 百度热搜 | `top.baidu.com/api/board` | 中国实时热点 |
| 今日头条热榜 | `toutiao.com/hot-event/hot-board` | 中文热点新闻 |
| 什么值得买 RSS | `post.smzdm.com/feed/` | 好物/好价（海淘金矿）|

## 为什么默认「草稿」而不是「直接发布」

1. 自动生成的内容，人工审核一遍再发，避免翻车（你懂中文，能校验翻译对不对）
2. 你的护城河 = 「真人把关 + 中文一手信息」，这一步不能省

## 下一步（按顺序）

1. 注册 WordPress 站点 + 域名
2. 申请 DeepSeek key
3. 注册联盟：Temu 联盟 / AliExpress 联盟 / Coupang 파트너스
4. 跑通 dry-run，人工改一改 prompt 和标题风格
5. 定第一个细分方向（比如「테무/알리 省钱避坑」），手动写 3~5 篇标杆文章，喂给 AI 当风格参考
