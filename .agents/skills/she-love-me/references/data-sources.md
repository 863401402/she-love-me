# 聊天数据获取与导入

本文件定义所有 Agent 共用的数据获取流程。工作目录始终是仓库根目录；原始导出放在 `data/raw/`，转换结果放在 `data/contacts/`。不得把聊天记录写入 tracked 文件。

## 目录

- [通用执行规则](#通用执行规则)
- [Windows 微信：weflow-cli（首选）](#windows-微信weflow-cli首选)
- [Windows 微信：CipherTalk（自动回退）](#windows-微信ciphertalk自动回退)
- [已有导出文件](#已有导出文件)

## 通用执行规则

1. Agent 应主动执行环境检查、安装、初始化、导出和转换命令，不要只把命令列表交给用户。
2. 若 Agent 运行环境要求批准全局 npm 安装、联网下载、管理员权限或进程读取，应直接发起相应授权请求。
3. 仅在必须由用户完成时暂停：启动/登录微信、扫码、授权管理员权限、选择联系人或提供 QCE Token。
4. 不输出数据库密钥、Access Token 或聊天正文到对话；只展示联系人名称、会话 ID、消息数和生成路径。
5. 首选工具失败后自动尝试备选工具；两个工具都失败才使用已有 JSON/Markdown。
6. 第三方工具由其各自项目维护。本项目可以代用户安装和运行，但不声称对其原生组件做过独立安全审计。

## Windows 微信：weflow-cli（首选）

已知兼容性反馈：[Issue #31](https://github.com/863401402/she-love-me/issues/31) 报告 Windows 微信 4.1.13.65 下两条提取路径失败，尚未验证修复。扫描返回空账号时，不要解释为账号不匹配；检查结构化错误码和诊断信息。两条路径均失败时转已有 JSON/Markdown 导入，不要循环登录重试或声称已适配该版本。

适用：Windows 10/11、微信 4.x、Python 3.9+、Node.js 18+、管理员终端。

### WX-1 环境检查与安装

先自动检查两个提供方：

```powershell
python scripts/setup_chat_exporter.py --provider auto
```

未就绪时请求所需授权，然后自动安装：

```powershell
python scripts/setup_chat_exporter.py --provider auto --install
```

读取 JSON 中的 `provider`；它会先尝试 weflow-cli，安装失败时自动尝试 CipherTalk。仅当 `ready` 为 `true` 时继续：`provider` 为 `weflow-cli` 执行 WX-2，为 `ciphertalk` 直接跳到 CT-2。如果错误为 Node.js/npm 缺失，提示用户安装 Node.js 后重试。不要根据某一台机器的 Node 小版本、编译工具或安装错误推导通用前置条件；以安装器在当前环境返回的结构化结果为准。

### WX-2 初始化微信数据

```powershell
weflow-cli init
```

- 微信未运行/未登录：让用户启动并登录微信，再重试。
- 权限或进程访问失败：请求在管理员终端重试。
- 工具可能等待微信出现；不要在它仍运行时结束任务。
- 不向用户显示或复述工具输出中的数据库密钥。

### WX-3 列出并选择会话

```powershell
weflow-cli sessions -n 30
```

只向用户展示前 30 个会话的序号、显示名和会话 ID，等待选择。不要展示最后一条消息摘要。

### WX-4 导出 JSON

```powershell
weflow-cli export "<会话 ID>" json --output "data/raw"
```

导出文件通常是 `data/raw/<会话 ID>_messages.json`。根据命令输出和目录中新生成的 JSON 确认实际文件，不要猜路径。

### WX-5 转换

```powershell
python scripts/convert_weflow_cli.py \
  --input "<实际 JSON 路径>" \
  --contact "<联系人显示名>" \
  --contact-id "<会话 ID>" \
  --output-dir data/contacts
```

读取返回 JSON 中的 `bundle_dir` 和 `messages_path`，进入主技能 Step 6。

## Windows 微信：CipherTalk（自动回退）

当 weflow-cli 安装、初始化或导出失败时使用。

### CT-1 检查与安装

```powershell
python scripts/setup_chat_exporter.py --provider ciphertalk
python scripts/setup_chat_exporter.py --provider ciphertalk --install
```

第二条仅在第一条未就绪时执行，并按 Agent 平台要求请求安装授权。

### CT-2 诊断并配置数据库目录

```powershell
python scripts/diagnose_ciphertalk.py
```

读取结构化结果：

- `candidates` 只有一个且 `usable_layout=true`：直接执行 `python scripts/diagnose_ciphertalk.py --configure`。
- 有多个候选：只展示候选序号、账号目录、`session_db_count` 和 `message_db_count`，让用户选择后执行 `--candidate <序号> --configure`。
- 没有候选：让用户在微信设置中查看聊天文件存储位置，仅提供目录路径，然后执行 `--db-path "<路径>" --configure`。不要让用户提供聊天正文。
- `config.has_key=true`：跳到 CT-4。
- `config.has_key=false`：进入 CT-3。

不要使用空参数的 `miyu init` 代替目录诊断；它不会自动发现 Windows 微信数据库路径。

### CT-3 本地配置密钥

先确认管理员终端和微信登录状态，然后只自动尝试一次：

```powershell
miyu --format=json --quiet key get --save
```

不要进入不带子命令的 `miyu` 交互工作台。不要显示、读取或要求用户在对话中粘贴密钥。

如果返回 `等待密钥超时`，停止重复登录。CipherTalk CLI 当前只 Hook `tasklist` 返回的第一个 `Weixin.exe`，在多进程微信上可能选错进程，且不支持指定 PID。此时仅使用以下可信路径之一：

1. Agent 直接执行以下无界面扫描流程。它从 CipherTalk 官方仓库固定 tag 下载约 468 KB 的 `wechat_key_tool.dll` 和匹配的 `wxKeyService.ts`，校验 SHA-256 后调用官方多进程扫描函数。密钥直接写入本机 miyu 配置，标准输出不包含密钥、账号资料或聊天正文：

```powershell
python scripts/diagnose_ciphertalk.py --scan-key --download-scanner
```

若提示微信未运行，让用户登录后重试；若提示权限不足，只请求管理员终端授权，不要反复退出登录。读取返回字段：

- `database_validated=true`：候选密钥已经通过 `contact.db` 验证，继续 CT-4。
- `database_validated=false`：官方 `scanAccount()` 只完成账号/格式自校验，尚未证明能打开磁盘数据库。让用户进入任意聊天触发数据库访问后再扫描一次，然后执行：

```powershell
python scripts/run_ciphertalk_cli.py --timeout 60 -- status
```

仅当返回的 `connection.ok=true` 时继续 CT-4。若超时、`DB_ERROR` 或 native 初始化失败，不得声称 CLI 已可导出，进入下方桌面版兼容兜底。不要从桌面版单独抽取 `WCDB.dll/wcdb_api.dll`：官方二进制在脱离应用环境时会拒绝初始化。

2. 仅当官方无界面扫描组件也失败时，进入 CT-Desktop。桌面版是最终兼容兜底，不是默认要求。
3. 用户已经通过可信工具持有密钥时，可在自己的本地管理员终端执行 `miyu key set <64位密钥>`；Agent 不接收该值。

CLI 密钥配置完成后执行 `miyu --format=json --quiet status`，仅当 `configured=true` 且连接成功时继续。没有密钥时不要运行 `status`，部分版本会长时间等待数据库连接。

### CT-4 列出会话并导出

```powershell
python scripts/run_ciphertalk_cli.py --timeout 120 -- --limit=30 sessions
python scripts/run_ciphertalk_cli.py --timeout 300 -- export "<会话 ID>" --output "data/raw/ciphertalk-chat.json"
```

向用户展示会话显示名和 ID，等待选择；不要展示聊天正文。

### CT-5 转换

```powershell
python scripts/convert_ciphertalk.py \
  --input "data/raw/ciphertalk-chat.json" \
  --contact "<联系人显示名>" \
  --contact-id "<会话 ID>" \
  --output-dir data/contacts
```

读取 `bundle_dir` 和 `messages_path`，进入主技能 Step 6。

转换器同时支持 CipherTalk CLI 消息数组、桌面版 detailed-json 和 ChatLab JSON。

### CT-Desktop 官方桌面版 + MCP 兜底

适用：CLI 无法验证或打开数据库，但官方 CipherTalk 桌面版能够完成账号配置。不要要求用户在桌面版手工逐个导出；配置完成后由 Agent 通过桌面版自带 MCP 完成列会话和完整导出。

#### CT-D1 下载、安装并配置桌面版

下载并校验官方 GitHub Release：

```powershell
python scripts/setup_ciphertalk_desktop.py --download
```

Agent 启动返回的官方安装包；仅在安装界面、微信登录或账号选择时等待用户。安装后启动 CipherTalk，用户在桌面版完成账号扫描/选择，直到主界面能正常查看会话。保持 CipherTalk 主程序运行。

不要读取或打印 `%APPDATA%/ciphertalk/ciphertalk-config.db` 的密钥、Token 或账号字段。不要让用户把密钥粘贴到对话。

#### CT-D2 准备桌面 MCP

部分官方发布包的 `ciphertalk-mcp.cmd` 缺少 JavaScript MCP SDK。检查并在已忽略的 `scripts/tmp/` 中安装固定依赖：

```powershell
python scripts/setup_ciphertalk_mcp.py
python scripts/setup_ciphertalk_mcp.py --install
```

第二条只在第一条返回 `dependency_ready=false` 时运行。脚本会自动查找标准 Windows 安装目录，也允许用 `--launcher "<ciphertalk-mcp.cmd>"` 指定非标准安装位置。只有 `ready=true` 时继续。

#### CT-D3 列出并选择会话

```powershell
python scripts/list_ciphertalk_sessions_mcp.py --limit 30
```

脚本只输出 `displayName`、`sessionId` 和 `kind`。向用户展示名称和会话 ID，等待选择；不要调用原始 MCP 客户端直接展示 `lastMessagePreview`。

#### CT-D4 完整导出

```powershell
python scripts/export_ciphertalk_mcp.py \
  --session-id "<会话 ID>" \
  --contact "<联系人显示名>" \
  --output-dir data/raw/ciphertalk-official
```

读取返回的 `output` 和 `total`。该脚本调用官方 `export_chat`，不导出图片、视频、语音或表情资产，只保留结构化消息记录。

**禁止用 MCP `get_messages` 的 offset 分页拼接全量记录。** 已观察到部分桌面版本在偏移达到一定值后循环返回旧页，可能造成重复消息和错误统计。完整导出必须使用 `export_ciphertalk_mcp.py` / 官方 `export_chat`，并以输出 JSON 的 `messages` 数量为准。

#### CT-D5 转换

```powershell
python scripts/convert_ciphertalk.py \
  --input "<CT-D4 返回的 output>" \
  --contact "<联系人显示名>" \
  --contact-id "<会话 ID>" \
  --output-dir data/contacts
```

读取返回的 `bundle_dir` 和 `messages_path`，进入主技能 Step 6。

## 已有导出文件

### 历史 WeFlow JSON

WeFlow 官方核心源码和 Release 已移除，不再引导新用户安装。仅转换用户以前保存的 JSON：

```bash
<PYTHON> scripts/convert_weflow.py --input "<JSON>" --output-dir data/contacts
```

### Markdown

支持 `[2026-08-12 20:10] 张三: 消息内容`：

```bash
<PYTHON> scripts/convert_markdown.py \
  --input "<Markdown>" --my-name "<自己的名字>" \
  --contact "<联系人>" --output-dir data/contacts
```

### 已有兼容解密器（高级/旧版）

仅当用户已经拥有可信兼容目录时使用：

```bash
<PYTHON> scripts/decrypt_wechat.py --decryptor-dir "<目录>"
<PYTHON> scripts/list_contacts.py --decrypted-dir "<目录>/decrypted"
<PYTHON> scripts/extract_messages.py \
  --decrypted-dir "<目录>/decrypted" --contact "<联系人>" \
  --output-dir data/contacts
```

不要运行 `setup_check.py --ensure-decryptor`，不要寻找或推荐来源不明的镜像。
