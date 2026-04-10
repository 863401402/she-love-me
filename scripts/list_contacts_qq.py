"""
list_contacts_qq.py — 通过 QQ Chat Exporter (QCE) REST API 列出 QQ 好友
用法:
    python scripts/list_contacts_qq.py --token <access_token> [--port 40653] [--top 30]

输出格式与 list_contacts.py 一致，便于 SKILL 流程统一处理。
"""

import argparse
import json
import sys
import urllib.request
import urllib.error


def call_api(base_url: str, path: str, token: str) -> dict:
    url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"[错误] HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[错误] 无法连接到 QCE 服务: {e.reason}", file=sys.stderr)
        print("请确认 NapCat + QCE 插件已启动，默认端口 40653。", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="列出 QQ 好友（通过 QCE API）")
    parser.add_argument("--token", required=True, help="QCE access token")
    parser.add_argument("--port", type=int, default=40653, help="QCE 服务端口（默认 40653）")
    parser.add_argument("--host", default="127.0.0.1", help="QCE 服务地址（默认 127.0.0.1）")
    parser.add_argument("--top", type=int, default=30, help="展示前 N 个好友（默认 30）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    # 获取当前登录用户信息
    status = call_api(base_url, "/api/system/status", args.token)
    current_uid = None
    current_uin = None
    if status.get("success") and status.get("data"):
        d = status["data"]
        current_uid = d.get("uid") or d.get("selfInfo", {}).get("uid")
        current_uin = d.get("uin") or d.get("selfInfo", {}).get("uin")

    # 获取好友列表（一次取全量）
    data = call_api(base_url, "/api/friends?limit=9999", args.token)
    if not data.get("success"):
        print(f"[错误] 获取好友列表失败: {data}", file=sys.stderr)
        sys.exit(1)

    friends_raw = data.get("data", {}).get("friends", [])

    contacts = []
    for f in friends_raw:
        uid = f.get("uid", "")
        uin = f.get("uin", "")
        nick = f.get("nick", "")
        remark = f.get("remark") or ""
        display_name = remark if remark else nick if nick else uin

        contacts.append({
            "uid": uid,
            "uin": str(uin),
            "nick_name": nick,
            "remark": remark,
            "display_name": display_name,
            # QCE API 不直接提供消息数，保持为 0（后续可扩展）
            "message_count": 0,
        })

    if args.json:
        print(json.dumps(contacts, ensure_ascii=False, indent=2))
        return

    # 人类可读输出
    print(f"\n{'='*60}")
    print(f"当前登录 QQ: {current_uin or '未知'} (uid: {current_uid or '未知'})")
    print(f"好友总数: {len(contacts)}")
    print(f"{'='*60}")
    print(f"{'序号':<5} {'显示名称':<20} {'QQ号':<15} {'备注':<15}")
    print(f"{'-'*60}")

    shown = contacts[:args.top]
    for i, c in enumerate(shown, 1):
        remark_str = f"({c['remark']})" if c["remark"] else ""
        print(f"{i:<5} {c['display_name']:<20} {c['uin']:<15} {remark_str}")

    if len(contacts) > args.top:
        print(f"... 还有 {len(contacts) - args.top} 位好友未显示，使用 --top N 查看更多")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
