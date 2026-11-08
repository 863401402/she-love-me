"""Diagnose and configure CipherTalk without exposing the database key."""

import argparse
import csv
import ctypes
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from run_ciphertalk_scanner import ScannerError


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SYSTEM_ACCOUNT_PREFIXES = (
    "all", "applet", "backup", "wmpf", "app_data", "system", "temp", "cache"
)


def is_admin():
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def weixin_processes():
    if sys.platform != "win32":
        return []
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    processes = []
    for row in csv.reader(result.stdout.splitlines()):
        if len(row) < 2 or row[0].lower() != "weixin.exe":
            continue
        try:
            processes.append({"name": row[0], "pid": int(row[1])})
        except ValueError:
            continue
    return processes


def read_miyu_config(path=None):
    config_path = Path(path) if path else Path.home() / ".miyu" / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("miyu 配置必须是 JSON 对象")
    except FileNotFoundError:
        data = {}
    except (OSError, ValueError) as exc:
        return {
            "path": str(config_path), "readable": False, "error": str(exc),
            "has_key": False, "key_format_valid": False,
        }
    key = data.get("keyHex")
    return {
        "path": str(config_path),
        "readable": True,
        "db_path": data.get("dbPath"),
        "wxid": data.get("wxid"),
        "has_key": bool(key),
        "key_format_valid": isinstance(key, str) and len(key) == 64
            and all(char in "0123456789abcdefABCDEF" for char in key),
    }


def default_search_roots(config_db_path=None):
    home = Path.home()
    roots = []
    if config_db_path:
        roots.append(Path(config_db_path))
    document_roots = [home / "Documents"]
    for env_name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(env_name)
        if value:
            document_roots.append(Path(value) / "Documents")
    for documents in document_roots:
        roots.extend((documents / "xwechat_files", documents / "WeChat Files"))
    unique = []
    seen = set()
    for root in roots:
        normalized = os.path.normcase(os.path.abspath(root))
        if normalized not in seen:
            seen.add(normalized)
            unique.append(root)
    return unique


def is_system_account(name):
    lower = name.lower()
    return any(lower.startswith(prefix) for prefix in SYSTEM_ACCOUNT_PREFIXES)


def account_from_db_storage(db_storage):
    account_path = db_storage.parent
    name = account_path.name
    wxid = name if name.lower().startswith("wxid_") else None
    session_count = sum(1 for path in db_storage.rglob("session.db") if path.is_file())
    message_count = sum(
        1 for pattern in ("msg_*.db", "message_*.db", "biz_message_*.db")
        for path in db_storage.rglob(pattern) if path.is_file()
    )
    try:
        modified = account_path.stat().st_mtime
    except OSError:
        modified = 0
    return {
        "root_path": str(account_path.parent),
        "account_path": str(account_path),
        "db_storage": str(db_storage),
        "wxid": wxid,
        "session_db_count": session_count,
        "message_db_count": message_count,
        "modified": modified,
        "usable_layout": session_count > 0 and message_count > 0,
    }


def discover_accounts(roots):
    candidates = []
    seen = set()
    for raw_root in roots:
        root = Path(raw_root).expanduser()
        if not root.exists() or not root.is_dir():
            continue
        db_storages = []
        if root.name.lower() == "db_storage":
            db_storages.append(root)
        elif (root / "db_storage").is_dir():
            db_storages.append(root / "db_storage")
        else:
            try:
                children = list(root.iterdir())
            except OSError:
                children = []
            for child in children:
                if child.is_dir() and not is_system_account(child.name):
                    storage = child / "db_storage"
                    if storage.is_dir():
                        db_storages.append(storage)
        for storage in db_storages:
            key = os.path.normcase(os.path.abspath(storage))
            if key in seen:
                continue
            seen.add(key)
            candidates.append(account_from_db_storage(storage))
    return sorted(
        candidates,
        key=lambda item: (item["usable_layout"], item["modified"]),
        reverse=True,
    )


def configure_miyu(candidate, miyu="miyu"):
    executable = shutil.which(miyu) or shutil.which(f"{miyu}.cmd")
    if not executable:
        raise RuntimeError("未找到 miyu 命令；请先安装 ciphertalk-cli")
    command = [
        executable, "--db-path", candidate["account_path"],
    ]
    if candidate.get("wxid"):
        command.extend(("--wxid", candidate["wxid"]))
    command.extend(("--format=json", "--quiet", "init"))
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "未知错误"
        raise RuntimeError(f"CipherTalk 配置失败：{detail}")
    saved = read_miyu_config()
    expected_path = os.path.normcase(os.path.abspath(candidate["account_path"]))
    actual_path = saved.get("db_path")
    if not actual_path or os.path.normcase(os.path.abspath(actual_path)) != expected_path:
        raise RuntimeError("CipherTalk 命令返回成功，但回读配置未发现 dbPath")
    if candidate.get("wxid") and saved.get("wxid") != candidate["wxid"]:
        raise RuntimeError("CipherTalk 命令返回成功，但回读配置中的 wxid 不匹配")


