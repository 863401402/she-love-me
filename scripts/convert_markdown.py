"""Convert common timestamped Markdown chat exports into a message bundle."""

import argparse
import json
import re
import sys
from pathlib import Path

from external_chat_import import write_contact_bundle


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


LINE_PATTERNS = (
    re.compile(r"^\s*[-*]?\s*\[?(?P<time>\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\]?\s+(?P<sender>[^:：]{1,80})[:：]\s*(?P<content>.*)$"),
    re.compile(r"^\s*[-*]?\s*(?P<sender>[^:：]{1,80})[:：]\s*\[?(?P<time>\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(?P<content>.*)$"),
)


def parse_markdown(text, my_name):
    messages = []
    current = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = next((pattern.match(line) for pattern in LINE_PATTERNS if pattern.match(line)), None)
        if match:
            current = {
                "local_id": line_number,
                "sender": "me" if match.group("sender").strip() == my_name else "them",
                "content": match.group("content").strip(),
                "timestamp": match.group("time"),
                "type": "text",
            }
            messages.append(current)
        elif current and line.strip() and not line.lstrip().startswith(("#", "---")):
            current["content"] += "\n" + line.strip()
    if not messages:
        raise ValueError("未识别到消息；支持格式：[2026-08-12 20:10] 张三: 消息内容")
    return messages


def main():
    parser = argparse.ArgumentParser(description="转换带时间戳的 Markdown 聊天记录")
    parser.add_argument("--input", required=True, help="Markdown 文件")
    parser.add_argument("--my-name", required=True, help="记录中代表你自己的发送者名称")
    parser.add_argument("--contact", required=True, help="联系人显示名")
    parser.add_argument("--contact-id", help="联系人稳定标识，用于目录去重")
    parser.add_argument("--output-dir", default="data/contacts", help="联系人导出根目录")
    args = parser.parse_args()

    source = Path(args.input)
    payload = {
        "source": "markdown",
        "contact_username": args.contact_id or args.contact,
        "contact_display": args.contact,
        "messages": parse_markdown(source.read_text(encoding="utf-8-sig"), args.my_name),
    }
    payload, bundle = write_contact_bundle(
        payload, args.contact, args.contact_id, args.output_dir, args.input
    )
    print(json.dumps({
        "status": "ok", "source": "markdown", "total": payload["total"],
        "bundle_dir": bundle["bundle_dir"], "messages_path": bundle["messages_path"],
        "import": payload["last_import"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
