import json
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_chat_history import load_messages
from message_normalizer import normalize_payload
from stats_analyzer import (
    analyze_linguistics, detect_bombing, detect_cold_replies,
    analyze_reply_times, summarize_reply_times, compute_scores, detect_unanswered,
)
from generate_html_report import render_html
from build_chat_history import build_generate


def msg(sender, content, timestamp, type_="text"):
    return {"sender": sender, "timestamp": timestamp, "type": type_, "content": content}


class BombingDetectionTests(unittest.TestCase):
    def test_trailing_run_is_counted(self):
        messages = [msg("them", "在吗", 1000 + i) for i in range(5)]
        result = detect_bombing(messages)
        self.assertEqual(result["their_bomb_count"], 1)
        self.assertEqual(result["their_max_consecutive"], 5)
        self.assertEqual(result["my_bomb_count"], 0)

    def test_runs_in_the_middle_are_still_counted(self):
        messages = (
            [msg("me", "早", 1000 + i) for i in range(3)]
            + [msg("them", "嗯", 2000)]
            + [msg("me", "吃了吗", 3000 + i) for i in range(4)]
        )
        result = detect_bombing(messages)
        self.assertEqual(result["my_bomb_count"], 2)
        self.assertEqual(result["my_max_consecutive"], 4)

    def test_short_trailing_run_is_not_a_bomb(self):
        messages = [msg("me", "好", 1000), msg("me", "嗯", 1001)]
        result = detect_bombing(messages)
        self.assertEqual(result["my_bomb_count"], 0)
        self.assertEqual(result["my_max_consecutive"], 2)

    def test_cross_day_messages_do_not_form_a_bomb(self):
        result = detect_bombing([msg("me", "早", 1000 + i * 86400) for i in range(5)])
        self.assertEqual(result["my_bomb_count"], 0)
        self.assertEqual(result["my_max_consecutive"], 1)

    def test_gap_closes_and_counts_both_runs(self):
        messages = [msg("me", "你好", 1000 + i) for i in range(3)]
        messages += [msg("me", "你好", 1000 + 86400 + i) for i in range(4)]
        result = detect_bombing(messages)
        self.assertEqual(result["my_bomb_count"], 2)
        self.assertEqual(result["my_max_consecutive"], 4)


class ReliabilityTests(unittest.TestCase):
    def test_delayed_reply_after_alternating_messages_is_counted(self):
        result = detect_unanswered([
            msg("me", "你好", 1000), msg("them", "你好呀", 1100),
            msg("me", "下班啦", 1100 + 7201),
        ])
        self.assertEqual(result["their_unanswered"], 1)
        self.assertEqual(result["my_unanswered"], 0)
        self.assertFalse(result["read_receipts_available"])

    def test_delay_threshold_and_unobserved_tail(self):
        result = detect_unanswered([
            msg("me", "你好", 1000), msg("them", "收到", 1000 + 7200),
            msg("them", "晚安", 1000 + 86400),
        ])
        self.assertEqual(result["my_unanswered"], 0)
        self.assertEqual(result["their_unanswered"], 0)

    def test_affectionate_short_messages_are_not_cold(self):
        result = detect_cold_replies([
            msg("them", text, 1000 + i)
            for i, text in enumerate(["爱你", "想你", "谢谢", "早安", "嗯"])
        ])
        self.assertEqual(result["their_cold_count"], 1)
        self.assertEqual(result["their_short_count"], 5)
        self.assertEqual(result["their_text_count"], 5)
        self.assertTrue(result["requires_context"])

    def test_no_reply_samples_are_null(self):
        messages = [msg("me", "你好", 1000), msg("me", "晚安", 2000)]
        self.assertEqual(analyze_reply_times(messages), (None, None))
        result = summarize_reply_times(messages)
        self.assertIsNone(result["speed_ratio"])
        self.assertIsNone(result["my_median_seconds"])
        self.assertIsNone(result["their_p90_seconds"])
        self.assertEqual(result["my_sample_count"], 0)
        self.assertEqual(result["their_avg_human"], "数据不足")

    def test_reply_distribution_and_filter_boundaries(self):
        gaps = [9, 10, 20, 86400, 86401]
        messages = [msg("me", "你好", 1000)]
        timestamp = 1000
        for i, gap in enumerate(gaps):
            timestamp += gap
            messages.append(msg("them" if i % 2 == 0 else "me", "收到", timestamp))
        result = summarize_reply_times(messages)
        self.assertEqual(result["my_sample_count"], 2)
        self.assertEqual(result["their_sample_count"], 1)
        self.assertEqual(result["my_median_seconds"], 43205)
        self.assertEqual(result["my_p90_seconds"], 86400)
        self.assertEqual(result["their_avg_seconds"], 20)

    def test_missing_reply_data_does_not_add_nonresponse_penalty(self):
        stats = {
            "basic": {"total_messages": 2, "my_messages": 1, "their_messages": 1},
            "initiative": {"my_starts": 1, "their_starts": 0},
            "reply_speed": {"my_avg_seconds": 60, "their_avg_seconds": None},
            "bombing": {"my_bomb_count": 0},
            "unanswered": {"my_unanswered": 0},
            "goodnight": {"my_goodnight": 0, "their_goodnight": 0},
            "cold_response": {"their_cold_count": 0, "their_text_count": 0},
            "message_length": {"my_avg_chars": 2, "their_avg_chars": 0},
        }
        missing = compute_scores(stats)
        stats["reply_speed"]["my_avg_seconds"] = None
        self.assertEqual(missing, compute_scores(stats))
        self.assertEqual(missing["loved_index"], 20)
        # Old stats used zero for missing data; these should also avoid the old penalty.
        stats["reply_speed"] = {"my_avg_seconds": 60, "their_avg_seconds": 0}
        self.assertEqual(missing, compute_scores(stats))

    def test_cold_ratio_uses_text_samples_instead_of_all_media(self):
        stats = {
            "basic": {"total_messages": 101, "my_messages": 1, "their_messages": 100},
            "initiative": {"my_starts": 1, "their_starts": 0},
            "reply_speed": {"my_avg_seconds": None, "their_avg_seconds": None},
            "bombing": {"my_bomb_count": 0}, "unanswered": {"my_unanswered": 0},
            "goodnight": {"my_goodnight": 0, "their_goodnight": 0},
            "cold_response": {"their_cold_count": 1, "their_text_count": 1},
            "message_length": {"my_avg_chars": 2, "their_avg_chars": 1},
        }
        self.assertEqual(compute_scores(stats)["cold_index"], 40)

    def test_single_sender_pipeline_generates_readable_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "messages.json"
            source.write_text(json.dumps({"messages": [
                msg("me", "想你", 1_700_000_000),
                msg("me", "爱你", 1_700_086_400),
            ]}, ensure_ascii=False), encoding="utf-8")
            target = root / "stats.json"
            subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "stats_analyzer.py"),
                "--input", str(source), "--output", str(target),
            ], check=True, capture_output=True)
            stats = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(stats["scoring_version"], "2.2")
            self.assertEqual(stats["cold_response"]["my_cold_count"], 0)
            self.assertEqual(stats["bombing"]["my_max_consecutive"], 1)
            self.assertEqual(stats["scores"]["loved_index"], 0)
            html = render_html(stats, {}, "测试联系人")
            self.assertIn("数据不足", html)
            self.assertIn("有效样本：你 0 条 / 对方 0 条", html)
            self.assertNotIn("None", html)
            self.assertNotIn("对方比你慢这么多倍", html)

    def test_report_accepts_old_stats_without_sample_counts(self):
        html = render_html({"reply_speed": {
            "my_avg_human": "1 分钟", "their_avg_human": "2 分钟", "speed_ratio": 2,
        }}, {}, "测试联系人")
        self.assertIn("1 分钟", html)
        self.assertIn("旧版统计未记录样本数", html)

    def test_report_escapes_reply_display_strings(self):
        html = render_html({"reply_speed": {"my_avg_human": "<script>bad()</script>"}}, {}, "测试")
        self.assertNotIn("<script>bad()</script>", html)
        self.assertIn("&lt;script&gt;bad()&lt;/script&gt;", html)


