"""Run CipherTalk's official multi-process scanner without exposing its key."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import setup_ciphertalk_scanner


class ScannerError(RuntimeError):
    def __init__(self, message, diagnostic=None, method=None, code=None):
        super().__init__(message)
        self.diagnostic = diagnostic
        self.method = method
        self.code = code


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def find_koffi():
    miyu = shutil.which("miyu") or shutil.which("miyu.cmd")
    candidates = []
    if miyu:
        resolved = Path(miyu).resolve()
        candidates.extend(parent / "node_modules" / "ciphertalk-cli" / "node_modules" / "koffi"
                          for parent in resolved.parents)
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm:
        result = subprocess.run(
            [npm, "root", "-g"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            candidates.append(Path(result.stdout.strip()) / "ciphertalk-cli" / "node_modules" / "koffi")
    for candidate in candidates:
        if (candidate / "package.json").is_file():
            return candidate
    return None


def run_scanner(account_path, component_dir, config_path=None, node="node"):
    node_path = shutil.which(node) or shutil.which(f"{node}.exe")
    if not node_path:
        raise RuntimeError("未找到 Node.js")
    koffi = find_koffi()
    if not koffi:
        raise RuntimeError("未找到 CipherTalk CLI 自带的 koffi；请先安装 ciphertalk-cli")
    component_dir = Path(component_dir)
    helper = Path(__file__).with_name("ciphertalk_key_helper.cjs")
    command = [
        node_path, str(helper),
        "--dll", str(component_dir / "wechat_key_tool.dll"),
        "--source", str(component_dir / "wxKeyService.ts"),
        "--account-path", str(account_path),
        "--koffi-path", str(koffi),
    ]
    if config_path:
        command.extend(("--config-path", str(config_path)))
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("CipherTalk 无界面扫描超时（180s）") from exc
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("密钥扫描器未返回有效结果") from exc
    if result.returncode != 0 or not payload.get("ok"):
        raise ScannerError(
            payload.get("error") or "密钥扫描失败",
            diagnostic=payload.get("diagnostic"),
            method=payload.get("method"),
            code=payload.get("errorCode"),
        )
    return payload


def main():
    parser = argparse.ArgumentParser(description="使用 CipherTalk 官方组件无界面扫描并保存密钥")
    parser.add_argument("--account-path", help="微信账号数据目录；默认读取 miyu 配置")
    parser.add_argument("--component-dir", default="vendor/ciphertalk/scanner")
    parser.add_argument("--config-path")
    parser.add_argument("--download", action="store_true", help="缺失时下载固定官方组件")
    args = parser.parse_args()

    config_path = Path(args.config_path) if args.config_path else Path.home() / ".miyu" / "config.json"
    account_path = args.account_path
    if not account_path:
        try:
            account_path = json.loads(config_path.read_text(encoding="utf-8")).get("dbPath")
        except (OSError, json.JSONDecodeError):
            account_path = None
    if not account_path:
        raise RuntimeError("miyu 尚未配置数据库目录；请先运行 diagnose_ciphertalk.py --configure")

    files, ready = setup_ciphertalk_scanner.component_status(args.component_dir)
    if not ready and args.download:
        for name, component in setup_ciphertalk_scanner.COMPONENTS.items():
            setup_ciphertalk_scanner.download_component(name, component, args.component_dir)
        files, ready = setup_ciphertalk_scanner.component_status(args.component_dir)
    if not ready:
        raise RuntimeError("CipherTalk 官方扫描组件未准备好；使用 --download 自动下载并校验")

    payload = run_scanner(account_path, args.component_dir, config_path=config_path)
    print(json.dumps({
        "status": "ok", "saved": payload["saved"], "method": payload["method"],
        "database_validated": bool(payload.get("databaseValidated")),
        "diagnostic": payload.get("diagnostic"), "source_verified": all(
            item["verified"] for item in files.values()
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ScannerError as exc:
        print(json.dumps({
            "status": "error", "error": str(exc), "method": exc.method,
            "diagnostic": exc.diagnostic,
            "error_code": exc.code,
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
