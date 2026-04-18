"""
export_emojis.py - 从 messages.json 导出表情元信息、下载资源并生成预览页。

默认输入 extract_messages.py 生成的 messages.json，要求表情消息已包含 emoji 元信息。
输出：
  - <bundle>/emojis.json / emojis.csv     表情清单
  - <bundle>/emojis_assets/               去重下载后的本地资源
  - <bundle>/emojis_download_manifest.json 下载与整理结果
  - <bundle>/emojis_preview.html          本地预览页

可选：将下载结果回写到 messages.json 顶层的 emoji_export 字段中。
"""
import argparse
import csv
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from contact_bundle import resolve_bundle_paths

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SIG_MAP = {
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def detect_ext(path):
    try:
        with open(path, "rb") as f:
            head = f.read(16)
        for sig, ext in SIG_MAP.items():
            if head.startswith(sig):
                return ext
        if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
            return ".webp"
    except Exception:
        pass
    return path.suffix if path.suffix else ".dat"


def normalize_url(url):
    return html.unescape(url or "").strip()


def build_emoji_rows(messages):
    unique = {}
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("type") != "emoji":
            continue
        emoji = msg.get("emoji") or {}
        emoji_id = msg.get("emoji_ref") or emoji.get("md5") or f"emoji_local_{msg.get('local_id')}"
        row = unique.get(emoji_id)
        if not row:
            row = {
            "emoji_id": emoji_id,
            "local_id": msg.get("local_id"),
            "timestamp": msg.get("timestamp"),
            "sender": msg.get("sender"),
            "content": msg.get("content"),
            "local_type": msg.get("local_type"),
            "emoji_type": emoji.get("type"),
            "md5": emoji.get("md5"),
            "androidmd5": emoji.get("androidmd5"),
            "len": emoji.get("len"),
            "productid": emoji.get("productid"),
            "fromusername": emoji.get("fromusername"),
            "tousername": emoji.get("tousername"),
            "cdnurl": normalize_url(emoji.get("cdnurl")),
            "thumburl": normalize_url(emoji.get("thumburl")),
            "occurrence_count": 1,
            "message_ref": msg,
            }
            unique[emoji_id] = row
        else:
            row["occurrence_count"] = row.get("occurrence_count", 1) + 1
    return list(unique.values())


def build_emoji_rows_from_catalog(catalog):
    rows = []
    for item in catalog.get("emoji_records", []) if isinstance(catalog, dict) else []:
        row = dict(item)
        row["emoji_type"] = row.get("emoji_type") or row.get("type")
        row["sender"] = row.get("sender") or "mixed"
        row["content"] = row.get("content") or "[表情]"
        row["local_type"] = row.get("local_type") or 47
        rows.append(row)
    return rows


def export_emoji_lists(rows, json_output, csv_output):
    export_rows = []
    for row in rows:
        clean = dict(row)
        clean.pop("message_ref", None)
        export_rows.append(clean)
    existing = None
    if os.path.exists(json_output):
        try:
            existing = load_json(json_output)
        except Exception:
            existing = None
    if isinstance(existing, dict):
        existing["total_messages"] = sum(int(r.get("occurrence_count", 1) or 1) for r in export_rows)
        existing["unique_emojis"] = len(export_rows)
        existing["emoji_records"] = export_rows
        save_json(json_output, existing)
    else:
        save_json(json_output, {
            "total_messages": sum(int(r.get("occurrence_count", 1) or 1) for r in export_rows),
            "unique_emojis": len(export_rows),
            "emoji_records": export_rows,
        })

    fields = [
        "local_id", "timestamp", "sender", "content", "local_type", "emoji_type",
        "emoji_id", "md5", "androidmd5", "len", "productid", "fromusername", "tousername", "occurrence_count",
        "cdnurl", "thumburl", "asset_path", "asset_ext", "download_status", "download_error",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(csv_output)), exist_ok=True)
    with open(csv_output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in export_rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def download_assets(rows, assets_dir, timeout=20):
    os.makedirs(assets_dir, exist_ok=True)
    unique = {}
    for row in rows:
        md5 = row.get("md5")
        url = row.get("cdnurl")
        if md5 and url and md5 not in unique:
            unique[md5] = row

    results = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for md5, row in unique.items():
        url = row["cdnurl"]
        outfile = Path(assets_dir) / f"{md5}.dat"
        result = {
            "md5": md5,
            "url": url,
            "path": str(outfile),
            "ok": False,
            "status": "error",
        }
        try:
            if outfile.exists() and outfile.stat().st_size > 0:
                data_len = outfile.stat().st_size
                result.update({"ok": True, "status": "exists", "size": data_len})
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read()
                outfile.write_bytes(data)
                result.update({"ok": True, "status": "downloaded", "size": len(data)})
        except Exception as e:
            result["error"] = str(e)
        results.append(result)
        time.sleep(0.05)
    return results


def organize_assets(results):
    updated = []
    for rec in results:
        path = Path(rec.get("path", ""))
        if not rec.get("ok") or not path.exists():
            updated.append(rec)
            continue
        ext = detect_ext(path)
        target = path.with_suffix(ext)
        if target != path:
            if target.exists():
                if target.stat().st_size == path.stat().st_size:
                    path.unlink()
                else:
                    path.replace(target)
            else:
                path.replace(target)
        rec["path"] = str(target)
        rec["detected_ext"] = ext
        updated.append(rec)
    return updated


def annotate_rows(rows, asset_results):
    asset_map = {r.get("md5"): r for r in asset_results if r.get("md5")}
    for row in rows:
        md5 = row.get("md5")
        asset = asset_map.get(md5)
        if not asset:
            continue
        row["asset_path"] = asset.get("path")
        row["asset_ext"] = asset.get("detected_ext") or Path(asset.get("path", "")).suffix
        row["download_status"] = asset.get("status")
        row["download_error"] = asset.get("error")
        emoji = row.get("message_ref", {}).get("emoji")
        if isinstance(emoji, dict):
            emoji["asset_path"] = row.get("asset_path")
            emoji["asset_ext"] = row.get("asset_ext")
            emoji["download_status"] = row.get("download_status")
            if row.get("download_error"):
                emoji["download_error"] = row.get("download_error")


def annotate_catalog(catalog, asset_results):
    if not isinstance(catalog, dict):
        return catalog
    asset_map = {r.get("md5"): r for r in asset_results if r.get("md5")}
    for item in catalog.get("emoji_records", []):
        asset = asset_map.get(item.get("md5"))
        if not asset:
            continue
        item["asset_path"] = asset.get("path")
        item["asset_ext"] = asset.get("detected_ext") or Path(asset.get("path", "")).suffix
        item["download_status"] = asset.get("status")
        if asset.get("error"):
            item["download_error"] = asset.get("error")
    return catalog


def build_preview(rows, preview_output, title):
    preview_path = Path(preview_output)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [r for r in rows if r.get("asset_path") and Path(r["asset_path"]).exists()]
    cards = []
    for row in ok_rows:
        rel = os.path.relpath(row["asset_path"], preview_path.parent).replace("\\", "/")
        cards.append(
            f'''<div class="card">'''
            f'''<div class="imgwrap"><img src="{rel}" loading="lazy" /></div>'''
            f'''<div class="meta"><div class="md5">{row.get("md5","")}</div>'''
            f'''<div class="sub">{row.get("sender","?")} · {row.get("asset_ext","?")} · {row.get("len","?")} bytes</div></div></div>'''
        )
    html_doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title}</title>
