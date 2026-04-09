"""
stats_analyzer.py - 统计分析引擎

输入: messages.json (extract_messages.py 的输出)
输出: stats.json (纯数字统计，供 Claude AI 分析和 HTML 报告使用)

统计维度:
  - 基础数据: 消息总量、双方占比、时间跨度
  - 主动性: 谁先发起对话
  - 回复速度: 双方平均回复时间
  - 消息长度: 双方平均字数
  - 轰炸检测: 连续发多条未回
  - 冷淡回复: "嗯" "哦" "好" 等单字/敷衍
  - 晚安分析: 谁先说晚安
  - 活跃时段分布
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 冷淡回复词库
COLD_WORDS = {"嗯", "哦", "好", "行", "哦哦", "嗯嗯", "好的", "ok", "OK", "好吧",
              "随便", "可以", "知道了", "知道", "哈", "哈哈", "em", "em...", "emmm"}

# 早安/晚安关键词
GOODNIGHT_WORDS = {"晚安", "good night", "goodnight", "晚安啦", "晚安嗷", "晚安哦"}
GOODMORNING_WORDS = {"早安", "早上好", "早啊", "早哦", "good morning", "早", "早起了"}

# 对话间隔阈值（秒）: 超过此时间视为新对话开始
NEW_CONVERSATION_GAP = 3 * 3600  # 3小时


def load_messages(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data


def filter_text_messages(messages):
    """只保留文字类型消息用于内容分析"""
    return [m for m in messages if m["type"] == "text" and m["sender"] in ("me", "them")]


def detect_conversations(messages):
    """将消息序列切分为对话（session），返回每个对话的起始人"""
    if not messages:
        return []

    conversations = []
    current = [messages[0]]

    for msg in messages[1:]:
        gap = msg["timestamp"] - current[-1]["timestamp"]
        if gap > NEW_CONVERSATION_GAP:
            conversations.append(current)
            current = [msg]
        else:
            current.append(msg)

    if current:
        conversations.append(current)

    return conversations


def analyze_reply_times(messages):
    """计算双方平均回复时间（秒）"""
    my_reply_times = []
    their_reply_times = []
    last_sender = None
    last_time = None

    for msg in messages:
        if last_sender is not None and msg["sender"] != last_sender:
            gap = msg["timestamp"] - last_time
            if 10 <= gap <= 86400:  # 忽略太短（同时发）和太长（隔天）
                if msg["sender"] == "me":
                    my_reply_times.append(gap)
                else:
                    their_reply_times.append(gap)
        last_sender = msg["sender"]
        last_time = msg["timestamp"]

    avg_my = sum(my_reply_times) / len(my_reply_times) if my_reply_times else 0
    avg_their = sum(their_reply_times) / len(their_reply_times) if their_reply_times else 0
    return avg_my, avg_their


def detect_bombing(messages):
    """检测连续发送多条未回的情况（轰炸）"""
    my_bombs = 0
    their_bombs = 0
    my_consecutive = 0
    their_consecutive = 0
    my_max_consecutive = 0
    their_max_consecutive = 0

    last_sender = None
    for msg in messages:
        sender = msg["sender"]
        if sender == last_sender:
            if sender == "me":
                my_consecutive += 1
            else:
                their_consecutive += 1
        else:
            if last_sender == "me" and my_consecutive >= 3:
                my_bombs += 1
            if last_sender == "them" and their_consecutive >= 3:
                their_bombs += 1
            my_max_consecutive = max(my_max_consecutive, my_consecutive)
            their_max_consecutive = max(their_max_consecutive, their_consecutive)
            if sender == "me":
                my_consecutive = 1
                their_consecutive = 0
            else:
                their_consecutive = 1
                my_consecutive = 0
        last_sender = sender

    return {
        "my_bomb_count": my_bombs,
        "their_bomb_count": their_bombs,
        "my_max_consecutive": my_max_consecutive,
        "their_max_consecutive": their_max_consecutive,
    }


def detect_cold_replies(text_messages):
    """检测冷淡回复"""
    my_cold = 0
    their_cold = 0
    cold_word_count = defaultdict(int)

    for msg in text_messages:
        content = msg["content"].strip()
        is_cold = content in COLD_WORDS or len(content) <= 2
        if is_cold:
            cold_word_count[content] += 1
            if msg["sender"] == "me":
                my_cold += 1
            else:
                their_cold += 1

    return {
        "my_cold_count": my_cold,
        "their_cold_count": their_cold,
        "cold_words": dict(sorted(cold_word_count.items(), key=lambda x: -x[1])[:10]),
    }


def detect_unanswered(messages):
    """检测一方发消息后对方长时间未回（>2小时）"""
    my_unanswered = 0
    their_unanswered = 0
    last_sender = None
    last_time = None
    pending_sender = None

    for msg in messages:
        if last_sender is not None and msg["sender"] != last_sender:
            gap = msg["timestamp"] - last_time
            if gap > 7200 and pending_sender:  # >2小时
                if pending_sender == "me":
                    my_unanswered += 1
                else:
                    their_unanswered += 1
            pending_sender = None
        else:
            pending_sender = msg["sender"]

        last_sender = msg["sender"]
        last_time = msg["timestamp"]

    return {"my_unanswered": my_unanswered, "their_unanswered": their_unanswered}


def detect_goodnight(text_messages):
    """检测晚安/早安，判断谁先说"""
    my_goodnight = 0
    their_goodnight = 0

    for msg in text_messages:
        content = msg["content"].lower().strip()
        if any(w in content for w in GOODNIGHT_WORDS):
            if msg["sender"] == "me":
                my_goodnight += 1
            else:
                their_goodnight += 1

    return {"my_goodnight": my_goodnight, "their_goodnight": their_goodnight}


def compute_scores(stats):
    """计算舔狗指数、被爱指数、冷淡指数（0-100）"""
    basic = stats["basic"]
    initiative = stats["initiative"]
    reply = stats["reply_speed"]
    bombing = stats["bombing"]
    unanswered = stats["unanswered"]
    goodnight = stats["goodnight"]
    cold = stats["cold_response"]

    total = basic["total_messages"]
    my_total = basic["my_messages"]
    their_total = basic["their_messages"]

    # === 舔狗指数 ===
    simp_score = 0.0

    # 消息占比（你发超过60%加分）
    my_ratio = my_total / total if total > 0 else 0.5
    simp_score += 20 * min(my_ratio / 0.7, 1.0)

    # 主动发起占比
    total_starts = initiative["my_starts"] + initiative["their_starts"]
    my_start_ratio = initiative["my_starts"] / total_starts if total_starts > 0 else 0.5
    simp_score += 25 * min(my_start_ratio / 0.75, 1.0)

    # 回复速度差（你比对方快多少）
    my_speed = reply["my_avg_seconds"]
    their_speed = reply["their_avg_seconds"]
    if their_speed > 0 and my_speed > 0:
        speed_ratio = their_speed / my_speed
        simp_score += 20 * min(speed_ratio / 10, 1.0)
    elif my_speed > 0 and their_speed == 0:
        simp_score += 20

    # 连续轰炸
    bomb_ratio = bombing["my_bomb_count"] / max(total_starts, 1)
    simp_score += 15 * min(bomb_ratio / 0.3, 1.0)

    # 晚安主动率
    total_goodnight = goodnight["my_goodnight"] + goodnight["their_goodnight"]
    if total_goodnight > 0:
        my_gn_ratio = goodnight["my_goodnight"] / total_goodnight
        simp_score += 10 * min(my_gn_ratio / 0.8, 1.0)

    # 已读不回忍受
    if unanswered["my_unanswered"] > 5:
        simp_score += 10

    simp_index = min(int(simp_score), 100)

    # === 被爱指数 ===
    loved_score = 0.0

    # 对方消息占比
    their_ratio = their_total / total if total > 0 else 0.5
    loved_score += 20 * min(their_ratio / 0.5, 1.0)

    # 对方主动发起
    loved_score += 25 * min(initiative["their_starts"] / max(total_starts * 0.4, 1), 1.0)

    # 对方回复速度快
    if their_speed > 0 and my_speed > 0:
        their_responsiveness = my_speed / their_speed
        loved_score += 20 * min(their_responsiveness / 3, 1.0)

    # 对方消息长（用心）
    my_len = stats["message_length"]["my_avg_chars"]
    their_len = stats["message_length"]["their_avg_chars"]
    if my_len > 0:
        len_ratio = their_len / my_len
        loved_score += 15 * min(len_ratio / 1.0, 1.0)

    # 对方说晚安主动
    if total_goodnight > 0:
        their_gn_ratio = goodnight["their_goodnight"] / total_goodnight
        loved_score += 10 * min(their_gn_ratio / 0.6, 1.0)

    # 对方不敷衍（冷淡少）
    their_cold_ratio = cold["their_cold_count"] / max(their_total, 1)
    loved_score += 10 * (1 - min(their_cold_ratio / 0.3, 1.0))

    loved_index = min(int(loved_score), 100)

    # === 冷淡指数（对方对你的冷淡程度）===
    cold_score = 0.0
    cold_ratio = cold["their_cold_count"] / max(their_total, 1)
    cold_score += 40 * min(cold_ratio / 0.3, 1.0)
    if their_speed > 0 and my_speed > 0 and their_speed > my_speed * 5:
        cold_score += 30
    if their_total > 0 and my_total / their_total > 2:
        cold_score += 30
    cold_index = min(int(cold_score), 100)

    return {
        "simp_index": simp_index,
        "loved_index": loved_index,
        "cold_index": cold_index,
    }


def fmt_duration(seconds):
    if seconds < 60:
        return f"{int(seconds)} 秒"
    if seconds < 3600:
        return f"{int(seconds / 60)} 分钟"
    return f"{seconds / 3600:.1f} 小时"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = load_messages(args.input)
    messages = data.get("messages", [])
    contact_display = data.get("contact_display", "对方")

    if not messages:
        print(json.dumps({"error": "没有消息"}))
        sys.exit(1)

    # 只分析 me/them 的消息
    valid = [m for m in messages if m["sender"] in ("me", "them")]
    text_msgs = filter_text_messages(valid)

    my_msgs = [m for m in valid if m["sender"] == "me"]
    their_msgs = [m for m in valid if m["sender"] == "them"]
    total = len(valid)

    # 时间范围
    timestamps = [m["timestamp"] for m in valid]
    date_start = datetime.fromtimestamp(min(timestamps)).strftime("%Y-%m-%d")
    date_end = datetime.fromtimestamp(max(timestamps)).strftime("%Y-%m-%d")
    total_days = max((max(timestamps) - min(timestamps)) // 86400, 1)

    # 消息长度（只算文字）
    my_text = [m for m in text_msgs if m["sender"] == "me"]
    their_text = [m for m in text_msgs if m["sender"] == "them"]
    my_avg_len = sum(len(m["content"]) for m in my_text) / len(my_text) if my_text else 0
    their_avg_len = sum(len(m["content"]) for m in their_text) / len(their_text) if their_text else 0

    # 对话发起统计
    conversations = detect_conversations(valid)
    my_starts = sum(1 for c in conversations if c[0]["sender"] == "me")
    their_starts = sum(1 for c in conversations if c[0]["sender"] == "them")

    # 回复速度
    avg_my_reply, avg_their_reply = analyze_reply_times(valid)

    # 轰炸
    bombing = detect_bombing(valid)

    # 冷淡
    cold = detect_cold_replies(text_msgs)

    # 未回复
    unanswered = detect_unanswered(valid)

    # 晚安
    goodnight = detect_goodnight(text_msgs)

    # 活跃时段
    active_hours = defaultdict(int)
    for m in valid:
        hour = datetime.fromtimestamp(m["timestamp"]).hour
        active_hours[str(hour)] += 1

    # 每日趋势（最近90天）
    daily_counts = defaultdict(int)
    for m in valid:
        day = datetime.fromtimestamp(m["timestamp"]).strftime("%Y-%m-%d")
        daily_counts[day] += 1
    daily_trend = [{"date": k, "count": v}
                   for k, v in sorted(daily_counts.items())[-90:]]

    # 消息类型统计
    type_counts = defaultdict(lambda: {"me": 0, "them": 0})
    for m in valid:
        type_counts[m["type"]][m["sender"]] += 1

    stats = {
        "contact": contact_display,
        "basic": {
            "total_messages": total,
            "my_messages": len(my_msgs),
            "their_messages": len(their_msgs),
            "my_ratio": round(len(my_msgs) / total, 3) if total > 0 else 0,
            "their_ratio": round(len(their_msgs) / total, 3) if total > 0 else 0,
            "date_range": [date_start, date_end],
            "total_days": total_days,
            "avg_daily": round(total / total_days, 1),
        },
        "initiative": {
            "my_starts": my_starts,
            "their_starts": their_starts,
            "my_start_ratio": round(my_starts / max(my_starts + their_starts, 1), 3),
        },
        "reply_speed": {
            "my_avg_seconds": round(avg_my_reply),
            "their_avg_seconds": round(avg_their_reply),
            "my_avg_human": fmt_duration(avg_my_reply),
            "their_avg_human": fmt_duration(avg_their_reply),
            "speed_ratio": round(avg_their_reply / max(avg_my_reply, 1), 1),
        },
        "message_length": {
            "my_avg_chars": round(my_avg_len, 1),
            "their_avg_chars": round(their_avg_len, 1),
        },
        "bombing": bombing,
        "cold_response": cold,
        "unanswered": unanswered,
        "goodnight": goodnight,
        "active_hours": dict(active_hours),
        "daily_trend": daily_trend,
        "message_types": {k: dict(v) for k, v in type_counts.items()},
    }

    stats["scores"] = compute_scores(stats)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    s = stats["scores"]
    print(f"[+] 分析完成: 舔狗={s['simp_index']} 被爱={s['loved_index']} 冷淡={s['cold_index']}", file=sys.stderr)
    print(json.dumps({"status": "ok", "scores": stats["scores"]}))


if __name__ == "__main__":
    main()
