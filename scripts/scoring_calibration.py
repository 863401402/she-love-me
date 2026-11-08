"""Deterministic balance indicators; these describe behavior, not affection."""

WEIGHTS = {"initiative": 0.3, "reply": 0.2, "resumption": 0.3, "messages": 0.2}


def calibrate_balance(stats):
    basic = stats.get("basic", {})
    initiative = stats.get("initiative", {})
    reply = stats.get("reply_speed", {})
    repair = stats.get("repair", {})
    dimensions = {}

    def count_dimension(name, left, right, minimum, fields):
        total = left + right
        dimensions[name] = {
            "value": round(2 * min(left, right) / total, 6) if total >= minimum else None,
            "weight": WEIGHTS[name], "sample_count": total, "minimum_samples": minimum,
            "reason": None if total >= minimum else f"需要至少 {minimum} 个样本，实际 {total}",
            "stats_fields": fields,
        }
        return left / total if total else None

    starts_share = count_dimension("initiative", initiative.get("my_starts", 0),
                                   initiative.get("their_starts", 0), 4,
                                   ["initiative.my_starts", "initiative.their_starts"])
    message_share = count_dimension("messages", basic.get("my_messages", 0),
                                    basic.get("their_messages", 0), 20,
                                    ["basic.my_messages", "basic.their_messages"])
    resumption_share = count_dimension("resumption", repair.get("me_repair_count", 0),
                                       repair.get("them_repair_count", 0), 2,
                                       ["repair.me_repair_count", "repair.them_repair_count"])
    mine, theirs = reply.get("my_median_seconds"), reply.get("their_median_seconds")
    my_n, their_n = reply.get("my_sample_count", 0), reply.get("their_sample_count", 0)
    usable_reply = mine is not None and theirs is not None and mine > 0 and theirs > 0 and min(my_n, their_n) >= 3
    dimensions["reply"] = {
        "value": round(2 * min(mine, theirs) / (mine + theirs), 6) if usable_reply else None,
        "weight": WEIGHTS["reply"], "sample_count": {"me": my_n, "them": their_n},
        "minimum_samples_per_person": 3,
        "reason": None if usable_reply else "双方各需至少 3 个有效回复间隔及正值中位数",
        "stats_fields": ["reply_speed.my_median_seconds", "reply_speed.their_median_seconds",
                         "reply_speed.my_sample_count", "reply_speed.their_sample_count"],
    }
    coverage = round(sum(item["weight"] for item in dimensions.values() if item["value"] is not None), 2)
    usable = coverage >= 0.7 and dimensions["initiative"]["value"] is not None and dimensions["messages"]["value"] is not None
    score = round(10 * sum(item["value"] * item["weight"] for item in dimensions.values()
                          if item["value"] is not None) / coverage, 1) if usable else None
    direction = "mixed_or_balanced"
    if starts_share is not None and message_share is not None:
        if min(starts_share, message_share) > 0.6:
            direction = "me"
        elif max(starts_share, message_share) < 0.4:
            direction = "them"
    return {
        "version": "2.2", "symmetry_score": score, "coverage": coverage,
        "evidence_level": "high" if usable and coverage == 1 else "medium" if usable else "insufficient",
        "reason": ("按有效维度权重归一化；缺少维度不能视为平衡" if usable
                   else "样本不足：需消息量与发起维度有效，且权重覆盖至少 70%"),
        "dimensions": dimensions,
        "investment_direction": {"observed_direction": direction,
                                 "my_message_share": message_share, "my_initiation_share": starts_share,
                                 "my_resumption_share": resumption_share},
        "limitations": "仅衡量可观察的聊天行为均衡；沉默后恢复不等于冲突修复，回复间隔不等于已读时间，评分不代表爱情概率。",
    }
