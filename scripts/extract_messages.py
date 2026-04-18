"""
extract_messages.py - 提取指定联系人的全部消息，并生成独立联系人目录中的 messages.json / emojis.json

消息存储结构（WeChat 4.0）：
  - message/message_N.db -> 每个联系人有独立的 Msg_{md5(username)} 表
  - 列：local_id, local_type, create_time, real_sender_id, message_content, WCDB_CT_message_content
  - real_sender_id 通过 Name2Id 表解析为 username
  - WCDB_CT_message_content == 4 表示 zstd 压缩
  - local_type == 1 文本, 3 图片, 34 语音, 43 视频, 47 表情, 49 链接/文件, 50 通话, 10000 系统

导出结构：
  - messages.json：聊天消息主体；表情消息只保留 emoji_ref
  - emojis.json：独立表情目录；保存 emoji_ref 对应的 md5 / cdnurl / len 等元信息
"""
import argparse
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
from xml.etree import ElementTree as ET

from contact_bundle import resolve_bundle_paths

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import zstandard as zstd
    _zstd_dctx = zstd.ZstdDecompressor()
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

MSG_TYPE_MAP = {
    1: "text",
    3: "image",
    34: "voice",
    42: "card",
    43: "video",
    47: "emoji",
    48: "location",
    49: "link",
    50: "call",
    10000: "system",
    10002: "revoke",
}


def decompress_content(content, ct):
    if ct == 4 and isinstance(content, bytes) and HAS_ZSTD:
        try:
            return _zstd_dctx.decompress(content).decode("utf-8", errors="replace")
        except Exception:
            return None
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return None
    return content


def get_msg_type(local_type):
    base = local_type & 0xFFFFFFFF if local_type > 0xFFFFFFFF else local_type
    return MSG_TYPE_MAP.get(base, "other")


def get_base_local_type(local_type):
    return local_type & 0xFFFFFFFF if local_type > 0xFFFFFFFF else local_type


def parse_emoji_metadata(content):
    """从表情消息 XML 中提取元信息。"""
    if not content or not isinstance(content, str) or "<emoji" not in content:
        return None
    try:
        root = ET.fromstring(content)
        emoji_node = root.find("emoji")
        if emoji_node is None:
            return None
        keep_fields = [
            "type", "md5", "len", "cdnurl", "thumburl", "encrypturl",
            "aeskey", "productid", "designerid", "thumbmd5",
            "androidmd5", "androidlen", "fromusername", "tousername",
            "externurl", "externmd5",
        ]
        meta = {}
        for key in keep_fields:
            value = emoji_node.attrib.get(key)
            if value not in (None, ""):
                meta[key] = html.unescape(value)
        return meta or None
    except Exception:
        return None


def build_emoji_id(meta, local_id):
    if meta and meta.get("md5"):
        return f"emoji_{meta['md5']}"
    return f"emoji_local_{local_id}"


def load_contacts(decrypted_dir):
    contact_db = os.path.join(decrypted_dir, "contact", "contact.db")
    names = {}
    if not os.path.exists(contact_db):
        return names
    conn = sqlite3.connect(contact_db)
    try:
        for row in conn.execute("SELECT username, nick_name, remark FROM contact").fetchall():
            uname, nick, remark = row
            names[uname] = remark or nick or uname
    finally:
        conn.close()
    return names


def find_username(contact_query, names):
    """模糊匹配联系人名字，返回 username"""
    q = contact_query.strip().lower()
    # 精确匹配 username
    if contact_query in names:
        return contact_query
    # 精确匹配 display_name
    for uname, display in names.items():
        if q == display.lower():
            return uname
    # 模糊匹配
    for uname, display in names.items():
        if q in display.lower() or q in uname.lower():
            return uname
    return None


def get_own_wxid(decrypted_dir):
    """从 config.json 推断自己的 wxid，兼容 Windows / macOS 路径"""
    # 尝试从 vendor/wechat-decrypt/config.json 读取
    config_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "vendor", "wechat-decrypt", "config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "vendor", "wechat-decrypt", "config.json"),
    ]
    for cfg_path in config_candidates:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("wxid"):
                    return cfg["wxid"]
                db_dir = cfg.get("db_dir", "")
                if db_dir:
                    parts = [p for p in os.path.normpath(db_dir).split(os.sep) if p]
                    if "db_storage" in parts:
                        idx = len(parts) - 1 - parts[::-1].index("db_storage")
                        if idx > 0:
                            return parts[idx - 1]
            except Exception:
                pass
    return None


