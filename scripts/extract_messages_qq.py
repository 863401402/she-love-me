"""
extract_messages_qq.py — 通过 QQ Chat Exporter (QCE) REST API 提取 QQ 消息
并转换为与 extract_messages.py 相同的 messages.json 格式

用法:
    python scripts/extract_messages_qq.py \
        --token <access_token> \
        --contact <好友显示名/QQ号> \
        --output data/messages.json \
        [--port 40653] [--host 127.0.0.1] [--chat-type 1]

chat-type: 1=私聊（默认），2=群聊
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error


# ─────────────────────────────────────────────────────────
# HTTP 工具
# ─────────────────────────────────────────────────────────

def call_get(base_url: str, path: str, token: str) -> dict:
    url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"[错误] HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[错误] 无法连接到 QCE 服务: {e.reason}", file=sys.stderr)
        print(f"请确认 NapCat + QCE 插件已启动，地址: {base_url}", file=sys.stderr)
        sys.exit(1)


def call_post(base_url: str, path: str, token: str, body: dict, timeout: int = 30) -> dict:
    url = f"{base_url}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"[错误] HTTP {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[错误] 请求失败: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ─────────────────────────────────────────────────────────
# 消息类型映射（QCE CleanMessage.type → 我们的格式）
# ─────────────────────────────────────────────────────────

QCE_TYPE_MAP = {
    "text":    "text",
    "image":   "image",
    "voice":   "voice",
    "audio":   "voice",
    "video":   "video",
    "sticker": "emoji",
    "face":    "emoji",
    "file":    "link",
    "link":    "link",
    "location":"link",
    "system":  "system",
    "mixed":   "text",   # 图文混排，取文字部分
    "unknown": "system",
}


def map_type(qce_type: str, recalled: bool) -> str:
    if recalled:
        return "revoke"
    return QCE_TYPE_MAP.get(qce_type, "system")


# ─────────────────────────────────────────────────────────
# 主逻辑
# ─────────────────────────────────────────────────────────

def get_self_uid(base_url: str, token: str) -> tuple[str, str]:
    """返回 (uid, uin)"""
    resp = call_get(base_url, "/api/system/info", token)
    if resp.get("success"):
        self_info = resp.get("data", {}).get("napcat", {}).get("selfInfo", {})
        return self_info.get("uid", ""), str(self_info.get("uin", ""))
    return "", ""


def find_friend(base_url: str, token: str, contact: str) -> dict | None:
    """根据名字/QQ号/备注模糊匹配好友，返回匹配的好友 dict"""
    resp = call_get(base_url, "/api/friends?limit=9999", token)
    if not resp.get("success"):
        return None
    friends = resp.get("data", {}).get("friends", [])
    contact_lower = contact.lower()

    # 精确匹配优先（QQ号、uid）
    for f in friends:
        if str(f.get("uin", "")) == contact or f.get("uid", "") == contact:
            return f

    # 模糊匹配（备注、昵称）
    for f in friends:
        remark = (f.get("remark") or "").lower()
        nick = (f.get("nick") or "").lower()
        if contact_lower in remark or contact_lower in nick:
            return f

    return None


def start_export_task(base_url: str, token: str, peer_uid: str, chat_type: int) -> dict:
    """发起 JSON 导出任务，返回任务信息"""
    body = {
        "peer": {
            "chatType": chat_type,
            "peerUid": peer_uid,
        },
        "format": "JSON",
    }
    resp = call_post(base_url, "/api/messages/export", token, body, timeout=10)
    if not resp.get("success"):
        print(f"[错误] 创建导出任务失败: {resp}", file=sys.stderr)
        sys.exit(1)
    return resp.get("data", {})


def poll_task(base_url: str, token: str, task_id: str, max_wait: int = 600) -> dict:
    """轮询任务状态直到完成，返回完成的任务信息"""
    print(f"[等待] 导出任务 {task_id} 进行中...", flush=True)
    deadline = time.time() + max_wait
    last_progress = -1

    while time.time() < deadline:
        resp = call_get(base_url, f"/api/tasks/{task_id}", token)
        if not resp.get("success"):
            time.sleep(2)
            continue

        task = resp.get("data", {})
        status = task.get("status", "")
        progress = task.get("progress", 0)

        if progress != last_progress:
            msg_count = task.get("messageCount", "?")
            print(f"  [{status}] 进度: {progress}% | 消息数: {msg_count}", flush=True)
            last_progress = progress

        if status == "completed":
            return task
        if status in ("failed", "cancelled"):
            err = task.get("error", "未知错误")
            print(f"[错误] 导出任务{status}: {err}", file=sys.stderr)
            sys.exit(1)

        time.sleep(3)

    print(f"[错误] 导出超时（{max_wait}秒）", file=sys.stderr)
    sys.exit(1)


def convert_messages(qce_messages: list, self_uid: str, contact_display: str) -> dict:
    """将 QCE CleanMessage[] 转换为我们的 messages.json 格式"""
    converted = []
    contact_uid = None

    for i, msg in enumerate(qce_messages):
        sender_uid = msg.get("sender", {}).get("uid", "")
        sender_uin = str(msg.get("sender", {}).get("uin", ""))
        is_me = (sender_uid == self_uid) if self_uid else False

        # 推断联系人 uid（第一条不是自己发的消息的 sender）
        if not is_me and contact_uid is None:
            contact_uid = sender_uid

        recalled = msg.get("recalled", False)
        msg_type = map_type(msg.get("type", "text"), recalled)

        # 提取文字内容
        content_obj = msg.get("content", {})
        if recalled:
            content = "[撤回了一条消息]"
        elif msg_type == "text":
            content = content_obj.get("text", "")
        elif msg_type == "image":
            content = "[图片]"
        elif msg_type == "voice":
            content = "[语音]"
        elif msg_type == "video":
            content = "[视频]"
        elif msg_type == "emoji":
            content = "[表情]"
        elif msg_type == "link":
            content = content_obj.get("text", "[链接/文件]") or "[链接/文件]"
        elif msg_type == "system":
            content = content_obj.get("text", "[系统消息]") or "[系统消息]"
        else:
            content = content_obj.get("text", "")

        converted.append({
            "local_id": i + 1,
            "sender": "me" if is_me else "them",
            "content": content,
            "timestamp": msg.get("timestamp", 0),
            "type": msg_type,
        })

    return {
        "source": "qq",
        "contact_username": contact_uid or "",
        "contact_display": contact_display,
        "own_wxid": self_uid,  # 字段名保持兼容，实际是 QQ uid
        "total": len(converted),
        "messages": converted,
    }


def main():
    parser = argparse.ArgumentParser(description="提取 QQ 消息（通过 QCE API）")
    parser.add_argument("--token", required=True, help="QCE access token")
    parser.add_argument("--contact", required=True, help="好友显示名、备注或 QQ 号")
    parser.add_argument("--output", default="data/messages.json", help="输出路径（默认 data/messages.json）")
    parser.add_argument("--port", type=int, default=40653, help="QCE 服务端口（默认 40653）")
    parser.add_argument("--host", default="127.0.0.1", help="QCE 服务地址（默认 127.0.0.1）")
    parser.add_argument("--chat-type", type=int, default=1, choices=[1, 2], help="1=私聊（默认），2=群聊")
    parser.add_argument("--uid", help="直接指定好友 uid（跳过搜索）")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    # 1. 获取当前用户 uid
    print("[步骤 1/4] 获取当前登录用户信息...")
    self_uid, self_uin = get_self_uid(base_url, args.token)
    if self_uid:
        print(f"  当前用户: QQ {self_uin} (uid: {self_uid})")
    else:
        print("  [警告] 未能获取当前用户 uid，消息方向判断可能不准确")

    # 2. 查找联系人
    peer_uid = args.uid
    contact_display = args.contact

    if not peer_uid:
        print(f"[步骤 2/4] 搜索联系人 '{args.contact}'...")
        friend = find_friend(base_url, args.token, args.contact)
        if not friend:
            print(f"[错误] 未找到联系人: {args.contact}", file=sys.stderr)
            print("请使用 list_contacts_qq.py 查看可用联系人", file=sys.stderr)
            sys.exit(1)
        peer_uid = friend.get("uid", "")
        remark = friend.get("remark", "")
        nick = friend.get("nick", "")
        contact_display = remark or nick or args.contact
        print(f"  找到: {contact_display} (QQ: {friend.get('uin', '?')}, uid: {peer_uid})")
    else:
        print(f"[步骤 2/4] 使用指定 uid: {peer_uid}")

    # 3. 发起导出任务
    print("[步骤 3/4] 创建 QCE 导出任务...")
    task_info = start_export_task(base_url, args.token, peer_uid, args.chat_type)
    task_id = task_info.get("taskId") or task_info.get("id", "")
    if not task_id:
        print(f"[错误] 未返回任务 ID: {task_info}", file=sys.stderr)
        sys.exit(1)
    print(f"  任务 ID: {task_id}")

    # 4. 等待完成
    print("[步骤 4/4] 等待导出完成（大量消息可能需要数分钟）...")
    completed_task = poll_task(base_url, args.token, task_id)

    # 读取导出文件
    file_path = completed_task.get("filePath") or completed_task.get("fileName", "")
    if not file_path or not os.path.exists(file_path):
        print(f"[错误] 导出文件不存在: {file_path}", file=sys.stderr)
        print(f"任务信息: {completed_task}", file=sys.stderr)
        sys.exit(1)

    print(f"  导出文件: {file_path}")
    print(f"  消息数量: {completed_task.get('messageCount', '?')}")

    with open(file_path, encoding="utf-8") as f:
        qce_data = json.load(f)

    qce_messages = qce_data.get("messages", [])
    if not qce_messages:
        print("[警告] 导出文件中没有消息")

    # 转换格式
    result = convert_messages(qce_messages, self_uid, contact_display)

    # 写入输出
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n完成！共 {result['total']} 条消息 → {args.output}")


if __name__ == "__main__":
    main()
