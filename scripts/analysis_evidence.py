"""Validate evidence references and bind analysis to the current message dataset."""

import re

from message_normalizer import normalize_payload


def evidence_entries(value, path="analysis"):
    if isinstance(value, dict):
        if "evidence_message_ids" in value or "stats_fields" in value:
            yield path, value
        for key, child in value.items():
            yield from evidence_entries(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from evidence_entries(child, f"{path}[{index}]")


def resolve_stats_field(stats, field):
    if not isinstance(field, str) or not field:
        raise ValueError("stats_fields 必须是非空统计字段路径")
    value = stats
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"统计证据字段不存在：{field}")
        value = value[part]
    return value


def validate_evidence(stats, analysis, payload=None):
    if not isinstance(stats, dict) or not isinstance(analysis, dict):
        raise ValueError("统计和分析 JSON 顶层必须是对象")
    entries = list(evidence_entries(analysis))
    strict = analysis.get("schema_version") == "2.1"
    normalized = normalize_payload(payload) if payload is not None else None
    if strict and not normalized:
        raise ValueError("证据版分析需要 --messages 原始消息文件")
    if normalized:
        current_digest = normalized["messages_digest"]
        for label, expected in (("统计", stats.get("messages_digest")),
                                ("分析", analysis.get("messages_digest"))):
            if expected and expected != current_digest:
                raise ValueError(f"{label}与当前消息数据不一致；请重新统计或分析")
        if strict and (analysis.get("messages_digest") != current_digest or
                       stats.get("messages_digest") != current_digest):
            raise ValueError("证据版分析和统计都必须记录当前 messages_digest")
    if strict:
        calibration = stats.get("balance_calibration")
        asymmetry = analysis.get("emotional_asymmetry")
        if calibration and asymmetry is not None:
            if not isinstance(asymmetry, dict) or asymmetry.get("symmetry_score") != calibration["symmetry_score"]:
                raise ValueError("分析中的对称性评分与统计引擎不一致；请原样复制 balance_calibration.symmetry_score")
        for section in ("key_findings", "danger_warnings"):
            items = analysis.get(section, [])
            if not isinstance(items, list):
                raise ValueError(f"{section} 必须是数组")
            for item in items:
                if not isinstance(item, dict) or not item.get("evidence_message_ids"):
                    raise ValueError(f"{section} 中每条结论必须关联原始消息")
    index = {m["message_id"]: m for m in normalized["messages"]} if normalized else {}
    for path, entry in entries:
        if entry.get("evidence_level") not in (None, "high", "medium", "low", "insufficient"):
            raise ValueError(f"{path} 的证据等级无效")
        ids = entry.get("evidence_message_ids", [])
        fields = entry.get("stats_fields", [])
        if not isinstance(ids, list) or not isinstance(fields, list):
            raise ValueError(f"{path} 的证据引用必须是数组")
        for message_id in ids:
            if not isinstance(message_id, str) or not re.fullmatch(r"msg_[0-9a-f]{64}", message_id):
                raise ValueError(f"{path} 的消息 ID 格式无效")
            if message_id not in index:
                raise ValueError(f"{path} 引用了不存在的消息；请提供匹配的 --messages 文件")
        for field in fields:
            value = resolve_stats_field(stats, field)
            if value is None and entry.get("evidence_level") in ("high", "medium"):
                raise ValueError(f"{path} 将缺失统计字段作为有效证据：{field}")
        quote = entry.get("quote")
        if quote and ids and not any(
            str(quote) in str(index[mid].get("content", "")) or
            str(quote) in str(index[mid].get("transcript", "")) for mid in ids
        ):
            raise ValueError(f"{path} 的引用原文与关联消息不符")
    return index, entries
