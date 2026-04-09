"""
decrypt_wechat.py - she-love-me 的跨平台解密入口

职责：
  - Windows / Linux: 直接调用 wechat-decrypt 的 main.py decrypt
  - macOS: 编译并调用 C 版密钥扫描器，再执行 decrypt_db.py
"""
import os
import platform
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DECRYPTOR_DIR = REPO_ROOT / "vendor" / "wechat-decrypt"
MACOS_SCANNER = DECRYPTOR_DIR / "find_all_keys_macos"
MACOS_SCANNER_SOURCE = DECRYPTOR_DIR / "find_all_keys_macos.c"
KEYS_FILE = DECRYPTOR_DIR / "all_keys.json"


def run_command(cmd, cwd, check=True):
    result = subprocess.run(cmd, cwd=str(cwd))
    if check and result.returncode != 0:
        raise RuntimeError(f"命令执行失败: {' '.join(cmd)}")
    return result.returncode


def ensure_decryptor_exists():
    if not DECRYPTOR_DIR.exists():
        raise RuntimeError("未找到 vendor/wechat-decrypt，请先执行 setup_check.py")


def should_rebuild_macos_scanner():
    if not MACOS_SCANNER.exists():
        return True
    return MACOS_SCANNER_SOURCE.stat().st_mtime > MACOS_SCANNER.stat().st_mtime


def load_existing_keys():
    if not KEYS_FILE.exists():
        return {}

    try:
        with KEYS_FILE.open(encoding="utf-8") as f:
            keys = json.load(f)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}

    return {name: value for name, value in keys.items() if not str(name).startswith("_")}


def run_macos_flow():
    existing_keys = load_existing_keys()
    if existing_keys:
        print(f"[*] 检测到现有数据库密钥 {len(existing_keys)} 个，跳过重复扫描。")
    else:
        if should_rebuild_macos_scanner():
            print("[*] 编译 macOS 密钥扫描器...")
            run_command(
                ["cc", "-O2", "-o", str(MACOS_SCANNER), str(MACOS_SCANNER_SOURCE), "-framework", "Foundation"],
                cwd=DECRYPTOR_DIR,
            )

        print("[*] 运行 macOS 密钥扫描器...")
        scanner_rc = run_command([str(MACOS_SCANNER)], cwd=DECRYPTOR_DIR, check=False)
        if scanner_rc != 0:
            raise RuntimeError(
                "macOS 密钥扫描失败。通常需要：1) 以 root 运行扫描器；2) 对 /Applications/WeChat.app 做 ad-hoc 重签名；3) 重启微信后重试。"
            )

    print("[*] 开始解密全部数据库...")
    run_command([sys.executable, "decrypt_db.py"], cwd=DECRYPTOR_DIR)


def run_default_flow():
    print("[*] 调用 wechat-decrypt 主流程...")
    run_command([sys.executable, "main.py", "decrypt"], cwd=DECRYPTOR_DIR)


def main():
    ensure_decryptor_exists()
    system = platform.system().lower()

    if system == "darwin":
        run_macos_flow()
        return

    run_default_flow()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        sys.exit(1)
