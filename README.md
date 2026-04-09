<div align="center">

<img height="40" src="https://img.shields.io/badge/%E5%A5%B9%E7%88%B1%E4%BD%A0%E5%90%97%EF%BC%9F-%E8%88%94%E7%8B%97%E9%89%B4%E5%AE%9A%E6%89%80%20%C2%B7%20Skill-ff69b4?style=for-the-badge&logo=wechat&logoColor=white" alt="她爱你吗？舔狗鉴定所 · Skill" />

<br/>
<br/>

**用 AI，帮你从微信聊天记录里找到答案。**

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-0078d4.svg?style=flat-square)]()
[![WeChat](https://img.shields.io/badge/WeChat-4.0%2B-07c160.svg?style=flat-square)]()
[![Agent Skill](https://img.shields.io/badge/Universal-Agent%20Skill-d97706.svg?style=flat-square)](https://github.com/863401402/she-love-me)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-✓-d97706.svg?style=flat-square)](https://claude.ai/code)
[![Codex](https://img.shields.io/badge/Codex-✓-111111.svg?style=flat-square)](https://developers.openai.com/codex)
[![Cursor](https://img.shields.io/badge/Cursor-✓-000000.svg?style=flat-square)](https://cursor.sh)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/863401402/she-love-me/pulls)

<br/>

[快速开始](#快速开始) · [功能特性](#功能特性) · [工作原理](#工作原理) · [致谢](#致谢)

</div>

---

## 简介

**她爱你吗？** 是一个**通用 Agent Workflow**，支持 Claude Code、Codex、Cursor、GitHub Copilot、Gemini CLI 等主流 AI 编程工具。

只需要一条命令 `/she-love-me`，它就能自动解密你的微信数据库、分析你和某个联系人的全部聊天记录，然后告诉你：**你到底有多舔，她到底爱不爱你。**

> 分析全程在本地运行，数据不上传任何服务器。

---

## 输出效果

> *(首次运行后，在 `reports/` 目录用浏览器打开 HTML 报告)*

### 鉴定指数

```
🐶 舔狗指数   73 ████████░░  你发起对话 72%，偶尔连轰 767 次
💜 被爱指数   66 ███████░░░  她凌晨 3 点发了 8 条消息说想你
🧊 冷淡指数   28 ███░░░░░░░  回复速度 8 分钟，态度还行
```

### 报告截图

> 📸 *截图示例（以真实运行结果为准）*

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
| 🐶 **舔狗指数** | 主动发起占比 · 连续轰炸次数 · 回复速度差 · 消息长度比 |
| 💜 **被爱指数** | 对方主动次数 · 晚安/早安分析 · 关心频率 |
| 🧊 **冷淡检测** | "嗯""哦""好" 占比 · 长时间已读不回统计 |
| 📊 **话语权分析** | 谁在主导对话，谁在迎合 |
| 📈 **趋势图表** | 每日消息量 · 活跃时段 · 双方占比（Chart.js） |
| 🔍 **AI 鉴定** | Claude 读取样本消息，给出有洞察力（且幽默）的结论 |
| 📄 **双格式输出** | 终端 Markdown 摘要 + 可分享的 HTML 报告 |

---

## 快速开始

### 前置条件

- Windows / macOS + WeChat 4.0+（**必须处于登录运行状态**）
- 任意一个支持 Skill 的 AI 编程工具（见下方）
- Windows 需要使用**管理员终端**
- macOS 请确保终端具备必要系统权限，并按上游解密器提示授权

### 安装

```bash
git clone https://github.com/863401402/she-love-me
cd she-love-me
```

根据你使用的 AI 工具，启动对应的 Agent：

| 工具 | Skill 格式 | 启动命令 | 运行命令 |
|------|-----------|----------|----------|
| [Claude Code](https://claude.ai/code) | `.claude/skills/` | `claude` | `/she-love-me` |
| [Codex](https://developers.openai.com/codex) | `AGENTS.md` | `codex` / 在 Codex 中打开项目 | 直接输入「运行 she-love-me 工作流」 |
| [OpenClaw](https://openclaw.ai) | `.claude/skills/` | `openclaw`（管理员） | `/she-love-me` |
| [Cursor](https://cursor.sh) | `.agents/skills/` | 打开项目文件夹 | `/she-love-me` |
| [GitHub Copilot](https://github.com/features/copilot) | `.agents/skills/` | 打开 VS Code | `/she-love-me` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `.agents/skills/` | `gemini` | `/she-love-me` |

> Skill 文件位于 `.claude/skills/she-love-me/SKILL.md`（Claude Code / OpenClaw）和 `.agents/skills/she-love-me/SKILL.md`（通用格式）；Codex 使用根目录 `AGENTS.md` 作为项目级指令入口。

### 运行

Claude / Cursor / Copilot / Gemini CLI:

```
/she-love-me
```

Codex:

```text
运行 she-love-me 工作流
```

**就这些。** Skill 会自动处理一切：

```
/she-love-me
  ↓
运行 setup_check.py → 自动 clone wechat-decrypt → pip install 依赖
  ↓
扫描微信内存 → 提取密钥 → 解密 19 个数据库
  ↓
展示联系人列表 → 你选择分析对象
  ↓
提取消息 → 统计计算 → Claude AI 深度鉴定
  ↓
生成 HTML 报告 + 终端摘要
```

---

## 工作原理

```
WeChat 4.0（运行中）
    │
    │  内存扫描，提取 SQLCipher4 密钥
    ▼
wechat-decrypt（自动 clone）
    │
    │  解密 19 个数据库文件
    ▼
标准 SQLite 文件（contact.db · message_N.db · session.db）
    │
    │  scripts/ 统计分析引擎
    ▼
舔狗指数 / 被爱指数 / 成分表 / 趋势数据
    │
    │  Claude AI 读取样本消息，深度鉴定
    ▼
HTML 报告（暗色现代风格）+ Markdown 摘要
```

**微信解密部分完全依赖 [ylytdeng/wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt)，本项目不包含任何解密代码，只调用其公开接口。**

---

## 项目结构

```
she-love-me/
├── AGENTS.md                   # Codex 项目级指令入口
├── .claude/
│   ├── settings.json           # Skill 注册配置
│   └── skills/
│       └── she-love-me/
│           └── SKILL.md        # Skill 入口（Claude Code / OpenClaw）
├── .agents/
│   └── skills/
│       └── she-love-me/
│           └── SKILL.md        # Skill 入口（Cursor / Copilot / Gemini CLI）
├── scripts/
│   ├── setup_check.py          # 跨平台环境检查 / 依赖准备 / 微信进程检测
│   ├── decrypt_wechat.py       # 跨平台解密入口（macOS 走 C 扫描器）
│   ├── list_contacts.py        # 列出联系人（按消息数排序）
│   ├── extract_messages.py     # 提取指定联系人全部消息
│   ├── stats_analyzer.py       # 统计分析引擎（舔狗指数计算）
│   └── generate_html_report.py # 生成 HTML 报告
├── vendor/                     # wechat-decrypt 自动 clone 到这里（gitignore）
├── data/                       # 分析中间数据（gitignore）
├── reports/                    # 生成的 HTML 报告（gitignore）
├── assets/                     # README 截图
├── requirements.txt
└── LICENSE
```

---

## 支持平台

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows | ✅ 支持 | 需要管理员终端 |
| macOS | 🧪 实验性支持 | 依赖上游 wechat-decrypt、ad-hoc 签名与本机权限配置 |
| Linux | 🔜 规划中 | wechat-decrypt 已支持，适配中 |

---

## 版本规划

- **v1.0**（当前）：文字消息分析 · HTML 报告 · 舔狗/被爱/冷淡指数
- **v2.0**（规划）：语音消息转文字分析 · 图片表情包分析 · Linux 支持完善

---

## 致谢

本项目的微信数据库解密能力完全来自：

> **[ylytdeng/wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt)**
>
> WeChat 4.0 database decryptor — 通过内存扫描提取 SQLCipher4 密钥，实时解密微信数据库。
> 没有这个项目，本工具无从实现。感谢作者的开源贡献 🙏

---

## 免责声明

- 本工具**仅供娱乐**，鉴定结果不构成任何情感建议
- **仅用于分析你自己的微信数据**，请勿侵犯他人隐私
- 所有数据处理在本地完成，不上传至任何服务器
- 使用前请确认当地法律法规

---

<div align="center">

**MIT License © 2026 她爱你吗？舔狗鉴定所**

*如果这个项目帮你想通了什么，记得给个 ⭐*

</div>
