<div align="center">

<img src="assets/banner.svg" alt="她不一样.Skill" width="860" />

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-0078d4.svg?style=flat-square)]()
[![WeChat](https://img.shields.io/badge/WeChat-4.0%2B-07c160.svg?style=flat-square)]()
[![QQ](https://img.shields.io/badge/QQ-NapCat%20%2B%20QCE-12b7f5.svg?style=flat-square)](https://github.com/shuakami/qq-chat-exporter)
[![Agent Skill](https://img.shields.io/badge/Universal-Agent%20Skill-d97706.svg?style=flat-square)](https://github.com/863401402/she-love-me)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-✓-d97706.svg?style=flat-square)](https://claude.ai/code)
[![Codex](https://img.shields.io/badge/Codex-✓-111111.svg?style=flat-square)](https://developers.openai.com/codex/overview)
[![Cursor](https://img.shields.io/badge/Cursor-✓-000000.svg?style=flat-square)](https://cursor.sh)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/863401402/she-love-me/pulls)

[快速开始](#快速开始) · [功能特性](#功能特性) · [工作原理](#工作原理) · [致谢](#致谢)

</div>

---

## 简介

**她不一样** 是一个**通用 Agent Skill**，支持 Claude Code、Codex、Cursor、GitHub Copilot、Gemini CLI 等主流 AI 编程工具。

只需要一句调用指令（例如 Claude 里输入 `/she-love-me`，Codex 里输入 `$she-love-me`），它就能自动解密你的微信数据库（或通过 QCE 提取 QQ 记录）、分析你和某个联系人的全部聊天记录，帮你看清：**她是不是真的不一样——这段感情里，你们到底是什么关系？**

融入专业心理学框架（依恋类型 · Gottman · Sternberg 三角），支持**危险信号预警**、**军师建议**、**👴 祖师爷寄语**，全程本地运行，数据不上传任何服务器。

---

## 交流群

<div align="center">

<img src="https://raw.githubusercontent.com/863401402/she-love-me/main/assets/jiaoliuqun.jpg" width="220" alt="微信交流群" />

*扫码加入微信交流群，遇到问题、分享鉴定结果、更新优化方向都可以聊*

</div>

---

## 输出效果

> *(首次运行后，在 `reports/` 目录用浏览器打开 HTML 报告)*

### 分析指数

```
🔥 主动指数   73 ████████░░  你发起对话 72%，偶尔连轰 767 次
💜 被爱指数   66 ███████░░░  她凌晨 3 点发了 8 条消息说想你
🧊 冷淡指数   28 ███░░░░░░░  回复速度 8 分钟，态度还行
```

### 报告截图

| 成分表 | 数据面板 | 趋势图表 |
|:---:|:---:|:---:|
| ![成分表](assets/preview-ingredients.png) | ![数据](assets/preview-stats.png) | ![图表](assets/preview-charts.png) |

| 最终鉴定结果 |
|:---:|
| ![鉴定结果](assets/result.png) |

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🔓 **自动解密** | 自动 clone 并调用 wechat-decrypt，无需手动操作 |
| 👥 **联系人选择** | 按消息数量排列，选你想分析的那个人 |
| 📊 **主动指数** | 主动发起占比 · 连续轰炸次数 · 回复速度差 · 消息长度比 |
| 💜 **被爱指数** | 对方主动次数 · 晚安/早安分析 · 关心频率 |
| 🧊 **冷淡检测** | "嗯""哦""好" 占比 · 长时间已读不回统计 |
| 📊 **话语权分析** | 谁在主导对话，谁在迎合；权力动态量化 |
| 📈 **趋势图表** | 每日消息量 · 活跃时段 · 双方占比（Chart.js） |
| 🧠 **依恋类型诊断** | 安全型 / 焦虑型 / 回避型 / 恐惧型，双方都分析 |
| 🔄 **追逃循环复盘** | 还原完整"案发现场"：触发→撤退→升级→恶化 |
| 💘 **Sternberg 三角** | 激情 · 亲密 · 承诺三维评分，判断爱情类型 |
| 🩹 **修复尝试分析** | 冷战后谁低头？对方接受还是继续惩罚？ |
| 💡 **情感可得性评估** | 对方此刻是否真的有能力投入这段关系 |
| ⚠️ **危险预警** | 7 类信号（煤气灯 · 爱情轰炸 · 间歇性强化 · 单相思痴迷等）· **双阈值触发**（量化+文本同时满足才高亮，否则降级为观察提示） |
| 🎯 **军师模式** | 核心诊断 + 停止/开始建议（含时机）+ 路线图 + **止损红线** |
| 👴 **祖师爷寄语** | 童锦程视角 · 读局 + 推进关系三条实招 + 关系地位指南 + 金句收尾 |
| 🔍 **AI 深度鉴定** | 全量统计层（stats.json）+ 用户选定范围分层采样，三层架构避免"全量幻觉"，评分有推导来源不靠模型主观拍板 |
| 🎯 **动态采样选择** | 自动推荐分析时间范围（1个月/3个月/半年/全量），展示每个选项的消息条数，由用户决定分析窗口 |
| 📄 **双格式输出** | 终端 Markdown 摘要 + 可分享的 HTML 报告 |

---

## 快速开始

### 前置条件

**微信分析**：
- Windows / macOS + WeChat 4.0+（**必须处于登录运行状态**）
- Windows 需要使用**管理员终端**
- macOS 请确保终端具备必要系统权限，并按上游解密器提示授权

**QQ 分析**：
- 安装并启动 [QQ Chat Exporter (QCE)](https://github.com/shuakami/qq-chat-exporter)（NapCat + QCE 插件）
- 用手机 QQ 扫码登录，获取控制台显示的 Access Token

### 安装与运行

```bash
git clone https://github.com/863401402/she-love-me
cd she-love-me
```

| 工具 | 调用方式 |
|------|----------|
| [Claude Code](https://claude.ai/code) / [OpenClaw](https://openclaw.ai) / [Cursor](https://cursor.sh) / [Copilot](https://github.com/features/copilot) / [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `/she-love-me` |
| [Codex](https://developers.openai.com/codex/overview) | `$she-love-me` 或直接说"使用 she-love-me 分析聊天记录" |

**就这些。** Skill 会先询问平台（微信 / QQ），然后自动处理一切——解密、提取、分析、生成报告。

---

## 工作原理

```
WeChat（运行中）/ NapCat + QCE（QQ）
    │
    │  微信：内存扫描提取密钥 → wechat-decrypt 解密数据库
    │  QQ：REST API 导出聊天记录
    ▼
标准 SQLite / JSON 消息数据
    │
    ├─► stats_analyzer.py → stats.json（全量统计：主动性/回复速度/语言学特征）
    │
    ├─► build_chat_history.py（用户动态选择分析范围）
    │       → chat_history.txt（分层采样：起源窗口 / 高冲突区间 / 近30天 / 修复时刻）
    ▼
AI Agent 深度分析（全量统计 + 分层采样关键窗口）
    │  Sternberg 三角（信号计数推导）· Gottman 正负比（词典+文本校正）
    │  对称性评分（stats.json 字段加权）· 双阈值危险预警
    │  依恋类型 · 核心恐惧 · 防御机制 · 军师建议 · 👴 祖师爷寄语
    ▼
HTML 报告（暗色现代风格）+ Markdown 摘要
```

> 微信解密完全依赖 [ylytdeng/wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt)，QQ 导出依赖 [shuakami/qq-chat-exporter](https://github.com/shuakami/qq-chat-exporter)，本项目不包含任何解密代码。

---

## 项目结构

```
she-love-me/
├── .agents/skills/she-love-me/
│   ├── SKILL.md                               # 唯一 Skill 入口（所有工具共用）
│   ├── agents/openai.yaml
│   └── references/                            # 知识库（SKILL.md 按需读取）
│       ├── analysis-framework.md              # 心理学分析框架（模块 F / A / B）
│       ├── risk-signals.md                    # 危险预警 7 类信号 + 双阈值触发规则
│       ├── strategist-guide.md                # 军师 / 童锦程寄语 / 语气风格
│       ├── report-schema.md                   # analysis.json 结构 + 评分推导规则
│       └── report-template.md                 # Step 9 Markdown 展示模板
├── .claude/settings.json                      # Claude Code Skill 路径注册
├── references/tong-jincheng/                  # 祖师爷心智模型参考材料
├── scripts/
│   ├── setup_check.py                         # 环境检查 / 依赖准备
│   ├── decrypt_wechat.py                      # 微信解密入口
│   ├── list_contacts.py / list_contacts_qq.py
│   ├── extract_messages.py / extract_messages_qq.py
│   ├── stats_analyzer.py                      # 全量统计分析引擎
│   ├── build_chat_history.py                  # 分层采样：动态范围选择 + 关键窗口提取
│   └── generate_html_report.py                # HTML 报告生成（微信/QQ 共用）
├── vendor/                                    # wechat-decrypt（gitignore）
├── data/                                      # 分析中间数据（gitignore）
└── reports/                                   # 生成的 HTML 报告（gitignore）
```

---

## 支持平台

| 平台 | 微信 | QQ | 备注 |
|------|------|-----|------|
| Windows | ✅ 支持 | ✅ 支持 | 微信需要管理员终端；QQ 无需管理员 |
| macOS | 🧪 实验性 | ✅ 支持 | 微信依赖上游 wechat-decrypt 与本机权限配置 |
| Linux | 🔜 规划中 | ✅ 支持 | QQ 通过 Docker NapCat 部署可用 |

---

## 版本规划

- **v1.0**：文字消息分析 · HTML 报告 · 主动/被爱/冷淡指数
- **v2.0**：依恋类型诊断 · Sternberg 三角 · Gottman 四骑士 · 危险预警 · 军师模式
- **v2.1**：核心恐惧分析 · 情感可得性评估 · 权力动态量化 · 修复尝试分析 · 追逃循环复盘 · 止损红线
- **v2.2**：**QQ 聊天记录支持**（通过 QQ Chat Exporter API）· 微信/QQ 统一分析管线
- **v2.3**：👴 **祖师爷寄语**（童锦程视角）· 推进关系三条实招 · 关系地位指南
- **v3.0**：🔄 **品牌重构**「她不一样」· 叙事框架升级 · 分析模块微调 · HTML 报告开源地址
- **v3.1**（当前）：🏗️ **架构重构** · SKILL.md 控制平面拆分（980 行 → 228 行）· 双入口合一 · 分层采样引擎（`build_chat_history.py`）· 动态范围选择 · 评分推导规则（对称性/Sternberg/Gottman 均有字段来源）· 双阈值危险预警 · 可空字段设计
- **v3.2**（规划）：语音消息转文字分析 · 图片表情包分析 · Linux 支持完善

---

## 社区支持

<div align="center">

**学 AI，上 L 站**

[![LINUX DO](https://img.shields.io/badge/LINUX%20DO-社区支持-blue?style=for-the-badge)](https://linux.do)

本项目在 [LINUX DO](https://linux.do) 社区发布与交流，感谢佬友们的支持与反馈。

</div>

---

## 致谢

> **[ylytdeng/wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt)** — WeChat 4.0 数据库解密器，本项目微信能力的基础 🙏

> **[shuakami/qq-chat-exporter](https://github.com/shuakami/qq-chat-exporter)** — NapCat + QCE 插件，QQ 聊天记录导出方案 🙏

> **[hotcoffeeshake/tong-jincheng-skill](https://github.com/hotcoffeeshake/tong-jincheng-skill)** — 祖师爷童锦程心智模型与语录整理 🙏

---

## 免责声明

本工具仅供娱乐，不构成情感建议。仅用于分析你自己的数据，请勿侵犯他人隐私。所有数据本地处理，不上传任何服务器。

---

<div align="center">

**MIT License © 2026 她不一样**

*如果这个项目帮你想通了什么，记得给个 ⭐*

</div>

> 曾用名：「她爱我吗？恋情分析室」· 前身：舔狗鉴定所