def extract_messages_from_db(db_path, table_name, id_to_username, own_wxid, contact_username, contact_display):
    messages = []
    emoji_records = {}
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                f"SELECT local_id, local_type, create_time, real_sender_id, "
                f"message_content, WCDB_CT_message_content "
                f"FROM [{table_name}] ORDER BY create_time ASC"
            ).fetchall()

            last_known_sender = None  # 用于 revoke 消息回溯
            for row in rows:
                local_id, local_type, create_time, real_sender_id, content, ct = row
                content = decompress_content(content, ct)
                msg_type = get_msg_type(local_type)
                base_local_type = get_base_local_type(local_type)
                emoji_meta = parse_emoji_metadata(content) if msg_type == "emoji" else None

                # 判断发送方
                sender_username = id_to_username.get(real_sender_id, "")
                if own_wxid and sender_username == own_wxid:
                    sender = "me"
                elif sender_username == contact_username:
                    sender = "them"
                elif msg_type == "revoke" and last_known_sender:
                    # revoke 消息 real_sender_id 通常为 0，回溯上一条消息的 sender
                    sender = last_known_sender
                elif own_wxid and not sender_username:
                    sender = "unknown"
                else:
                    sender = "them" if sender_username == contact_username else "me"

                if sender in ("me", "them"):
                    last_known_sender = sender

                # 处理内容
                display_content = content or ""
                if msg_type == "text" and display_content and ":\n" in display_content:
                    # 群消息格式，只取内容部分（此处处理单聊，理论上不会有这种格式）
                    display_content = display_content.split(":\n", 1)[-1]
                elif msg_type == "image":
                    display_content = "[图片]"
                elif msg_type == "voice":
                    display_content = "[语音消息]"
                elif msg_type == "video":
                    display_content = "[视频]"
                elif msg_type == "emoji":
                    display_content = "[表情]"
                elif msg_type == "call":
                    display_content = "[通话]"
                elif msg_type == "revoke":
                    display_content = "[撤回了一条消息]"
                elif msg_type == "system":
                    display_content = f"[系统消息] {display_content}"
                elif msg_type == "link":
                    # 尝试提取链接标题
                    if display_content and "<title>" in display_content:
                        import re as _re
                        m = _re.search(r"<title>(.*?)</title>", display_content)
                        display_content = f"[链接] {m.group(1)}" if m else "[链接]"
                    else:
                        display_content = "[链接/文件]"

                record = {
                    "local_id": local_id,
                    "sender": sender,
                    "content": display_content,
                    "timestamp": create_time,
                    "type": msg_type,
                    "local_type": base_local_type,
                }
                if emoji_meta:
                    emoji_id = build_emoji_id(emoji_meta, local_id)
                    record["emoji_ref"] = emoji_id
                    existing = emoji_records.get(emoji_id)
                    if not existing:
                        emoji_records[emoji_id] = {
                            "emoji_id": emoji_id,
                            "md5": emoji_meta.get("md5"),
                            "type": emoji_meta.get("type"),
                            "len": emoji_meta.get("len"),
                            "cdnurl": emoji_meta.get("cdnurl"),
                            "thumburl": emoji_meta.get("thumburl"),
                            "encrypturl": emoji_meta.get("encrypturl"),
                            "aeskey": emoji_meta.get("aeskey"),
                            "productid": emoji_meta.get("productid"),
                            "designerid": emoji_meta.get("designerid"),
                            "thumbmd5": emoji_meta.get("thumbmd5"),
                            "androidmd5": emoji_meta.get("androidmd5"),
                            "androidlen": emoji_meta.get("androidlen"),
                            "fromusername": emoji_meta.get("fromusername"),
                            "tousername": emoji_meta.get("tousername"),
                            "externurl": emoji_meta.get("externurl"),
                            "externmd5": emoji_meta.get("externmd5"),
                            "first_local_id": local_id,
                            "first_timestamp": create_time,
                            "occurrence_count": 1,
                        }
                    else:
                        existing["occurrence_count"] = existing.get("occurrence_count", 0) + 1
                messages.append(record)
        finally:
            conn.close()
    except Exception as e:
        print(f"[!] 读取 {db_path} 失败: {e}", file=sys.stderr)

    return messages, emoji_records


