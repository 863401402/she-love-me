"""
convert_weflow.py - Convert WeFlow chat export to she-love-me format

WeFlow (https://weflow.io) is a WeChat chat backup tool that exports
chat logs as JSON with {weflow, session, messages} structure.

This script converts WeFlow exports into the messages.json format
expected by she-love-me's stats_analyzer.py, enabling analysis
without going through the WeChat decryption pipeline.

Usage:
    python scripts/convert_weflow.py --input <weflow.json> --output <contacts_dir>

Output:
    <contacts_dir>/<wxid>_weflow/messages.json  — converted messages
    <contacts_dir>/<wxid>_weflow/emojis.json    — emoji catalog

Then run:
    python scripts/stats_analyzer.py --input <messages.json> --output <stats.json>
"""
import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

MSG_TYPE_MAP = {
    "文本消息": "text",
    "动画表情": "emoji",
    "图片消息": "image",
    "语音消息": "voice",
    "视频消息": "video",
    "表情": "emoji",
    "链接消息": "link",
    "系统消息": "system",
    "撤回消息": "revoke",
    "小程序消息": "mini_program",
    "位置消息": "location",
    "名片消息": "card",
    "合并转发消息": "merged",
    "文件消息": "file",
}


def convert(input_path, output_dir, own_wxid=None, display_name=None, wxid=None):
    """
    Convert WeFlow JSON export to she-love-me format.

    Args:
        input_path: Path to WeFlow export JSON file
        output_dir: Output directory (e.g., data/contacts)
        own_wxid: Your WeChat wxid (auto-detected if omitted)
        display_name: Contact display name (defaults to remark/nickname)
        wxid: Contact wxid (defaults to session.wxid)
    """
    with open(input_path, encoding="utf-8-sig") as f:
        data = json.load(f)

    session = data.get("session", {})
    messages_raw = data.get("messages", [])

    if not messages_raw:
        print("[-] Error: No messages found in input file", file=sys.stderr)
        sys.exit(1)

    contact_username = wxid or session.get("wxid", "unknown")
    contact_display = display_name or session.get("remark") or session.get("nickname") or "对方"

    # Auto-detect own_wxid: find a message where isSend=1 and sender != contact
    detected_own = own_wxid
    if not detected_own:
        for m in messages_raw:
            if m.get("isSend") == 1 and m.get("senderUsername") != contact_username:
                detected_own = m["senderUsername"]
                break
    if not detected_own:
        # Fallback: assume the non-contact sender in isSend=0 messages is us
        for m in messages_raw:
            if m.get("isSend") == 0:
                sender = m.get("senderUsername")
                if sender and sender != contact_username:
                    detected_own = sender
                    break

    output_path = Path(output_dir) / f"{contact_username}_weflow"
    output_path.mkdir(parents=True, exist_ok=True)

    messages = []
    emoji_records = {}

    for idx, m in enumerate(messages_raw, start=1):
        msg_type_str = m.get("type", "")
        msg_type = MSG_TYPE_MAP.get(msg_type_str, "other")
        local_type = m.get("localType", 0)
        create_time = m.get("createTime", 0)
        content = m.get("content", "")
        is_send = m.get("isSend", 0)
        sender_username = m.get("senderUsername", "")

        # Determine sender
        if is_send == 1:
            sender = "me"
        elif sender_username == contact_username:
            sender = "them"
        elif sender_username == detected_own:
            sender = "me"
        else:
            sender = "them"

        record = {
            "local_id": m.get("localId", idx),
            "sender": sender,
            "content": content,
            "timestamp": create_time,
            "type": msg_type,
            "local_type": local_type,
        }

        # Handle special message types
        if msg_type == "emoji" or local_type == 47:
            md5 = m.get("emojiMd5", f"unknown_{len(emoji_records) + 1}")
            emoji_id = f"emoji_{md5}"
            record["emoji_ref"] = emoji_id
            record["type"] = "emoji"
            record["content"] = content if content else "[表情]"
            if emoji_id not in emoji_records:
                emoji_records[emoji_id] = {
                    "emoji_id": emoji_id,
                    "md5": md5,
                    "type": m.get("type", ""),
                    "len": m.get("emojiLen"),
                    "cdnurl": m.get("emojiCdnUrl", ""),
                    "first_local_id": m.get("localId", idx),
                    "first_timestamp": create_time,
                    "occurrence_count": 1,
                }
            else:
                emoji_records[emoji_id]["occurrence_count"] += 1
        elif msg_type == "image":
            record["content"] = content if content else "[图片]"
        elif msg_type == "voice":
            record["content"] = content if content else "[语音消息]"
        elif msg_type == "video":
            record["content"] = content if content else "[视频]"
        elif msg_type == "revoke" or local_type == 10002:
            record["content"] = "[撤回了一条消息]"
        elif msg_type == "system":
            record["content"] = content if content else "[系统消息]"

        messages.append(record)

    messages.sort(key=lambda x: x["timestamp"])

    result = {
        "contact_username": contact_username,
        "contact_display": contact_display,
        "own_wxid": detected_own or "unknown",
        "bundle_dir": str(output_path),
        "total": len(messages),
        "emoji_total": sum(1 for m in messages if m.get("type") == "emoji"),
        "emoji_catalog_file": "emojis.json",
        "source": "WeFlow export",
        "original_file": Path(input_path).name,
        "messages": messages,
    }

    emoji_result = {
        "contact_username": contact_username,
        "contact_display": contact_display,
        "bundle_dir": str(output_path),
        "total_messages": result["emoji_total"],
        "unique_emojis": len(emoji_records),
        "emoji_records": sorted(
            emoji_records.values(),
            key=lambda x: (x.get("first_timestamp", 0), x.get("emoji_id", "")),
        ),
    }

    messages_file = output_path / "messages.json"
    emojis_file = output_path / "emojis.json"

    with open(messages_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(emojis_file, "w", encoding="utf-8") as f:
        json.dump(emoji_result, f, ensure_ascii=False, indent=2)

    print(f"[+] Converted {len(messages)} messages -> {messages_file}", file=sys.stderr)
    print(f"[+] Emojis: {result['emoji_total']} -> {emojis_file}", file=sys.stderr)
    print(json.dumps({
        "status": "ok",
        "total": len(messages),
        "emoji_total": result["emoji_total"],
        "contact": contact_display,
        "bundle_dir": str(output_path),
        "messages_path": str(messages_file),
        "emojis_path": str(emojis_file),
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Convert WeFlow chat export to she-love-me messages.json format"
    )
    parser.add_argument("--input", required=True, help="Path to WeFlow export JSON")
    parser.add_argument("--output", required=True, help="Output directory for converted data")
    parser.add_argument("--own-wxid", default=None, help="Your WeChat wxid (auto-detected if omitted)")
    parser.add_argument("--display-name", default=None, help="Override contact display name")
    parser.add_argument("--wxid", default=None, help="Override contact wxid")
    args = parser.parse_args()

    convert(args.input, args.output,
            own_wxid=args.own_wxid,
            display_name=args.display_name,
            wxid=args.wxid)


if __name__ == "__main__":
    main()
