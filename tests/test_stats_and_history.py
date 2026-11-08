import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_chat_history import load_messages
from message_normalizer import normalize_payload
from stats_analyzer import analyze_linguistics, detect_bombing
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
