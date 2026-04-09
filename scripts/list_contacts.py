"""
list_contacts.py - 列出微信联系人及消息数量

从解密后的 SQLite 数据库读取：
  - contact/contact.db -> contact 表 (username, nick_name, remark)
  - message/message_N.db -> Name2Id + Msg_* 表计数
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


def get_display_name(row):
    username, nick_name, remark = row
    return remark or nick_name or username


def load_contacts(decrypted_dir):
    contact_db = os.path.join(decrypted_dir, "contact", "contact.db")
    if not os.path.exists(contact_db):
        print(f"[!] 找不到联系人数据库: {contact_db}", file=sys.stderr)
        return []

    contacts = []
    conn = sqlite3.connect(contact_db)
    try:
        rows = conn.execute(
            "SELECT username, nick_name, remark FROM contact WHERE username NOT LIKE '%@chatroom'"
        ).fetchall()
        for row in rows:
            username, nick_name, remark = row
            display = remark or nick_name or username
            # 过滤掉公众号和系统账号
            if username.startswith("gh_") or username in ("filehelper", "newsapp", "weixin", "fmessage"):
                continue
            contacts.append({
                "username": username,
                "nick_name": nick_name or "",
                "remark": remark or "",
                "display_name": display,
                "message_count": 0,
            })
    finally:
        conn.close()

    return contacts


def count_messages(decrypted_dir, contacts):
    """扫描 message/message_N.db 文件，统计每个联系人的消息数"""
    username_to_idx = {c["username"]: i for i, c in enumerate(contacts)}
    msg_dir = os.path.join(decrypted_dir, "message")
    if not os.path.exists(msg_dir):
        return

    msg_dbs = sorted([
        f for f in os.listdir(msg_dir)
        if re.match(r"message_\d+\.db$", f)
    ])

    for db_file in msg_dbs:
        db_path = os.path.join(msg_dir, db_file)
        try:
            conn = sqlite3.connect(db_path)
            try:
                # 通过 Name2Id 表找到 username -> table 的对应关系
                try:
                    id_rows = conn.execute("SELECT user_name FROM Name2Id").fetchall()
                except sqlite3.OperationalError:
                    continue

                for (user_name,) in id_rows:
                    if not user_name or user_name not in username_to_idx:
                        continue
                    table_hash = hashlib.md5(user_name.encode()).hexdigest()
                    table_name = f"Msg_{table_hash}"
                    try:
                        count = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
                        contacts[username_to_idx[user_name]]["message_count"] += count
                    except sqlite3.OperationalError:
                        pass
            finally:
                conn.close()
        except Exception:
            continue


def main():
    parser = argparse.ArgumentParser(description="列出微信联系人")
    parser.add_argument("--decrypted-dir", required=True, help="解密数据库目录")
    args = parser.parse_args()

    decrypted_dir = os.path.abspath(args.decrypted_dir)
    if not os.path.exists(decrypted_dir):
        print(json.dumps({"error": f"目录不存在: {decrypted_dir}"}))
        sys.exit(1)

    contacts = load_contacts(decrypted_dir)
    if not contacts:
        print(json.dumps({"error": "未找到联系人数据"}))
        sys.exit(1)

    count_messages(decrypted_dir, contacts)

    # 按消息数量排序，过滤掉 0 消息的
    contacts = [c for c in contacts if c["message_count"] > 0]
    contacts.sort(key=lambda c: c["message_count"], reverse=True)

    print(json.dumps(contacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
