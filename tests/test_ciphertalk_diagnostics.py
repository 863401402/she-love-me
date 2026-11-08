import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import diagnose_ciphertalk


class CipherTalkDiagnosticTests(unittest.TestCase):
    def test_config_accepts_bom_and_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text('{"dbPath":"C:/custom"}', encoding="utf-8-sig")
            self.assertEqual(diagnose_ciphertalk.read_miyu_config(config)["db_path"], "C:/custom")
            config.write_text('[]', encoding="utf-8")
            self.assertFalse(diagnose_ciphertalk.read_miyu_config(config)["readable"])

    @patch.object(diagnose_ciphertalk, "build_report")
    @patch.object(diagnose_ciphertalk.sys, "argv", ["diagnose", "--config-path", "custom.json"])
    def test_cli_uses_custom_config_for_initial_diagnosis(self, build_report):
        build_report.return_value = {"status": "ok"}
        diagnose_ciphertalk.main()
        build_report.assert_called_once_with([], config_path="custom.json")

    @patch.object(diagnose_ciphertalk.subprocess, "run")
    def test_scan_failure_keeps_diagnostics_and_code(self, run):
        run.return_value.returncode = 1
        run.return_value.stdout = ""
        run.return_value.stderr = json.dumps({
            "status": "error", "error": "empty account", "error_code": "SCANNER_EMPTY_ACCOUNT",
            "method": "active-account", "diagnostic": {"candidateCount": 526},
        })
        with self.assertRaises(diagnose_ciphertalk.ScannerError) as raised:
            diagnose_ciphertalk.run_headless_scanner("C:/account")
        self.assertEqual(raised.exception.code, "SCANNER_EMPTY_ACCOUNT")
        self.assertEqual(raised.exception.diagnostic, {"candidateCount": 526})

    def test_scan_key_cli_accepts_private_config_path(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "diagnose_ciphertalk.py"),
             "--config-path", "private-config.json", "--help"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("--config-path", result.stdout)

    def test_discovers_account_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "xwechat_files"
            storage = root / "wxid_example" / "db_storage"
            (storage / "session").mkdir(parents=True)
            (storage / "message").mkdir()
            (storage / "session" / "session.db").touch()
            (storage / "message" / "message_0.db").touch()

            candidates = diagnose_ciphertalk.discover_accounts([root])

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["wxid"], "wxid_example")
            self.assertTrue(candidates[0]["usable_layout"])

    def test_config_report_never_returns_key(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text(json.dumps({
                "dbPath": "C:/chat/wxid_example",
                "wxid": "wxid_example",
                "keyHex": "a" * 64,
            }), encoding="utf-8")

            report = diagnose_ciphertalk.read_miyu_config(config)

            self.assertTrue(report["has_key"])
            self.assertTrue(report["key_format_valid"])
            self.assertNotIn("keyHex", report)
            self.assertNotIn("a" * 64, json.dumps(report))

    def test_system_directories_are_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "All Users" / "db_storage").mkdir(parents=True)
            self.assertEqual(diagnose_ciphertalk.discover_accounts([root]), [])

    def test_unvalidated_scan_is_not_treated_as_complete(self):
        required = diagnose_ciphertalk.required_inputs_after_scan(
            {"has_key": True}, {"database_validated": False}
        )
        self.assertEqual(required, ["database_validation"])

    @patch.object(diagnose_ciphertalk, "read_miyu_config")
    @patch.object(diagnose_ciphertalk.subprocess, "run")
    @patch.object(diagnose_ciphertalk.shutil, "which")
    def test_configure_uses_resolved_command_path(self, which, run, read_config):
        which.return_value = "C:/tools/miyu.CMD"
        run.return_value.returncode = 0
        candidate = {"account_path": "C:/chat/wxid_example", "wxid": "wxid_example"}
        read_config.return_value = {
            "db_path": "C:/chat/wxid_example", "wxid": "wxid_example"
        }

        diagnose_ciphertalk.configure_miyu(candidate)

        self.assertEqual(run.call_args.args[0][0], "C:/tools/miyu.CMD")
        self.assertEqual(run.call_args.args[0][-1], "init")


if __name__ == "__main__":
    unittest.main()
