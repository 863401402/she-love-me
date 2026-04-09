"""
extract_messages.py - 提取指定联系人的全部消息

消息存储结构（WeChat 4.0）：
  - message/message_N.db -> 每个联系人有独立的 Msg_{md5(username)} 表
  - 列：local_id, local_type, create_time, real_sender_id, message_content, WCDB_CT_message_content
  - real_sender_id 通过 Name2Id 表解析为 username
  - WCDB_CT_message_content == 4 表示 zstd 压缩
  - local_type == 1 文本, 3 图片, 34 语音, 43 视频, 47 表情, 49 链接/文件, 50 通话, 10000 系统
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys

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
    """从 config.json 或目录结构推断自己的 wxid"""
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
                db_dir = cfg.get("db_dir", "")
                if db_dir and os.path.basename(db_dir) == "db_storage":
                    # D:\xwechat_files\<wxid>\db_storage
                    return os.path.basename(os.path.dirname(db_dir))
            except Exception:
                pass
    return None


def extract_messages_from_db(db_path, table_name, id_to_username, own_wxid, contact_username, contact_display):
    messages = []
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                f"SELECT local_id, local_type, create_time, real_sender_id, "
                f"message_content, WCDB_CT_message_content "
                f"FROM [{table_name}] ORDER BY create_time ASC"
            ).fetchall()

            for row in rows:
                local_id, local_type, create_time, real_sender_id, content, ct = row
                content = decompress_content(content, ct)
                msg_type = get_msg_type(local_type)

                # 判断发送方
                sender_username = id_to_username.get(real_sender_id, "")
                if own_wxid and sender_username == own_wxid:
                    sender = "me"
                elif sender_username == contact_username:
                    sender = "them"
                elif own_wxid and not sender_username:
                    # 无法确定，根据 real_sender_id 猜测
                    sender = "unknown"
                else:
                    sender = "them" if sender_username == contact_username else "me"

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

                messages.append({
                    "local_id": local_id,
                    "sender": sender,
                    "content": display_content,
                    "timestamp": create_time,
                    "type": msg_type,
                })
        finally:
            conn.close()
    except Exception as e:
        print(f"[!] 读取 {db_path} 失败: {e}", file=sys.stderr)

    return messages


def main():
    parser = argparse.ArgumentParser(description="提取指定联系人的微信消息")
    parser.add_argument("--decrypted-dir", required=True)
    parser.add_argument("--contact", required=True, help="联系人名字（备注名/昵称/wxid）")
    parser.add_argument("--output", required=True, help="输出 JSON 文件路径")
    args = parser.parse_args()

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

    all_messages = []
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

            msgs = extract_messages_from_db(db_path, table_name, id_to_username, own_wxid,
                                            contact_username, contact_display)
            all_messages.extend(msgs)
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
        "total": len(all_messages),
        "messages": all_messages,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[+] 已提取 {len(all_messages)} 条消息 -> {args.output}", file=sys.stderr)
    print(json.dumps({"status": "ok", "total": len(all_messages), "contact": contact_display}))


if __name__ == "__main__":
    main()
