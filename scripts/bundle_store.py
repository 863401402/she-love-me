"""Atomic, auditable incremental updates for normalized contact bundles."""

import json
import os
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from message_normalizer import digest, message_signature, normalize_payload


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".import-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update_bundle(payload, messages_path, source_path=None):
    incoming = normalize_payload(payload, drop_invalid=True)
    if not incoming["messages"]:
        raise ValueError("导入没有有效消息；保留现有联系人记录")
    path = Path(messages_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".import.lock")
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError("联系人正在导入或残留导入锁；确认没有导入进程后再处理锁文件") from exc
    try:
        os.close(lock_fd)
        old = normalize_payload(json.loads(path.read_text(encoding="utf-8-sig"))) if path.exists() else None
        if old and old["identity_namespace"] != incoming["identity_namespace"]:
            raise ValueError("来源、账号或联系人不一致；请使用独立输出目录，避免混合不同数据")
        if old and "import_history" not in old:
            # Preserve the pre-upgrade dataset before introducing native IDs.
            atomic_json(path.parent / "imports" / "legacy.json", old)
            available = {}
            for message in incoming["messages"]:
                available.setdefault(digest(message_signature(message)), []).append(message)
            for previous in old["messages"]:
                candidates = available.get(digest(message_signature(previous)), [])
                if previous["identity_method"] == "content_occurrence" and candidates:
                    match = candidates.pop(0)
                    if match["identity_method"] == "source_id":
                        previous["source_message_id"] = match["source_message_id"]
            old = normalize_payload(old)
        history = list(old.get("import_history", [])) if old else []
        batch_id = digest({"namespace": incoming["identity_namespace"],
                           "messages_digest": incoming["messages_digest"]})
        if any(batch["batch_id"] == batch_id for batch in history):
            old["last_import"] = {"batch_id": batch_id, "status": "already_imported",
                                  "added": 0, "updated": 0, "duplicates": incoming["total"]}
            return old
        old_fallback = {m["message_id"] for m in old["messages"]
                        if m["identity_method"] == "content_occurrence"} if old else set()
        incoming_fallback = {m["message_id"] for m in incoming["messages"]
                             if m["identity_method"] == "content_occurrence"}
        if old_fallback & incoming_fallback and not old_fallback <= incoming_fallback:
            raise ValueError("无原始消息 ID 的重叠片段无法可靠去重；请导入包含旧记录的完整导出")
        merged = {m["message_id"]: dict(m) for m in old["messages"]} if old else {}
        added = duplicates = updated = 0
        for message in incoming["messages"]:
            previous = merged.get(message["message_id"])
            if previous is None:
                merged[message["message_id"]] = dict(message)
                added += 1
            else:
                if message_signature(previous) != message_signature(message):
                    raise ValueError("相同来源消息 ID 对应不同正文或时间；保留旧记录，请检查导出数据")
                if message.get("transcript") and previous.get("transcript") != message["transcript"]:
                    if previous.get("transcript"):
                        raise ValueError("同一消息出现冲突转写；保留旧记录，请检查输入")
                    previous["transcript"] = message["transcript"]
                    updated += 1
                else:
                    duplicates += 1
        timestamps = [m["timestamp"] for m in incoming["messages"]]
        batch = {
            "batch_id": batch_id, "status": "imported",
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "source_file": Path(source_path).name if source_path else None,
            "source_sha256": hashlib.sha256(Path(source_path).read_bytes()).hexdigest() if source_path else None,
            "received": incoming["total"], "added": added, "updated": updated,
            "duplicates": duplicates, "dropped": incoming["normalization"]["dropped_messages"],
            "date_range_seconds": [min(timestamps), max(timestamps)],
            "identity_fallback_count": sum(m["identity_method"] == "content_occurrence"
                                           for m in incoming["messages"]),
            "identity_warning": (
                "缺少来源消息 ID：同秒同文消息按完整导出的出现次数识别，无法区分另一次内容完全相同的新增事件"
                if incoming_fallback else None
            ),
        }
        result = normalize_payload({**incoming, "messages": list(merged.values())})
        result["bundle_dir"] = str(path.parent.resolve())
        result["import_history"] = history + [batch]
        result["last_import"] = batch
        result["normalization"] = incoming["normalization"]
        # The canonical file is the commit point; an interrupted earlier archive write is harmless.
        archive = path.parent / "imports" / f"{batch_id}.json"
        atomic_json(archive, {"batch": batch, "payload": incoming})
        atomic_json(path, result)
        return result
    finally:
        lock.unlink()
