"""Bounded context retrieval for an agent, within the user's selected scope."""

import argparse
import json
import sys
from datetime import datetime, timezone

from bundle_store import atomic_json
from message_normalizer import analytical_text, normalize_payload


def query_context(payload, message_ids=None, keyword=None, since=None, until=None,
                  before=10, after=10, max_matches=5, max_messages=100, max_chars=20000,
                  expected_digest=None):
    if bool(message_ids) == bool(keyword):
        raise ValueError("请选择消息 ID 或关键词中的一种查询方式")
    if keyword is not None and not keyword.strip():
        raise ValueError("关键词不能为空白")
    if message_ids and len(message_ids) > 20:
        raise ValueError("每轮最多查询 20 个消息 ID")
    if not 0 <= before <= 50 or not 0 <= after <= 50:
        raise ValueError("上下文各限制在 0–50 条")
    if not 1 <= max_matches <= 20 or not 1 <= max_messages <= 200 or not 1 <= max_chars <= 100000:
        raise ValueError("查询预算超出允许范围")
    data = normalize_payload(payload)
    if expected_digest and expected_digest != data["messages_digest"]:
        raise ValueError("消息数据已更新；请重新统计和采样后再补采样")

    def date_boundary(value):
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() if value else None

    lower, upper = date_boundary(since), date_boundary(until)
    if upper is not None:
        upper += 86400  # inclusive end date, matching sampling's UTC date convention
    if lower is not None and upper is not None and lower >= upper:
        raise ValueError("起始日期不能晚于结束日期")
    messages = [m for m in data["messages"] if (lower is None or m["timestamp"] >= lower)
                and (upper is None or m["timestamp"] < upper)]
    ids = set(message_ids or [])
    if ids and not ids <= {m["message_id"] for m in messages}:
        raise ValueError("消息 ID 不存在或不在已选时间范围内")
    anchors = [i for i, m in enumerate(messages) if m["message_id"] in ids] if ids else [
        i for i, m in enumerate(messages) if keyword.casefold() in
        (analytical_text(m) or m.get("content", "")).casefold()]
    selected = set()
    for index in anchors[:max_matches]:
        selected.update(range(max(0, index - before), min(len(messages), index + after + 1)))
    result_messages = []
    chars = 0
    for index in sorted(selected):
        message = messages[index]
        cost = len(json.dumps(message, ensure_ascii=False))
        if len(result_messages) >= max_messages or chars + cost > max_chars:
            break
        result_messages.append(message)
        chars += cost
    returned_ids = {m["message_id"] for m in result_messages}
    return {
        "status": "ok", "messages_digest": data["messages_digest"],
        "scope": {"since": since, "until": until, "timezone": "UTC", "message_count": len(messages)},
        "query": {"message_ids": sorted(ids), "keyword": keyword},
        "matched_count": len(anchors), "anchor_message_ids": [messages[i]["message_id"] for i in anchors[:max_matches]],
        "returned_anchor_ids": [messages[i]["message_id"] for i in anchors[:max_matches]
                                if messages[i]["message_id"] in returned_ids],
        "messages": result_messages, "returned_count": len(result_messages),
        "truncated": len(anchors) > max_matches or len(result_messages) < len(selected),
        "budget": {"max_messages": max_messages, "max_chars": max_chars, "used_chars": chars},
        "note": "补采样仅用于核对语境；未匹配到关键词不代表事件从未发生。",
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 按消息 ID 或关键词补取有预算的上下文")
    parser.add_argument("--input", required=True)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--message-id", action="append")
    selector.add_argument("--keyword")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--before", type=int, default=10)
    parser.add_argument("--after", type=int, default=10)
    parser.add_argument("--max-matches", type=int, default=5)
    parser.add_argument("--max-messages", type=int, default=100)
    parser.add_argument("--max-chars", type=int, default=20000)
    parser.add_argument("--expected-digest", required=True)
    parser.add_argument("--output", help="保存补采样 JSON；省略则输出 JSON 到终端")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    result = query_context(data, args.message_id, args.keyword, args.since, args.until,
                           args.before, args.after, args.max_matches, args.max_messages,
                           args.max_chars, args.expected_digest)
    if args.output:
        atomic_json(args.output, result)
        print(json.dumps({key: value for key, value in result.items() if key != "messages"}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