class PronounCountingTests(unittest.TestCase):
    def assert_pronouns(self, text, we, i):
        message = msg("me", text, 1000)
        result = analyze_linguistics([message], [message])
        self.assertEqual(result["pronoun_we_count"]["me"], we, text)
        self.assertEqual(result["pronoun_i_count"]["me"], i, text)

    def test_standalone_wo_after_women(self):
        self.assert_pronouns("我很想你，我们见面吧", we=1, i=1)

    def test_zanmen_contains_no_standalone_wo(self):
        self.assert_pronouns("咱们明天去", we=1, i=0)

    def test_women_only(self):
        self.assert_pronouns("我们加油", we=1, i=0)

    def test_zanmen_not_double_counted(self):
        self.assert_pronouns("我们咱们", we=2, i=0)


class ChatHistorySamplingTests(unittest.TestCase):
    def _generate(self, messages):
        payload = normalize_payload({"messages": messages}, drop_invalid=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "chat_history.txt"
            build_generate(payload, None, str(output))
            return output.read_text(encoding="utf-8")

    def test_recent_30d_window_keeps_newest_messages(self):
        base = 1_700_000_000  # 归一化器要求真实纪元时间戳
        old = [msg("me", f"旧消息{i:03d}", base + i) for i in range(200)]
        new = [msg("them", f"新消息{i:03d}", base + 25 * 86400 + 1000 + i) for i in range(250)]
        text = self._generate(old + new)
        window3 = text.split("窗口 3")[1].split("窗口 4")[0]
        self.assertIn("新消息249", window3)
        self.assertNotIn("旧消息", window3)

    def test_overview_labels_share_as_message_ratio(self):
        text = self._generate([
            msg("me", "你好", 1_700_000_000),
            msg("them", "你好呀", 1_700_000_100),
        ])
        self.assertIn("消息占比", text)
        self.assertNotIn("发起占比: 我方", text)
        self.assertIn("stats.json 的 initiative", text)


class BomToleranceTests(unittest.TestCase):
    def test_load_messages_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "messages.json"
            path.write_text(json.dumps({
                "messages": [msg("me", "你好", 1000)],
            }, ensure_ascii=False), encoding="utf-8-sig")
            data = load_messages(path)
            self.assertEqual(data["messages"][0]["content"], "你好")


if __name__ == "__main__":
    unittest.main()