<style>
body{{font-family:Inter,system-ui,-apple-system,Segoe UI,Arial,sans-serif;background:#0f1115;color:#e8eaf0;margin:0;padding:24px}}
.header{{margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}}
.card{{background:#171a21;border:1px solid #262b36;border-radius:14px;overflow:hidden;box-shadow:0 8px 20px rgba(0,0,0,.18)}}
.imgwrap{{height:160px;display:flex;align-items:center;justify-content:center;background:#0b0d12}}
.imgwrap img{{max-width:100%;max-height:100%;object-fit:contain}}
.meta{{padding:10px 12px}}
.md5{{font-size:12px;word-break:break-all;color:#cbd3e1}}
.sub{{font-size:12px;color:#8d97aa;margin-top:6px}}
</style>
</head>
<body>
<div class="header"><h1>{title}</h1><p>共 {len(ok_rows)} 个成功下载的唯一表情资源</p></div>
<div class="grid">{''.join(cards)}</div>
</body>
</html>'''
    preview_path.write_text(html_doc, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="导出并下载 messages.json 中的微信表情资源")
    parser.add_argument("--input", required=True, help="extract_messages.py 生成的 messages.json")
    parser.add_argument("--emoji-json")
    parser.add_argument("--emoji-csv")
    parser.add_argument("--assets-dir")
    parser.add_argument("--manifest")
    parser.add_argument("--preview")
    parser.add_argument("--title", default="微信表情预览")
    parser.add_argument("--skip-download", action="store_true", help="仅导出清单，不下载表情")
    parser.add_argument("--no-writeback", action="store_true", help="不要把下载结果回写到 input messages.json")
    args = parser.parse_args()

    payload = load_json(args.input)
    messages = payload.get("messages", []) if isinstance(payload, dict) else []
    bundle = resolve_bundle_paths(
        contact_display=payload.get("contact_display", "contact"),
        contact_username=payload.get("contact_username"),
        output=args.input,
        output_dir=None,
    )
    emoji_json_path = args.emoji_json or payload.get("emojis_path") or bundle["emojis_path"]
    emoji_csv_path = args.emoji_csv or bundle["emojis_csv_path"]
    assets_dir = args.assets_dir or bundle["emojis_assets_dir"]
    manifest_path = args.manifest or bundle["emojis_manifest_path"]
    preview_path = args.preview or bundle["emojis_preview_path"]

    rows = build_emoji_rows(messages)
    emoji_catalog = None
    if os.path.exists(emoji_json_path):
        emoji_catalog = load_json(emoji_json_path)
    if (not rows or not any(r.get("md5") for r in rows)) and emoji_catalog:
        rows = build_emoji_rows_from_catalog(emoji_catalog)
    if not rows:
        print(json.dumps({"error": "messages.json 中未发现可导出的 emoji 元信息"}, ensure_ascii=False))
        sys.exit(1)

    asset_results = []
    if not args.skip_download:
        asset_results = organize_assets(download_assets(rows, assets_dir))
        save_json(manifest_path, {
            "total_unique": len({r.get('md5') for r in rows if r.get('md5')}),
            "success": sum(1 for r in asset_results if r.get("ok")),
            "failed": sum(1 for r in asset_results if not r.get("ok")),
            "results": asset_results,
        })
        annotate_rows(rows, asset_results)
        if emoji_catalog and not messages:
            emoji_catalog = annotate_catalog(emoji_catalog, asset_results)
            save_json(emoji_json_path, emoji_catalog)
        build_preview(rows, preview_path, args.title)
        payload["emoji_export"] = {
            "total_messages": len(rows),
            "unique_assets": len({r.get('md5') for r in rows if r.get('md5')}),
            "assets_dir": assets_dir,
            "manifest": manifest_path,
            "preview": preview_path,
        }
        if not args.no_writeback:
            save_json(args.input, payload)

    export_emoji_lists(rows, emoji_json_path, emoji_csv_path)

    print(json.dumps({
        "status": "ok",
        "emoji_messages": len(rows),
        "unique_assets": len({r.get('md5') for r in rows if r.get('md5')}),
        "emoji_json": emoji_json_path,
        "emoji_csv": emoji_csv_path,
        "assets_dir": None if args.skip_download else assets_dir,
        "preview": None if args.skip_download else preview_path,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
