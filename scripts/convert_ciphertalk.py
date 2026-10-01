"""Convert CipherTalk CLI JSON exports into a she-love-me message bundle."""

import argparse
import json
import sys

from external_chat_import import (
    content_or_placeholder,
    load_message_array,
    normalize_external_type,
    write_contact_bundle,
)


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def convert_payload(data, contact, contact_id=None):
    raw_messages = load_message_array(data, "CipherTalk")
    converted = []
    for index, raw in enumerate(raw_messages, start=1):
        if not isinstance(raw, dict):
            converted.append(raw)
            continue
        direction = str(raw.get("direction") or "").strip().lower()
        if direction:
            sender = {"out": "me", "in": "them"}.get(direction, "unknown")
        elif raw.get("isSend") in (True, 1, "1"):
            sender = "me"
        elif raw.get("isSend") in (False, 0, "0"):
            sender = "them"
        elif isinstance(data, dict) and data.get("meta", {}).get("ownerId"):
            sender = "me" if raw.get("sender") == data["meta"]["ownerId"] else "them"
        else:
            sender = "unknown"
        local_type = raw.get("localType", raw.get("type", raw.get("kind")))
        message_type = normalize_external_type(local_type)
        record = {
            "local_id": raw.get("localId", raw.get("messageId", index)),
            "source_message_id": raw.get("serverId") or raw.get("msgSvrId") or raw.get("messageId") or raw.get("localId"),
            "sender": sender,
            "timestamp": raw.get("createTime", raw.get("timestamp")),
            "type": message_type,
            "local_type": local_type,
            "content": content_or_placeholder(
                raw.get("content", raw.get("text")), message_type
            ),
        }
        media = raw.get("media") if isinstance(raw.get("media"), dict) else {}
        transcript = (
            raw.get("transcript") or raw.get("voiceTranscript") or media.get("transcript")
        )
        if transcript:
            record["transcript"] = str(transcript)
        converted.append(record)
    return {
        "source": "ciphertalk",
        "contact_username": contact_id or contact,
        "contact_display": contact,
        "account_id": data.get("meta", {}).get("ownerId", "unknown") if isinstance(data, dict) else "unknown",
        "messages": converted,
    }


def main():
    parser = argparse.ArgumentParser(description="转换 CipherTalk CLI/桌面版 JSON 为 she-love-me 数据格式")
    parser.add_argument("--input", required=True, help="CipherTalk CLI 或桌面版导出的 JSON 文件")
    parser.add_argument("--contact", required=True, help="联系人显示名")
    parser.add_argument("--contact-id", help="联系人 wxid 或稳定标识")
    parser.add_argument("--output-dir", default="data/contacts", help="联系人导出根目录")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    payload = convert_payload(data, args.contact, args.contact_id)
    normalized, bundle = write_contact_bundle(
        payload, args.contact, args.contact_id, args.output_dir, args.input
    )
    print(json.dumps({
        "status": "ok", "source": "ciphertalk", "total": normalized["total"],
        "dropped": normalized["normalization"]["dropped_messages"],
        "bundle_dir": bundle["bundle_dir"], "messages_path": bundle["messages_path"],
        "import": normalized["last_import"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