def run_headless_scanner(account_path, download=False, config_path=None):
    script = Path(__file__).with_name("run_ciphertalk_scanner.py")
    command = [sys.executable, str(script), "--account-path", account_path]
    if download:
        command.append("--download")
    if config_path:
        command.extend(("--config-path", str(config_path)))
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    try:
        payload = json.loads(result.stdout or result.stderr)
    except json.JSONDecodeError as exc:
        raise RuntimeError("CipherTalk 无界面扫描器未返回有效结果") from exc
    if result.returncode != 0 or payload.get("status") != "ok":
        raise ScannerError(
            payload.get("error") or "CipherTalk 无界面密钥扫描失败",
            diagnostic=payload.get("diagnostic"), method=payload.get("method"),
            code=payload.get("error_code"),
        )
    return payload


def required_inputs_after_scan(config, scan):
    if not config.get("has_key"):
        return ["local_key_setup"]
    if scan.get("database_validated"):
        return []
    return ["database_validation"]


def build_report(search_roots, config_path=None):
    config = read_miyu_config(config_path)
    roots = list(search_roots) or default_search_roots(config.get("db_path"))
    candidates = discover_accounts(roots)
    processes = weixin_processes()
    needs = []
    if not candidates:
        needs.append("db_path")
    elif len(candidates) > 1:
        needs.append("account_selection")
    if not config.get("has_key"):
        needs.append("local_key_setup")
    report = {
        "status": "ok",
        "platform": sys.platform,
        "administrator": is_admin(),
        "miyu_command": shutil.which("miyu") or shutil.which("miyu.cmd"),
        "weixin_process_count": len(processes),
        "weixin_processes": processes,
        "config": config,
        "searched_roots": [str(Path(root).expanduser()) for root in roots],
        "candidates": candidates,
        "required_user_inputs": needs,
    }
    if len(processes) > 1 and not config.get("has_key"):
        report["key_capture_warning"] = (
            "CipherTalk CLI currently hooks the first Weixin.exe returned by tasklist; "
            "automatic key capture may time out on multi-process WeChat."
        )
    return report


def main():
    parser = argparse.ArgumentParser(description="诊断并配置 CipherTalk 微信数据环境")
    parser.add_argument("--search-root", action="append", default=[], help="额外检查的微信数据根目录")
    parser.add_argument("--db-path", help="已知的账号目录、db_storage 或其上级目录")
    parser.add_argument("--candidate", type=int, help="配置诊断结果中的候选序号（从 1 开始）")
    parser.add_argument("--configure", action="store_true", help="把唯一/选定候选写入 miyu 配置")
    parser.add_argument("--scan-key", action="store_true", help="使用官方多进程组件扫描并本地保存密钥")
    parser.add_argument("--download-scanner", action="store_true", help="缺失时下载并校验官方扫描组件")
    parser.add_argument("--config-path", help=argparse.SUPPRESS)
    args = parser.parse_args()

    roots = list(args.search_root)
    if args.db_path:
        roots.insert(0, args.db_path)
    if args.configure and args.config_path:
        raise RuntimeError("--configure 仅支持 miyu 默认配置；自定义 --config-path 可用于诊断和扫描")
    report = build_report(roots, config_path=args.config_path)
    if args.configure:
        candidates = report["candidates"]
        if not candidates:
            raise RuntimeError("未找到有效的 db_storage；请用 --db-path 指定微信数据目录")
        if args.candidate:
            index = args.candidate - 1
            if index < 0 or index >= len(candidates):
                raise RuntimeError(f"候选序号超出范围：1-{len(candidates)}")
        elif len(candidates) == 1:
            index = 0
        else:
            raise RuntimeError("发现多个账号；请用 --candidate 选择，不要自动猜测")
        configure_miyu(candidates[index])
        refreshed = read_miyu_config()
        report["config"] = refreshed
        report["required_user_inputs"] = (
            [] if refreshed.get("has_key") else ["local_key_setup"]
        )
        report["configured"] = {
            "account_path": candidates[index]["account_path"],
            "wxid": candidates[index]["wxid"],
        }
    if args.scan_key:
        candidates = report["candidates"]
        configured_path = report["config"].get("db_path")
        if not configured_path:
            raise RuntimeError("miyu 尚未配置数据库目录；请先使用 --configure")
        scan = run_headless_scanner(
            configured_path, download=args.download_scanner, config_path=args.config_path
        )
        report["key_scan"] = scan
        report["config"] = read_miyu_config(args.config_path)
        report["required_user_inputs"] = required_inputs_after_scan(report["config"], scan)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ScannerError as exc:
        print(json.dumps({
            "status": "error", "error": str(exc), "error_code": exc.code,
            "method": exc.method, "diagnostic": exc.diagnostic,
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
