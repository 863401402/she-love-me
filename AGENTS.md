# she-love-me for Codex

当用户要求运行 she-love-me、分析微信聊天记录、生成鉴定报告时，按以下流程执行。

## 工作约束

- 始终以仓库根目录作为工作目录。
- 优先使用相对路径，不要硬编码绝对路径。
- 解释器选择：
  - Windows 优先 `python`
  - macOS / Linux 优先 `python3`
  - 若首选不存在，再回退到另一个

## 标准流程

1. 先运行环境检查脚本：

   - `<PYTHON> scripts/setup_check.py --ensure-decryptor`

   脚本会负责：

   - 检查 Python 版本
   - 在 `vendor/wechat-decrypt/` 不存在时自动 clone
   - 安装 `pycryptodome` 与 `zstandard`
   - 检查微信是否正在运行
   - 在 Windows / macOS 上给出对应的权限提示

2. 如果环境检查失败：

   - 直接读取报错并告诉用户原因
   - Windows 常见原因：未以管理员身份启动终端
   - macOS 常见原因：终端未获得必要系统权限，或微信未启动

3. 解密微信数据库：

   - `<PYTHON> scripts/decrypt_wechat.py`

4. 列出联系人：

   - `<PYTHON> scripts/list_contacts.py --decrypted-dir vendor/wechat-decrypt/decrypted`

5. 向用户展示联系人列表：

   - 按消息量倒序，只展示前 30 位
   - 让用户输入联系人名字或序号

6. 提取消息：

   - `<PYTHON> scripts/extract_messages.py --decrypted-dir vendor/wechat-decrypt/decrypted --contact "<联系人>" --output data/messages.json`

7. 统计分析：

   - `<PYTHON> scripts/stats_analyzer.py --input data/messages.json --output data/stats.json`

8. 读取 `data/messages.json` 最近 200 条文字消息和 `data/stats.json`，生成 `data/analysis.json`，至少包含：

   - `relationship_type`
   - `relationship_label`
   - `simp_description`
   - `love_description`
   - `key_findings`
   - `verdict`

9. 生成 HTML 报告：

   - `<PYTHON> scripts/generate_html_report.py --stats data/stats.json --analysis data/analysis.json --contact "<联系人>" --output reports/`

10. 用 Markdown 向用户输出摘要，并告知 HTML 报告路径。

## 输出风格

- 结论可以幽默，但不要刻薄。
- 必须引用聊天模式或消息特征，不要只报分数。
- 优先指出主动性、回复速度、冷淡回复、轰炸行为、晚安/关心等信号。
