import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analysis_evidence import validate_evidence
from generate_html_report import render_emotional_asymmetry
from message_normalizer import normalize_payload
from query_chat_context import query_context
from scoring_calibration import calibrate_balance


def stats():
    return {"basic": {"my_messages": 100, "their_messages": 100},
            "initiative": {"my_starts": 10, "their_starts": 10},
            "repair": {"me_repair_count": 4, "them_repair_count": 4},
            "reply_speed": {"my_median_seconds": 60, "their_median_seconds": 60,
                            "my_sample_count": 10, "their_sample_count": 10}}


class CalibrationTests(unittest.TestCase):
    def test_balanced_behavior_receives_ten(self):
        result = calibrate_balance(stats())
        self.assertEqual(result["symmetry_score"], 10)
        self.assertEqual(result["coverage"], 1)
        self.assertEqual(result["investment_direction"]["observed_direction"], "mixed_or_balanced")

    def test_swapping_people_keeps_score_and_reverses_direction(self):
        first = stats()
        first["basic"] = {"my_messages": 160, "their_messages": 40}
        first["initiative"] = {"my_starts": 16, "their_starts": 4}
        first["repair"] = {"me_repair_count": 6, "them_repair_count": 2}
        first["reply_speed"]["their_median_seconds"] = 600
        second = copy.deepcopy(first)
        for section, pairs in {"basic": [("my_messages", "their_messages")],
                               "initiative": [("my_starts", "their_starts")],
                               "repair": [("me_repair_count", "them_repair_count")],
                               "reply_speed": [("my_median_seconds", "their_median_seconds"),
                                               ("my_sample_count", "their_sample_count")]}.items():
            for left, right in pairs:
                second[section][left], second[section][right] = second[section][right], second[section][left]
        a, b = calibrate_balance(first), calibrate_balance(second)
        self.assertEqual(a["symmetry_score"], b["symmetry_score"])
        self.assertEqual(a["investment_direction"]["observed_direction"], "me")
        self.assertEqual(b["investment_direction"]["observed_direction"], "them")

    def test_faster_reply_difference_is_relative_not_one_day_offset(self):
        data = stats()
        data["reply_speed"]["their_median_seconds"] = 600
        result = calibrate_balance(data)
        self.assertAlmostEqual(result["dimensions"]["reply"]["value"], 2 / 11, places=5)

    def test_missing_resumption_is_not_treated_as_balance(self):
        data = stats()
        data["repair"] = {"me_repair_count": 0, "them_repair_count": 0}
        result = calibrate_balance(data)
        self.assertEqual(result["coverage"], .7)
        self.assertIsNone(result["dimensions"]["resumption"]["value"])
        self.assertEqual(result["symmetry_score"], 10)
        self.assertEqual(result["evidence_level"], "medium")

    def test_insufficient_samples_do_not_produce_a_score(self):
        data = stats()
        data["reply_speed"]["my_sample_count"] = 2
        data["repair"] = {"me_repair_count": 0, "them_repair_count": 0}
        result = calibrate_balance(data)
        self.assertIsNone(result["symmetry_score"])
        self.assertEqual(result["coverage"], .5)
        self.assertIsNone(calibrate_balance({})["symmetry_score"])

    def test_one_sided_conversation_can_only_use_observed_dimensions(self):
        data = stats()
        data["basic"]["their_messages"] = 0
        data["initiative"]["their_starts"] = 0
        data["repair"] = {}
        data["reply_speed"] = {}
        result = calibrate_balance(data)
        self.assertIsNone(result["symmetry_score"])
        self.assertEqual(result["dimensions"]["messages"]["value"], 0)
        self.assertEqual(result["investment_direction"]["observed_direction"], "me")

    def test_report_uses_engine_score_and_renders_missing_dimensions(self):
        calibration = calibrate_balance(stats())
        html = render_emotional_asymmetry({"symmetry_score": 1}, calibration)
        self.assertIn('>10.0<span', html)
        self.assertIn("有效权重覆盖 100%", html)
        self.assertIn("聊天行为对称性", html)
        empty = render_emotional_asymmetry({"symmetry_score": None}, calibrate_balance({}))
        self.assertIn("数据不足", empty)
        self.assertNotIn("None", empty)

    def test_strict_analysis_cannot_replace_engine_score(self):
        data = normalize_payload({"messages": []})
        calibrated = {"messages_digest": data["messages_digest"], "balance_calibration": calibrate_balance(stats())}
        analysis = {"schema_version": "2.1", "messages_digest": data["messages_digest"],
                    "emotional_asymmetry": {"symmetry_score": 1}}
        with self.assertRaisesRegex(ValueError, "统计引擎"):
            validate_evidence(calibrated, analysis, data)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.data = normalize_payload({"source": "test", "contact_username": "friend", "messages": [
            {"source_message_id": i, "sender": "me" if i % 2 else "them", "timestamp": 1704067200 + i * 86400,
             "type": "text", "content": "想你" if i in (3, 4) else f"消息{i}"} for i in range(8)]})
        self.ids = [m["message_id"] for m in self.data["messages"]]

    def test_id_query_returns_neighbors_in_order(self):
        result = query_context(self.data, [self.ids[3]], before=1, after=1,
                               expected_digest=self.data["messages_digest"])
        self.assertEqual([m["message_id"] for m in result["messages"]], self.ids[2:5])
        self.assertFalse(result["truncated"])

    def test_keyword_windows_overlap_without_duplicate_messages(self):
        result = query_context(self.data, keyword="想你", before=1, after=1)
        self.assertEqual(result["matched_count"], 2)
        self.assertEqual([m["message_id"] for m in result["messages"]], self.ids[2:6])

    def test_scope_excludes_neighbors_and_out_of_scope_anchor(self):
        result = query_context(self.data, [self.ids[3]], since="2024-01-04", until="2024-01-04")
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["messages"][0]["message_id"], self.ids[3])
        with self.assertRaisesRegex(ValueError, "时间范围"):
            query_context(self.data, [self.ids[2]], since="2024-01-04")

    def test_budget_marks_truncation_and_omitted_anchors(self):
        result = query_context(self.data, [self.ids[3]], before=2, after=2, max_messages=1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["returned_anchor_ids"], [])
        result = query_context(self.data, keyword="想你", max_matches=1)
        self.assertTrue(result["truncated"])
        result = query_context(self.data, [self.ids[3]], max_chars=1)
        self.assertEqual(result["returned_count"], 0)
        self.assertTrue(result["truncated"])

    def test_invalid_queries_and_stale_digest_fail(self):
        for kwargs in ({"message_ids": ["bad"]}, {"keyword": " "}, {"keyword": "想你", "before": -1},
                       {"keyword": "想你", "max_messages": 201}, {"keyword": "想你", "expected_digest": "old"},
                       {"keyword": "想你", "since": "2024-02-01", "until": "2024-01-01"},
                       {"keyword": "想你", "message_ids": [self.ids[3]]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                query_context(self.data, **kwargs)

    def test_no_match_does_not_claim_absence_of_event(self):
        result = query_context(self.data, keyword="无匹配")
        self.assertEqual(result["matched_count"], 0)
        self.assertFalse(result["truncated"])
        self.assertIn("不代表事件从未发生", result["note"])

    def test_voice_transcript_is_searchable(self):
        voice = {"messages": [{"sender": "them", "timestamp": 1704067200,
                               "type": "voice", "content": "[语音]", "transcript": "早点休息"}]}
        self.assertEqual(query_context(voice, keyword="休息")["matched_count"], 1)

    def test_cli_writes_reusable_context_with_original_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "messages.json", root / "context.json"
            source.write_text(json.dumps(self.data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPTS / "query_chat_context.py"),
                                     "--input", str(source), "--message-id", self.ids[3],
                                     "--expected-digest", self.data["messages_digest"],
                                     "--before", "1", "--after", "1", "--output", str(output)],
                                    check=True, capture_output=True, encoding="utf-8")
            self.assertNotIn("messages", json.loads(result.stdout))
            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["messages_digest"], self.data["messages_digest"])
            self.assertEqual(context["returned_anchor_ids"], [self.ids[3]])

    def test_stats_context_and_evidence_report_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            messages_path, stats_path = root / "messages.json", root / "stats.json"
            messages_path.write_text(json.dumps(self.data), encoding="utf-8")
            subprocess.run([sys.executable, str(SCRIPTS / "stats_analyzer.py"),
                            "--input", str(messages_path), "--output", str(stats_path)],
                           check=True, capture_output=True)
            generated = json.loads(stats_path.read_text(encoding="utf-8"))
            context = query_context(self.data, [self.ids[3]], before=1, after=1,
                                    expected_digest=generated["messages_digest"])
            analysis = {"schema_version": "2.1", "messages_digest": context["messages_digest"],
                        "emotional_asymmetry": {"symmetry_score": generated["balance_calibration"]["symmetry_score"]},
                        "key_findings": [{"quote": "想你", "evidence_message_ids": context["returned_anchor_ids"]}]}
            validate_evidence(generated, analysis, self.data)
            self.assertEqual(generated["scoring_version"], "2.2")
            self.assertIsNone(generated["balance_calibration"]["symmetry_score"])


if __name__ == "__main__":
    unittest.main()
