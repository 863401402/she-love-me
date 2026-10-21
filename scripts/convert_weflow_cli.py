"""Convert weflow-cli JSON exports into a she-love-me message bundle."""

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


def _is_sent(value):
    if value in (1, True, "1"):
        return True
    if value in (0, False, "0"):
        return False
    return None


def convert_payload(data, contact, contact_id=None, own_wxid=None):
    raw_messages = load_message_array(data, "weflow-cli")
    converted = []
    for index, raw in enumerate(raw_messages, start=1):
        if not isinstance(raw, dict):
            converted.append(raw)
            continue
        sent = _is_sent(raw.get("isSend"))
        if sent is None and own_wxid:
            sent = raw.get("senderUsername") == own_wxid
        if sent is None and contact_id and raw.get("senderUsername") == contact_id:
            sent = False
        message_type = normalize_external_type(raw.get("localType", raw.get("type")))
        content = raw.get("parsedContent") or raw.get("content") or raw.get("rawContent")
        record = {
            "local_id": raw.get("localId", index),
            "source_message_id": raw.get("serverId") or raw.get("msgSvrId") or raw.get("localId"),
            "sender": "me" if sent is True else "them" if sent is False else "unknown",
            "timestamp": raw.get("createTime", raw.get("timestamp")),
            "type": message_type,
            "local_type": raw.get("localType"),
            "content": content_or_placeholder(content, message_type),
        }
        transcript = raw.get("transcript") or raw.get("voiceTranscript")
        if transcript:
            record["transcript"] = str(transcript)
        converted.append(record)
    return {
        "source": "weflow-cli",
        "contact_username": contact_id or contact,
        "contact_display": contact,
        "own_wxid": own_wxid or "unknown",
        "messages": converted,
    }


def main():
    parser = argparse.ArgumentParser(description="转换 weflow-cli JSON 为 she-love-me 数据格式")
    parser.add_argument("--input", required=True, help="weflow-cli 导出的 JSON 文件")
    parser.add_argument("--contact", required=True, help="联系人显示名")
    parser.add_argument("--contact-id", help="联系人 wxid 或稳定标识")
    parser.add_argument("--own-wxid", help="自己的微信 wxid，用于补全缺失的发送方向")
    parser.add_argument("--output-dir", default="data/contacts", help="联系人导出根目录")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    payload = convert_payload(data, args.contact, args.contact_id, args.own_wxid)
    normalized, bundle = write_contact_bundle(
        payload, args.contact, args.contact_id, args.output_dir, args.input
    )
    print(json.dumps({
        "status": "ok", "source": "weflow-cli", "total": normalized["total"],
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
