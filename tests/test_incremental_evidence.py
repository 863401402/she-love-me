import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analysis_evidence import validate_evidence
from bundle_store import update_bundle
from generate_html_report import render_html
from message_normalizer import normalize_payload
from convert_weflow_cli import convert_payload


def message(text="你好", identifier=None, timestamp=1700000000):
    item = {"sender": "me", "timestamp": timestamp, "type": "text", "content": text}
    if identifier is not None:
        item["source_message_id"] = identifier
    return item


def payload(messages, **kwargs):
    return {"source": "test", "contact_username": "friend", "contact_display": "测试",
            "account_id": "my-account", "messages": messages, **kwargs}


class IncrementalTests(unittest.TestCase):
    def test_native_ids_survive_input_order_and_unit_changes(self):
        first = normalize_payload(payload([message(identifier=1), message("再见", 2)]))
        raw = payload([message("再见", 2), message(identifier=1, timestamp=1700000000000)])
        second = normalize_payload(raw)
        self.assertEqual({m["message_id"] for m in first["messages"]},
                         {m["message_id"] for m in second["messages"]})
        self.assertEqual(first["messages_digest"], second["messages_digest"])

    def test_pre_upgrade_bundle_is_archived_and_not_duplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            target.write_text(json.dumps(payload([message()])), encoding="utf-8")
            result = update_bundle(payload([message(identifier=1), message("新增", 2)]), target)
            self.assertEqual(result["total"], 2)
            self.assertTrue((target.parent / "imports" / "legacy.json").exists())
            self.assertEqual(result["last_import"]["added"], 1)

    def test_identical_messages_with_distinct_native_ids_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            result = update_bundle(payload([message(identifier=1), message(identifier=2)]),
                                   Path(directory) / "messages.json")
            self.assertEqual(result["total"], 2)

    def test_repeated_file_is_noop_and_partial_native_export_adds_only_new(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            first = update_bundle(payload([message(identifier=1), message("再见", 2)]), target)
            before = target.read_bytes()
            repeated = update_bundle(payload([message(identifier=1), message("再见", 2)]), target)
            self.assertEqual(repeated["last_import"]["status"], "already_imported")
            self.assertEqual(target.read_bytes(), before)
            result = update_bundle(payload([message("再见", 2), message("晚安", 3)]), target)
            self.assertEqual(result["total"], 3)
            self.assertEqual(result["last_import"]["added"], 1)
            self.assertEqual(result["last_import"]["duplicates"], 1)
            self.assertEqual(len(result["import_history"]), 2)
            self.assertEqual(len(list((target.parent / "imports").glob("*.json"))), 2)
            self.assertEqual(first["messages"][0]["message_id"], result["messages"][0]["message_id"])

    def test_idless_full_export_preserves_same_second_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            first = update_bundle(payload([message(), message()]), target)
            result = update_bundle(payload([message(), message(), message("新增")]), target)
            self.assertEqual(first["total"], 2)
            self.assertEqual(result["total"], 3)
            self.assertEqual(len({m["message_id"] for m in result["messages"]}), 3)
            self.assertEqual(result["last_import"]["identity_fallback_count"], 3)

    def test_ambiguous_idless_partial_overlap_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            update_bundle(payload([message(), message("旧记录")]), target)
            before = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "完整导出"):
                update_bundle(payload([message(), message("新增")]), target)
            self.assertEqual(before, target.read_bytes())

    def test_conflicting_native_id_and_corrupt_file_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            update_bundle(payload([message(identifier=1)]), target)
            before = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "不同正文"):
                update_bundle(payload([message("篡改", 1)]), target)
            self.assertEqual(before, target.read_bytes())
            target.write_text("corrupt", encoding="utf-8")
            with self.assertRaises(ValueError):
                update_bundle(payload([message(identifier=2)]), target)
            self.assertEqual(target.read_text(), "corrupt")

    def test_different_source_account_and_contact_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            update_bundle(payload([message(identifier=1)]), target)
            for changed in ({"source": "other"}, {"account_id": "other"}, {"contact_username": "other"}):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    update_bundle(payload([message(identifier=2)], **changed), target)

    def test_transcript_enrichment_keeps_identity_and_changes_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            voice = {**message("[语音]", 1), "type": "voice"}
            first = update_bundle(payload([voice]), target)
            updated = update_bundle(payload([{**voice, "transcript": "想你"}]), target)
            self.assertEqual(updated["total"], 1)
            self.assertEqual(updated["last_import"]["updated"], 1)
            self.assertEqual(first["messages"][0]["message_id"], updated["messages"][0]["message_id"])
            self.assertNotEqual(first["messages_digest"], updated["messages_digest"])

    def test_failed_commit_preserves_old_file_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            update_bundle(payload([message(identifier=1)]), target)
            before = target.read_bytes()
            original_replace = os.replace
            def fail_canonical_commit(source, destination):
                if Path(destination) == target:
                    raise OSError("disk error")
                return original_replace(source, destination)
            with patch("bundle_store.os.replace", side_effect=fail_canonical_commit):
                with self.assertRaises(OSError):
                    update_bundle(payload([message(identifier=2)]), target)
            self.assertEqual(before, target.read_bytes())
            self.assertFalse(target.with_suffix(".import.lock").exists())

    def test_normalized_import_cli_preserves_incremental_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "normalized.json"
            source.write_text(json.dumps(payload([message(identifier=1)])), encoding="utf-8")
            command = [sys.executable, str(SCRIPTS / "update_chat_bundle.py"), "--input", str(source),
                       "--output-dir", str(root / "contacts")]
            first = subprocess.run(command, check=True, capture_output=True, encoding="utf-8")
            source.write_text(json.dumps(payload([message(identifier=1), message("新增", 2)])), encoding="utf-8")
            second = subprocess.run(command, check=True, capture_output=True, encoding="utf-8")
            self.assertEqual(json.loads(first.stdout)["total"], 1)
            self.assertEqual(json.loads(second.stdout)["total"], 2)
            self.assertEqual(json.loads(second.stdout)["import"]["added"], 1)

    def test_existing_lock_and_empty_import_preserve_data(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.json"
            update_bundle(payload([message(identifier=1)]), target)
            with self.assertRaises(ValueError):
                update_bundle(payload([]), target)
            target.with_suffix(".import.lock").touch()
            with self.assertRaisesRegex(ValueError, "导入锁"):
                update_bundle(payload([message(identifier=2)]), target)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = normalize_payload(payload([message("想你", 1)]))
        self.mid = self.data["messages"][0]["message_id"]
        self.stats = {"messages_digest": self.data["messages_digest"], "basic": {"total_messages": 1}}
        self.analysis = {"schema_version": "2.1", "messages_digest": self.data["messages_digest"],
                         "key_findings": [{"title": "表达想念", "quote": "想你", "analysis": "表达了想念",
                                           "evidence_message_ids": [self.mid], "evidence_level": "medium",
                                           "stats_fields": ["basic.total_messages"]}]}

    def test_links_resolve_to_original_message(self):
        html = render_html(self.stats, self.analysis, "测试", self.data)
        self.assertIn(f'href="#evidence-{self.mid}"', html)
        self.assertIn(f'id="evidence-{self.mid}"', html)
        self.assertIn("想你", html)

    def test_fabricated_ids_quotes_and_fields_are_rejected(self):
        for field, value in (("evidence_message_ids", ["msg_" + "0" * 64]),
                             ("quote", "并不存在的引用"), ("stats_fields", ["basic.missing"]),
                             ("evidence_message_ids", "string")):
            analysis = copy.deepcopy(self.analysis)
            analysis["key_findings"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_evidence(self.stats, analysis, self.data)

    def test_stale_stats_or_analysis_are_rejected(self):
        for field in ("stats", "analysis"):
            stats, analysis = copy.deepcopy(self.stats), copy.deepcopy(self.analysis)
            (stats if field == "stats" else analysis)["messages_digest"] = "wrong"
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_evidence(stats, analysis, self.data)

    def test_strict_analysis_requires_digest_and_message_evidence(self):
        for changes in ({"messages_digest": None}, {"key_findings": [{"title": "无证据"}]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_evidence(self.stats, {**self.analysis, **changes}, self.data)
        with self.assertRaises(ValueError):
            validate_evidence(self.stats, self.analysis)

    def test_missing_numeric_sample_cannot_be_confident_evidence(self):
        self.stats["reply_speed"] = {"my_avg_seconds": None}
        self.analysis["key_findings"][0]["stats_fields"] = ["reply_speed.my_avg_seconds"]
        with self.assertRaisesRegex(ValueError, "缺失统计"):
            validate_evidence(self.stats, self.analysis, self.data)

    def test_evidence_content_is_html_escaped(self):
        data = normalize_payload(payload([message('<img src=x onerror="bad()">', 1)]))
        stats = {"messages_digest": data["messages_digest"]}
        analysis = {"evidence": [{"claim": "<script>bad()</script>",
                                 "evidence_message_ids": [data["messages"][0]["message_id"]]}]}
        html = render_html(stats, analysis, "测试", data)
        self.assertNotIn('<img src=x onerror="bad()">', html)
        self.assertIn("&lt;img", html)

    def test_conversion_statistics_sampling_and_report_with_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export.json"
            source.write_text(json.dumps([{"localId": 1, "localType": 1, "createTime": 1700000000,
                                           "isSend": 1, "parsedContent": "想你"}]), encoding="utf-8")
            convert_command = [sys.executable, str(SCRIPTS / "convert_weflow_cli.py"),
                               "--input", str(source), "--contact", "测试", "--contact-id", "friend",
                               "--output-dir", str(root / "contacts")]
            subprocess.run(convert_command, check=True, capture_output=True)
            repeat = subprocess.run(convert_command, check=True, capture_output=True, encoding="utf-8")
            self.assertEqual(json.loads(repeat.stdout)["import"]["status"], "already_imported")
            messages_path = next((root / "contacts").glob("*/messages.json"))
            data = json.loads(messages_path.read_text(encoding="utf-8"))
            stats_path = messages_path.parent / "stats.json"
            subprocess.run([sys.executable, str(SCRIPTS / "stats_analyzer.py"), "--input", str(messages_path),
                            "--output", str(stats_path)], check=True, capture_output=True)
            history_path = messages_path.parent / "chat_history.txt"
            subprocess.run([sys.executable, str(SCRIPTS / "build_chat_history.py"), "--input", str(messages_path),
                            "--output", str(history_path)], check=True, capture_output=True)
            self.assertIn(data["messages"][0]["message_id"], history_path.read_text(encoding="utf-8"))
            analysis = {"schema_version": "2.1", "messages_digest": data["messages_digest"],
                        "key_findings": [{"title": "表达想念", "quote": "想你",
                                          "evidence_message_ids": [data["messages"][0]["message_id"]]}]}
            analysis_path = messages_path.parent / "analysis.json"
            analysis_path.write_text(json.dumps(analysis), encoding="utf-8")
            command = [sys.executable, str(SCRIPTS / "generate_html_report.py"), "--stats", str(stats_path),
                       "--analysis", str(analysis_path), "--contact", "测试", "--output", str(root / "reports")]
            for _ in range(2):
                subprocess.run(command, check=True, capture_output=True)
            manifests = list((root / "reports").glob("*.manifest.json"))
            self.assertEqual(len(manifests), 2)
            self.assertEqual(len(list((root / "reports").glob("*.html"))), 2)
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["messages_digest"], data["messages_digest"])
            self.assertEqual(manifest["analysis_snapshot"], analysis)


if __name__ == "__main__":
    unittest.main()
