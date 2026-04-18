import hashlib
import os
import re
from pathlib import Path


def safe_slug(value, fallback="contact"):
    text = (value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._")
    return text[:48] or fallback


def contact_export_dir(root_dir, contact_display, contact_username=None):
    slug = safe_slug(contact_display or contact_username or "contact")
    suffix_source = contact_username or contact_display or slug
    suffix = hashlib.md5(suffix_source.encode("utf-8")).hexdigest()[:8]
    return os.path.join(root_dir, f"{slug}__{suffix}")


def resolve_bundle_paths(contact_display, contact_username=None, output=None, output_dir=None):
    if output and output_dir:
        raise ValueError("output and output_dir cannot be used together")

    if output_dir:
        bundle_dir = contact_export_dir(output_dir, contact_display, contact_username)
        messages_path = os.path.join(bundle_dir, "messages.json")
    else:
        target = output or os.path.join("data", "messages.json")
        if target.lower().endswith(".json"):
            messages_path = target
            bundle_dir = os.path.dirname(os.path.abspath(target))
        else:
            bundle_dir = contact_export_dir(target, contact_display, contact_username)
            messages_path = os.path.join(bundle_dir, "messages.json")

    bundle_dir = os.path.abspath(bundle_dir)
    messages_path = os.path.abspath(messages_path)
    return {
        "bundle_dir": bundle_dir,
        "messages_path": messages_path,
        "emojis_path": os.path.join(bundle_dir, "emojis.json"),
        "emojis_csv_path": os.path.join(bundle_dir, "emojis.csv"),
        "emojis_assets_dir": os.path.join(bundle_dir, "emojis_assets"),
        "emojis_manifest_path": os.path.join(bundle_dir, "emojis_download_manifest.json"),
        "emojis_preview_path": os.path.join(bundle_dir, "emojis_preview.html"),
        "stats_path": os.path.join(bundle_dir, "stats.json"),
        "chat_history_path": os.path.join(bundle_dir, "chat_history.txt"),
        "analysis_path": os.path.join(bundle_dir, "analysis.json"),
        "reports_dir": os.path.join(bundle_dir, "reports"),
    }