def main():
    parser = argparse.ArgumentParser(description="提取指定联系人的微信消息")
    parser.add_argument("--decrypted-dir", required=True)
    parser.add_argument("--contact", required=True, help="联系人名字（备注名/昵称/wxid）")
    parser.add_argument("--output", help="输出 messages.json 文件路径；不传时可配合 --output-dir 使用")
    parser.add_argument("--output-dir", help="按联系人自动创建导出目录，例如 data/contacts")
    args = parser.parse_args()

    if not args.output and not args.output_dir:
        parser.error("必须提供 --output 或 --output-dir 其中之一")

    decrypted_dir = os.path.abspath(args.decrypted_dir)
    names = load_contacts(decrypted_dir)
    if not names:
        print(json.dumps({"error": "无法加载联系人数据"}))
        sys.exit(1)

    contact_username = find_username(args.contact, names)
    if not contact_username:
        print(json.dumps({"error": f"找不到联系人: {args.contact}"}))
        sys.exit(1)

    contact_display = names.get(contact_username, contact_username)
    own_wxid = get_own_wxid(decrypted_dir)
    table_hash = hashlib.md5(contact_username.encode()).hexdigest()
    table_name = f"Msg_{table_hash}"

    msg_dir = os.path.join(decrypted_dir, "message")
    if not os.path.exists(msg_dir):
        print(json.dumps({"error": f"消息目录不存在: {msg_dir}"}))
        sys.exit(1)

    msg_dbs = sorted([
        f for f in os.listdir(msg_dir)
        if re.match(r"message_\d+\.db$", f)
    ])

    bundle = resolve_bundle_paths(
        contact_display=contact_display,
        contact_username=contact_username,
        output=args.output,
        output_dir=args.output_dir,
    )

    all_messages = []
    emoji_catalog = {}
    for db_file in msg_dbs:
        db_path = os.path.join(msg_dir, db_file)
        conn = sqlite3.connect(db_path)
        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ).fetchone()
            if not exists:
                conn.close()
                continue

            id_to_username = {}
            try:
                for rowid, user_name in conn.execute("SELECT rowid, user_name FROM Name2Id").fetchall():
                    if user_name:
                        id_to_username[rowid] = user_name
            except sqlite3.OperationalError:
                pass
            conn.close()

            msgs, emojis = extract_messages_from_db(db_path, table_name, id_to_username, own_wxid,
                                                    contact_username, contact_display)
            all_messages.extend(msgs)
            for emoji_id, meta in emojis.items():
                if emoji_id not in emoji_catalog:
                    emoji_catalog[emoji_id] = meta
                else:
                    emoji_catalog[emoji_id]["occurrence_count"] = (
                        emoji_catalog[emoji_id].get("occurrence_count", 0)
                        + meta.get("occurrence_count", 0)
                    )
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    # 按时间排序
    all_messages.sort(key=lambda m: m["timestamp"])

    result = {
        "contact_username": contact_username,
        "contact_display": contact_display,
        "own_wxid": own_wxid or "unknown",
        "bundle_dir": bundle["bundle_dir"],
        "total": len(all_messages),
        "emoji_total": sum(1 for m in all_messages if m.get("type") == "emoji"),
        "emoji_catalog_file": os.path.basename(bundle["emojis_path"]),
        "messages": all_messages,
    }

    emoji_result = {
        "contact_username": contact_username,
        "contact_display": contact_display,
        "bundle_dir": bundle["bundle_dir"],
        "total_messages": result["emoji_total"],
        "unique_emojis": len(emoji_catalog),
        "emoji_records": sorted(
            emoji_catalog.values(),
            key=lambda x: (x.get("first_timestamp", 0), x.get("emoji_id", "")),
        ),
    }

    os.makedirs(bundle["bundle_dir"], exist_ok=True)
    with open(bundle["messages_path"], "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(bundle["emojis_path"], "w", encoding="utf-8") as f:
        json.dump(emoji_result, f, ensure_ascii=False, indent=2)

    print(f"[+] 已提取 {len(all_messages)} 条消息 -> {bundle['messages_path']}", file=sys.stderr)
    print(f"[+] 已导出 {result['emoji_total']} 条表情消息 -> {bundle['emojis_path']}", file=sys.stderr)
    print(json.dumps({
        "status": "ok",
        "total": len(all_messages),
        "emoji_total": result["emoji_total"],
        "contact": contact_display,
        "bundle_dir": bundle["bundle_dir"],
        "messages_path": bundle["messages_path"],
        "emojis_path": bundle["emojis_path"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
