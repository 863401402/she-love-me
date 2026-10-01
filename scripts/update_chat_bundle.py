"""Incrementally import an existing normalized messages.json into a contact bundle."""

import argparse
import json
import sys

from external_chat_import import write_contact_bundle


def main():
    parser = argparse.ArgumentParser(description="合并统一格式聊天记录，保留历史导入批次")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="data/contacts")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    contact = payload.get("contact_display") or payload.get("contact_username")
    if not contact:
        raise ValueError("输入需要 contact_display 或 contact_username")
    result, bundle = write_contact_bundle(payload, contact, payload.get("contact_username"),
                                          args.output_dir, args.input)
    print(json.dumps({"status": "ok", "total": result["total"],
                      "messages_path": bundle["messages_path"], "import": result["last_import"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
