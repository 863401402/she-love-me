<div align="center">

<img src="../assets/banner.svg" alt="她不一样 Traditional Deployment" width="860" />

<br/>

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-0078d4.svg?style=flat-square)]()
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab.svg?style=flat-square)](https://www.python.org/downloads/)
[![Output](https://img.shields.io/badge/Output-messages.json%20%2B%20prompt-0f766e.svg?style=flat-square)]()
[![LLM](https://img.shields.io/badge/Use%20With-ChatGPT%20%7C%20Claude%20%7C%20Gemini-111111.svg?style=flat-square)]()

[快速开始](#快速开始) · [微信版](#微信版一步一步操作) · [QQ版](#qq版一步一步操作) · [常见问题](#常见问题)

</div>

---

# 传统部署版使用说明

这份文档是给没有编程基础的用户准备的。

你不需要使用 `/she-love-me`、`$she-love-me` 这类 agent 命令，也不需要理解仓库内部原理。你只需要做两件事：

1. 用仓库自带脚本导出聊天记录
2. 生成两份最终文件，然后上传给聊天模型

最终你会拿到这两份文件：

- `messages.json`
- `analysis_prompt.txt`

把这两个文件一起上传给 ChatGPT、Claude、Gemini、Kimi、豆包这类支持文件上传的聊天模型，就可以完成这个项目的核心使用流程。

---

## 最重要的前置要求

从这一步开始，你先记住两件事：

### 1. 终端一定要在仓库根目录打开

也就是说，你后面输入命令时，终端当前所在的位置必须是这个项目文件夹，也就是：

`she-love-me`

正确示例：

`<你的路径>\she-love-me`

如果你不是在这个目录里运行命令，后面很多命令都会报错。

### 2. 先安装环境依赖，再开始导出聊天记录

最推荐的做法是：

1. 先安装 Python
2. 再进入项目根目录
3. 运行依赖安装命令

---

## 先看结论

如果你只想知道自己最后要做什么，看这一段就够了：

1. 下载这个仓库到电脑
2. 安装 Python
3. 打开终端
4. 运行几条复制粘贴命令，导出聊天记录
5. 运行一条打包命令
6. 去 `traditional-deployment/output/你的联系人名字/` 里找到两份文件
7. 把这两份文件上传给聊天模型

---

## 你会得到什么

打包完成后，脚本会在下面这个目录生成结果：

`traditional-deployment/output/<联系人名>/`

里面有：

- `messages.json`
  这是整理好的聊天记录数据
- `analysis_prompt.txt`
  这是给聊天模型的详细分析提示词

你之后只需要上传这两个文件，不需要再自己写复杂提示词。

---

## 适合谁用

这个方案适合下面这些人：

- 不想依赖 agent 入口
- 想用最传统的“运行脚本 -> 出文件 -> 上传模型”的方式
- 想把结果交给任意聊天模型，而不是绑定在某个 agent 里
- 想把这套流程发给完全不懂编程的人照着做

---

## 使用前准备

### 1. 推荐操作系统

最推荐：

- Windows

也可以尝试：

- macOS

如果你是第一次操作，优先用 Windows。

### 2. 你需要准备什么

- 一台电脑
- 已安装并登录的微信，或者可用的 QQ Chat Exporter
- Python 3.9 或更高版本
- 能打开终端

### 3. 什么是“终端”

你可以把终端理解成“输入命令的黑框”。

Windows 常见方式：

1. 按键盘 `Win + R`
2. 输入 `powershell`
3. 回车

如果你已经安装了 Windows Terminal，也可以直接打开它。

### 4. 命令里的 `python` 和 `py`

在 Windows 里：

- 如果 `python` 能用，就用 `python`
- 如果 `python` 不可用，就把文档里的 `python` 全部换成 `py`

如果你完全不确定，直接优先试 `py`。

---

## 第零步：先把仓库下载到电脑

如果你已经把这个仓库下载好了，可以跳过这一节。

### 方法 A：最适合零基础用户

1. 打开这个仓库的 GitHub 页面
2. 点击绿色按钮 `Code`
3. 点击 `Download ZIP`
4. 下载完成后，解压到一个你找得到的位置

例如：

`<你的路径>\she-love-me`

### 方法 B：如果你已经安装了 Git

```bash
git clone https://github.com/863401402/she-love-me
```

---

## 第一步：从项目文件夹直接打开终端

这是最推荐的方式，最不容易出错。

### Windows 用户推荐这样做

1. 用资源管理器打开你解压后的项目文件夹
2. 进入 `she-love-me` 这个文件夹
3. 在文件夹空白处按住 `Shift` 再点鼠标右键
4. 选择：
   - `在此处打开 PowerShell 窗口`
   - 或 `在终端中打开`

如果你看到了一个黑色或蓝色的命令窗口弹出来，而且当前路径已经是项目目录，那就成功了。

### 另一种方式：先开终端，再切换目录

如果你已经先打开了终端，也可以手动进入项目目录。

如果你的项目在：

`<你的路径>\she-love-me`

那就执行：

```powershell
cd <你的路径>\she-love-me
```

如果路径不同，就把上面的路径换成你自己的。

### 怎么判断你已经进入成功

如果终端当前行前面显示的路径里已经有 `she-love-me`，就说明进对了。

---

## 第二步：安装环境依赖

这一步建议所有人都先做。

请确认你现在的终端位置已经是项目根目录，也就是 `she-love-me` 文件夹。

### 2.1 先确认 Python 是否正常

在终端里执行：

```powershell
py --version
```

如果你看到类似：

```text
Python 3.13.5
```

说明 Python 正常，可以继续。

如果提示找不到命令，先去安装 Python：

- Python 官网：https://www.python.org/downloads/

安装时建议勾选：

- `Add Python to PATH`

安装完重新打开终端，再执行一次：

```powershell
py --version
```

### 2.2 升级 pip

执行：

```powershell
py -m pip install --upgrade pip
```

### 2.3 安装项目依赖

执行：

```powershell
py -m pip install -r requirements.txt
```

### 这一步安装了什么

主要会安装：

- `pycryptodome`
- `zstandard`

这两个库主要用于微信相关的数据处理。

如果你只分析 QQ，很多情况下即使不装也能跑通，但为了少踩坑，建议统一安装。

macOS/Linux 建议使用虚拟环境，避免系统 Python 的 `externally-managed-environment` 安装限制：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

激活后，本文中的 `py` 命令应改为 `python`。虚拟环境只解决依赖安装；微信密钥提取仍取决于平台和微信版本兼容性。

### 2.4 微信用户额外准备

Windows 微信 4.1.13.65 有用户报告两条密钥提取路径均失败，尚未验证修复，见 [Issue #31](https://github.com/863401402/she-love-me/issues/31)。扫描组件返回空账号时，不能据此认定账号或目录不匹配；可改用已有 JSON/Markdown，不要反复登录或公开密钥。

新用户不要运行 `setup_check.py --ensure-decryptor`：原上游已因 DMCA 被屏蔽。Windows 微信当前使用 weflow-cli，失败时使用 CipherTalk。下面的微信章节会完整说明。

---

## 快速开始

你只需要先决定一件事：

- 你要分析的是微信聊天记录
- 还是 QQ 聊天记录

如果你分析微信，直接看下面的“微信版一步一步操作”。

如果你分析 QQ，直接看下面的“QQ版一步一步操作”。

---

## 微信版：一步一步操作

> 适合：Windows 微信 4.x 用户
> 需要：管理员终端、Node.js 18+、Python 3.9+；weflow-cli 在当前环境不可用时自动改用 CipherTalk

### 微信版第 1 步：检查并安装 weflow-cli

```powershell
py scripts/setup_chat_exporter.py --provider auto --install
```

脚本会通过 npm 安装 weflow-cli，并安装该工具自身的 Python 依赖。输出 JSON 中 `ready` 为 `true` 才继续。

### 微信版第 2 步：初始化本地微信数据

先打开并登录微信，再执行：

```powershell
weflow-cli init
```

如果提示进程访问失败，请确认当前终端以管理员身份运行。

### 微信版第 3 步：列出会话

```powershell
weflow-cli sessions -n 30
```

记下要分析的联系人显示名和会话 ID（通常是 `wxid_...`）。

### 微信版第 4 步：导出并转换

```powershell
weflow-cli export "<会话 ID>" json --output "data/raw"
py scripts/convert_weflow_cli.py --input "data/raw/<会话 ID>_messages.json" --contact "<联系人显示名>" --contact-id "<会话 ID>" --output-dir data/contacts
```

第二条命令会返回 `messages_path`。后续所有命令都把 `<messages_path>` 换成这个实际路径。

### weflow-cli 失败时：CipherTalk

```powershell
py scripts/setup_chat_exporter.py --provider ciphertalk --install
py scripts/diagnose_ciphertalk.py
py scripts/diagnose_ciphertalk.py --configure
miyu --format=json --quiet key get --save
miyu --format=json --quiet --limit=30 sessions
miyu --format=json --quiet export "<会话 ID>" --output "data/raw/ciphertalk-chat.json"
py scripts/convert_ciphertalk.py --input "data/raw/ciphertalk-chat.json" --contact "<联系人显示名>" --contact-id "<会话 ID>" --output-dir data/contacts
```

如果诊断发现多个账号，先按输出候选序号执行 `--candidate <序号> --configure`。npm CLI 自动取密钥超时后不要反复登录；直接调用 CipherTalk 官方多进程扫描组件：

```powershell
py scripts/diagnose_ciphertalk.py --scan-key --download-scanner
```

组件从 CipherTalk 官方仓库固定 tag 下载并校验，密钥只写入本机 miyu 配置，不输出到终端或 Agent 对话。仅当返回 `database_validated=true`，或限时 `status` 验证返回 `connection.ok=true` 时才继续导出；`scanAccount()` 的未验证候选不能当作端到端成功。

只有无界面扫描也失败时，才由 Agent 下载并校验官方桌面版作为兼容兜底：

```powershell
py scripts/setup_ciphertalk_desktop.py --download
```

用户确认安装并在桌面版完成账号配置后，保持主程序运行。Agent 继续通过官方 MCP 列会话和完整导出，不要求用户手工导出：

```powershell
py scripts/setup_ciphertalk_mcp.py --install
py scripts/list_ciphertalk_sessions_mcp.py --limit 30
py scripts/export_ciphertalk_mcp.py --session-id "<会话 ID>" --contact "<联系人>" --output-dir data/raw/ciphertalk-official
py scripts/convert_ciphertalk.py --input "<导出返回的 output>" --contact "<联系人>" --contact-id "<会话 ID>" --output-dir data/contacts
```

必须使用官方 `export_chat` 完整导出，不要用 MCP `get_messages` offset 分页拼接全量记录；部分版本会循环返回旧页。用户已经持有可信密钥时，也可在本机执行 `miyu key set`，密钥不得发送给 Agent。

---

### 微信版第 5 步：生成统计摘要

这一步不是绝对必须，但强烈建议做。

执行：

```powershell
py scripts/stats_analyzer.py --input "<messages_path>" --output "<bundle_dir>/stats.json"
```

### 为什么建议做这一步

因为聊天模型除了看原始聊天内容，还会参考一些结构化指标，比如：

- 谁更常主动发起对话
- 谁回复更快
- 谁更常修复冷战
- 谁更冷淡

这些统计会帮助模型做出更稳定的分析。

---

### 微信版第 6 步：生成最终分析包

执行：

```powershell
py traditional-deployment/build_llm_package.py --messages "<messages_path>" --stats "<bundle_dir>/stats.json"
```

### 成功时你会看到什么

终端会输出类似：

```json
{
  "status": "ok",
  "messages": "traditional-deployment\\output\\小王\\messages.json",
  "prompt": "traditional-deployment\\output\\小王\\analysis_prompt.txt"
}
```

这表示已经成功生成最终可交给聊天模型的两份文件。

---

## QQ版：一步一步操作

> 适合：已经安装并运行 QQ Chat Exporter 的用户

### QQ版第 1 步：先启动 QCE

你需要先安装并运行：

- QQ Chat Exporter (QCE)

项目地址：

- https://github.com/shuakami/qq-chat-exporter

如果你还没装，通常做法是：

1. 去 QCE 的 Releases 页面下载 Windows 版本
2. 解压
3. 运行启动文件
4. 用手机 QQ 扫码登录
5. 在界面或控制台里拿到 `Access Token`

### 如果你找不到 Token

通常可以在下面的位置找：

`%USERPROFILE%\.qq-chat-exporter\security.json`

打开后找到：

- `accessToken`

把这串内容复制出来备用。

---

### QQ版第 2 步：列出好友

把下面命令中的 `你的QCE_TOKEN` 换成你自己的 Token：

```powershell
py scripts/list_contacts_qq.py --token "你的QCE_TOKEN"
```

### 你会看到什么

你会看到一个好友列表，通常包含：

- 显示名称
- QQ 号
- 备注

从里面找到你要分析的人。

---

### QQ版第 3 步：导出某个好友的聊天记录

把下面命令中的：

- `你的QCE_TOKEN`
- `好友备注、昵称或QQ号`

替换成你自己的内容。

执行：

```powershell
py scripts/extract_messages_qq.py --token "你的QCE_TOKEN" --contact "好友备注、昵称或QQ号" --output data/messages.json
```

示例：

```powershell
py scripts/extract_messages_qq.py --token "abc123456" --contact "小王" --output data/messages.json
```

如果名字搜不到，可以直接改成 QQ 号再试一次。

---

### QQ版第 4 步：生成统计摘要

执行：

```powershell
py scripts/stats_analyzer.py --input data/messages.json --output data/stats.json
```

---

### QQ版第 5 步：生成最终分析包

执行：

```powershell
py traditional-deployment/build_llm_package.py --messages data/messages.json --stats data/stats.json
```

成功后也会在：

`traditional-deployment/output/<联系人名>/`

里生成两份最终文件。

---

## 最后一步：把文件交给聊天模型

到这里为止，你已经不需要再运行仓库里的其它分析命令了。

你只要找到这两份文件：

- `messages.json`
- `analysis_prompt.txt`

然后按下面步骤做：

1. 打开 ChatGPT、Claude、Gemini、Kimi、豆包等支持上传文件的聊天模型
2. 同时上传这两个文件
3. 在聊天框里再补一句：

```text
请严格按照提示词分析这份聊天记录，不要省略证据引用。
```

### 如果模型不支持同时上传两个文件

那就这样做：

1. 打开 `analysis_prompt.txt`
2. 复制里面的全部文字
3. 粘贴到聊天框
4. 再上传 `messages.json`

---

## 推荐你这样理解整个流程

你可以把整个流程理解成：

1. 仓库脚本负责“从微信/QQ里把聊天记录拿出来”
2. `build_llm_package.py` 负责“把聊天记录和提示词整理好”
3. 聊天模型负责“根据提示词真正写分析报告”

所以这个传统方案不是替代仓库，而是把仓库变成一种更容易交付给普通用户的形式。

---

## 最常用命令总表

### 微信用户最常用

```powershell
py scripts/setup_chat_exporter.py --provider auto --install
weflow-cli init
weflow-cli sessions -n 30
weflow-cli export "<会话 ID>" json --output "data/raw"
py scripts/convert_weflow_cli.py --input "data/raw/<会话 ID>_messages.json" --contact "<联系人>" --contact-id "<会话 ID>" --output-dir data/contacts
py scripts/stats_analyzer.py --input "<messages_path>" --output "<bundle_dir>/stats.json"
py traditional-deployment/build_llm_package.py --messages "<messages_path>" --stats "<bundle_dir>/stats.json"
```

### QQ用户最常用

```powershell
py scripts/list_contacts_qq.py --token "你的QCE_TOKEN"
py scripts/extract_messages_qq.py --token "你的QCE_TOKEN" --contact "好友备注、昵称或QQ号" --output data/messages.json
py scripts/stats_analyzer.py --input data/messages.json --output data/stats.json
py traditional-deployment/build_llm_package.py --messages data/messages.json --stats data/stats.json
```

---

## 常见问题

### 1. 我完全不懂命令行，还能用吗？

可以。

这份文档已经尽量改成“复制一条，回车一条”的形式了。

你真正需要改动的地方通常只有两个：

- 联系人名字
- QCE Token

其它内容基本都可以直接复制。

### 2. 命令里为什么都写 `py`？

因为在 Windows 里，`py` 往往比 `python` 更稳定。

如果你在 macOS 上操作，可以把命令里的 `py` 换成：

```bash
python3
```

### 3. 如果我不生成 `stats.json`，能不能用？

能。

你可以直接执行：

```powershell
py traditional-deployment/build_llm_package.py --messages data/messages.json
```

但不推荐。

因为这样提示词里缺少自动统计摘要，聊天模型会少一部分结构化依据。

### 4. `messages.json` 太大，聊天模型吃不下怎么办？

优先考虑：

- 换上下文更大的模型

如果还是太大，建议不要一次性分析几年聊天记录，而是缩小范围，例如只分析：

- 最近 1 个月
- 最近 3 个月
- 最近半年
- 某次明显升温后的阶段
- 某次明显降温后的阶段

### 5. 我导出的不是中文路径，会不会有影响？

一般没有影响。

但如果你发现某些终端里中文文件夹显示异常，不代表文件没生成。你可以直接去：

`traditional-deployment/output/`

里面手动查看。

### 6. 这套方案会不会自动上传我的聊天记录？

不会。

这个仓库只负责在你本地生成文件。

真正是否上传到第三方服务，取决于你后面把文件交给了哪个聊天模型平台。

### 7. 我怎么知道自己已经成功了？

最简单的判断方法：

去看这个目录：

`traditional-deployment/output/`

只要你能看到某个联系人名字的文件夹，并且里面有这两个文件：

- `messages.json`
- `analysis_prompt.txt`

就说明你已经成功了。

---

## 对交付方的建议

如果你是把这个仓库发给别人用，最推荐的做法不是让对方研究整个项目，而是直接把这份文档发给对方。

对普通用户来说，他们真正关心的只有三件事：

1. 我要下载什么
2. 我要复制哪些命令
3. 最后我要把哪两个文件上传给聊天模型

这份文档就是专门为这三件事写的。

---

## 一句话版总结

先用仓库脚本导出 `data/messages.json`，再运行 [build_llm_package.py](./build_llm_package.py)，最后去 `traditional-deployment/output/联系人名/` 里拿 `messages.json` 和 `analysis_prompt.txt` 上传给聊天模型。
