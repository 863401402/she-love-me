# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

**她不一样** 是一个通用 Agent Skill，通过解密本地微信数据库、分析聊天记录，结合心理学框架生成恋爱关系分析报告。所有数据处理均在本地完成，不上传任何服务器。

主入口：`/she-love-me`（Skill 命令）

## 核心命令

```bash
# 环境检查 + 自动部署（首次运行或排查问题时）
python scripts/setup_check.py --ensure-decryptor

# 解密微信数据库
python scripts/decrypt_wechat.py

# 列出联系人（按消息数排序）
python scripts/list_contacts.py --decrypted-dir vendor/wechat-decrypt/decrypted

# 提取指定联系人消息
python scripts/extract_messages.py \
  --decrypted-dir vendor/wechat-decrypt/decrypted \
  --contact "<联系人名字>" \
  --output data/messages.json

# 统计分析
python scripts/stats_analyzer.py --input data/messages.json --output data/stats.json

# 生成 HTML 报告
python scripts/generate_html_report.py \
  --stats data/stats.json \
  --analysis data/analysis.json \
  --contact "<联系人名字>" \
  --output reports/
```

> macOS 用 `python3` 替换 `python`，Windows 需要管理员终端。

## 架构概览

```
/she-love-me (Skill 命令)
    ↓
scripts/setup_check.py        # 环境检查：Python 版本、clone vendor、安装依赖、检测微信进程
    ↓
scripts/decrypt_wechat.py     # 解密入口：Windows 走 Python 扫描，macOS 编译并调用 C 扫描器
    ↓
vendor/wechat-decrypt/        # 上游解密器（首次自动 clone，gitignored）
  decrypted/                  # 解密后的 SQLite 文件（contact.db, message_N.db, session.db）
    ↓
scripts/list_contacts.py → scripts/extract_messages.py
    ↓
data/messages.json
    ↓
scripts/stats_analyzer.py → data/stats.json        # 全量统计
scripts/build_chat_history.py → data/chat_history.txt  # 分层采样（用户选定时间范围）
    ↓
Claude AI 深度鉴定（全量统计 + 分层采样关键窗口）→ data/analysis.json
    ↓
scripts/generate_html_report.py → reports/*.html
```

## Skill 结构

- `.agents/skills/she-love-me/SKILL.md` — 唯一源文件（Claude Code + Cursor/Copilot/Gemini CLI 共用）
- `.agents/skills/she-love-me/references/` — 知识库（从 SKILL.md 拆出，按需读取）
  - `analysis-framework.md` — 模块 F + A + B 心理学分析框架
  - `risk-signals.md` — 模块 C 危险预警 7 类信号
  - `strategist-guide.md` — 模块 D + E + G 军师指南 + 语气风格
  - `report-schema.md` — analysis.json 完整 JSON schema
  - `report-template.md` — Step 9 Markdown 展示模板
- `.claude/settings.json` — 注册 Skill 路径（指向 `.agents/skills/she-love-me`）

AI 分析模块（F → A → B → C → D → E → G）：
- **模块 F**：人格深度画像（核心恐惧、防御机制、底层需求、信任架构）
- **模块 A**：关系诊断（Sternberg 三角、Gottman 四骑士、关系阶段、不对称分析）
- **模块 B**：人格分析（依恋类型、沟通风格、爱的语言、情感可得性）
- **模块 C**：危险预警（7 类高风险信号）
- **模块 D**：军师建议（停止/开始各 3 条 + 路线图 + 止损红线）
- **模块 E**：5 条鉴定发现（引用原文）
- **模块 G**：童锦程祖师爷寄语

## 数据流与目录约定

| 目录/文件 | 说明 |
|-----------|------|
| `vendor/wechat-decrypt/` | 上游解密器，首次自动 clone（gitignored） |
| `vendor/wechat-decrypt/decrypted/` | 解密后的 SQLite 文件 |
| `data/messages.json` | 提取的消息（中间数据，gitignored） |
| `data/stats.json` | 全量统计结果 |
| `data/chat_history.txt` | 分层采样聊天记录（用户选定范围 + 关键窗口） |
| `data/analysis.json` | Claude AI 分析结果（JSON schema 见 references/report-schema.md） |
| `reports/` | 生成的 HTML 报告（gitignored） |

## 依赖说明

本项目自身无外部 Python 依赖（仅用标准库 `sqlite3`）。`setup_check.py --ensure-decryptor` 会自动为 `vendor/wechat-decrypt` 安装：
- `pycryptodome>=3.19,<4`
- `zstandard>=0.22,<1`

需要 Python 3.9+，支持 Windows 和 macOS（Linux 规划中）。

## 平台注意事项

- **Windows**：必须以管理员终端运行；解密走 `find_all_keys_windows.py`
- **macOS**：实验性支持；`decrypt_wechat.py` 会自动编译 `vendor/wechat-decrypt/find_all_keys_macos.c`；需要终端系统权限
- 微信必须处于**运行+登录**状态才能提取密钥
