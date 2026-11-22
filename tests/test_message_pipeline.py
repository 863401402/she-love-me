import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from convert_markdown import parse_markdown
from convert_ciphertalk import convert_payload as convert_ciphertalk_payload
from convert_weflow import convert_payload
from convert_weflow_cli import convert_payload as convert_weflow_cli_payload
from generate_html_report import render_personality
from message_normalizer import analytical_text, normalize_payload, normalize_timestamp
from setup_check import decryptor_capabilities


class TimestampNormalizationTests(unittest.TestCase):
    def test_normalizes_seconds_milliseconds_microseconds_and_nanoseconds(self):
        expected = 1692946166
        self.assertEqual(normalize_timestamp(expected), expected)
        self.assertEqual(normalize_timestamp(expected * 1000), expected)
        self.assertEqual(normalize_timestamp(expected * 1_000_000), expected)
        self.assertEqual(normalize_timestamp(expected * 1_000_000_000), expected)

    def test_normalizes_date_text(self):
        timestamp = normalize_timestamp("2026-08-12 20:10")
        self.assertGreater(timestamp, 1_700_000_000)

    def test_payload_sorts_and_drops_invalid_messages(self):
        payload = normalize_payload({"messages": [
            {"sender": "them", "timestamp": 1692946167000, "type": "text", "content": "后"},
            {"sender": "me", "timestamp": 1692946166, "type": "text", "content": "前"},
            {"sender": "unknown", "timestamp": 1692946168, "type": "text", "content": "丢弃"},
        ]}, drop_invalid=True)
        self.assertEqual([item["content"] for item in payload["messages"]], ["前", "后"])
        self.assertEqual(payload["normalization"]["dropped_messages"], 1)

    def test_same_timestamp_messages_keep_numeric_source_order(self):
        payload = normalize_payload({"messages": [
            {"local_id": 1, "sender": "me", "timestamp": 1692946166, "content": "第一条"},
            {"local_id": 2, "sender": "them", "timestamp": 1692946166, "content": "第二条"},
            {"local_id": 10, "sender": "me", "timestamp": 1692946166, "content": "第十条"},
        ]})
        self.assertEqual(
            [item["content"] for item in payload["messages"]],
            ["第一条", "第二条", "第十条"],
        )

    def test_date_text_outside_supported_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "时间戳超出支持范围"):
            normalize_timestamp("1900-01-01T00:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "时间戳超出支持范围"):
            normalize_timestamp("2101-01-01T00:00:00+00:00")


class ImportTests(unittest.TestCase):
    def test_markdown_import(self):
        messages = parse_markdown(
            "[2026-08-12 20:10] 我: 你好\n[2026-08-12 20:11] 小王: 你好呀",
            "我",
        )
        payload = normalize_payload({"messages": messages})
        self.assertEqual([item["sender"] for item in payload["messages"]], ["me", "them"])

    def test_weflow_import_normalizes_milliseconds_and_transcript(self):
        payload, _ = convert_payload({
            "session": {"wxid": "wxid_friend", "nickname": "小王"},
            "messages": [{
                "localId": 1,
                "isSend": 0,
                "senderUsername": "wxid_friend",
                "createTime": 1692946166000,
                "type": "语音消息",
                "localType": 34,
                "voiceText": "早点休息",
            }],
        })
        message = payload["messages"][0]
        self.assertEqual(message["timestamp"], 1692946166)
        self.assertEqual(analytical_text(message), "早点休息")

    def test_weflow_drops_invalid_emoji_from_both_outputs(self):
        payload, emojis = convert_payload({
            "session": {"wxid": "wxid_friend"},
            "messages": [{
                "localId": 1,
                "isSend": 0,
                "createTime": 0,
                "type": "动画表情",
                "localType": 47,
                "emojiMd5": "bad",
            }],
        })
        self.assertEqual(payload["messages"], [])
        self.assertEqual(emojis, {})

    def test_weflow_cli_imports_top_level_array(self):
        payload = normalize_payload(convert_weflow_cli_payload([{
            "localId": 7,
            "localType": 1,
            "createTime": 1692946166000,
            "isSend": 1,
            "senderUsername": "wxid_me",
            "parsedContent": "早点休息",
        }], "小王", "wxid_friend"), drop_invalid=True)
        self.assertEqual(payload["source"], "weflow-cli")
        self.assertEqual(payload["messages"][0]["sender"], "me")
        self.assertEqual(payload["messages"][0]["content"], "早点休息")
        self.assertEqual(payload["messages"][0]["timestamp"], 1692946166)

    def test_weflow_cli_infers_incoming_from_contact_id(self):
        payload = normalize_payload(convert_weflow_cli_payload([{
            "localId": 9,
            "localType": 1,
            "createTime": 1692946168,
            "isSend": None,
            "senderUsername": "wxid_friend",
            "parsedContent": "在的",
        }], "小王", "wxid_friend"), drop_invalid=True)
        self.assertEqual(payload["messages"][0]["sender"], "them")

    def test_weflow_cli_drops_unresolvable_direction_with_warning(self):
        payload = normalize_payload(convert_weflow_cli_payload([{
            "localId": 10,
            "localType": 1,
            "createTime": 1692946169,
            "isSend": None,
            "senderUsername": "unknown",
            "parsedContent": "方向未知",
        }], "小王", "wxid_friend"), drop_invalid=True)
        self.assertEqual(payload["messages"], [])
        self.assertEqual(payload["normalization"]["dropped_messages"], 1)

    def test_ciphertalk_imports_wrapped_messages(self):
        payload = normalize_payload(convert_ciphertalk_payload({"messages": [{
            "localId": 8,
            "createTime": 1692946167,
            "direction": "in",
            "senderUsername": "wxid_friend",
            "type": 34,
            "content": "",
            "transcript": "你也早点休息",
        }]}, "小王", "wxid_friend"), drop_invalid=True)
        message = payload["messages"][0]
        self.assertEqual(payload["source"], "ciphertalk")
        self.assertEqual(message["sender"], "them")
        self.assertEqual(message["type"], "voice")
        self.assertEqual(message["content"], "[语音消息]")
        self.assertEqual(analytical_text(message), "你也早点休息")

    def test_ciphertalk_desktop_detailed_json(self):
        payload = normalize_payload(convert_ciphertalk_payload({"messages": [{
            "localId": 9,
            "createTime": 1692946168,
            "isSend": 1,
            "senderUsername": "wxid_me",
            "localType": 1,
            "content": "桌面版导出",
        }]}, "小王", "wxid_friend"), drop_invalid=True)
        self.assertEqual(payload["messages"][0]["sender"], "me")
        self.assertEqual(payload["messages"][0]["type"], "text")

    def test_ciphertalk_desktop_chatlab_json(self):
        payload = normalize_payload(convert_ciphertalk_payload({
            "meta": {"ownerId": "wxid_me"},
            "messages": [{
                "timestamp": 1692946169,
                "sender": "wxid_friend",
                "type": 0,
                "content": "ChatLab 导出",
            }],
        }, "小王", "wxid_friend"), drop_invalid=True)
        self.assertEqual(payload["messages"][0]["sender"], "them")


class ReportRenderingTests(unittest.TestCase):
    def test_personality_structured_fields_do_not_leak_dict_repr(self):
        html = render_personality({
            "user_attachment": {
                "value": "安全型偏回避",
                "evidence_level": "medium",
                "reason": "遇到冲突时先降温",
            },
            "partner_attachment": {
                "value": None,
                "evidence_level": "insufficient",
                "reason": "样本不足",
            },
        }, "小王")
        self.assertIn("安全型偏回避", html)
        self.assertIn("样本不足", html)
        self.assertNotIn("{'value'", html)


class DecryptorCompatibilityTests(unittest.TestCase):
    def test_detects_supported_entrypoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "main.py").write_text("", encoding="utf-8")
            self.assertEqual(decryptor_capabilities(root), {
                "default_flow": True,
                "macos_flow": False,
            })


class EndToEndTests(unittest.TestCase):
    def test_weflow_cli_json_to_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "weflow-cli.json"
            source.write_text(json.dumps([{
                "localId": 1, "localType": 1, "createTime": 1692946166,
                "isSend": 1, "senderUsername": "wxid_me", "parsedContent": "你好",
            }, {
                "localId": 2, "localType": 1, "createTime": 1692946167,
                "isSend": 0, "senderUsername": "wxid_friend", "parsedContent": "你好呀",
            }], ensure_ascii=False), encoding="utf-8")
            contacts = root / "contacts"
            result = subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "convert_weflow_cli.py"),
                "--input", str(source), "--contact", "小王",
                "--contact-id", "wxid_friend", "--output-dir", str(contacts),
            ], check=True, capture_output=True, text=True, encoding="utf-8")
            output = json.loads(result.stdout)
            payload = json.loads(Path(output["messages_path"]).read_text(encoding="utf-8"))
            self.assertEqual(output["total"], 2)
            self.assertEqual([item["sender"] for item in payload["messages"]], ["me", "them"])

    def test_ciphertalk_json_to_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "ciphertalk.json"
            source.write_text(json.dumps([{
                "localId": 1, "createTime": 1692946166,
                "direction": "out", "type": 1, "content": "你好",
            }, {
                "localId": 2, "createTime": 1692946167,
                "direction": "in", "type": 1, "content": "你好呀",
            }], ensure_ascii=False), encoding="utf-8")
            contacts = root / "contacts"
            result = subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "convert_ciphertalk.py"),
                "--input", str(source), "--contact", "小王",
                "--contact-id", "wxid_friend", "--output-dir", str(contacts),
            ], check=True, capture_output=True, text=True, encoding="utf-8")
            output = json.loads(result.stdout)
            payload = json.loads(Path(output["messages_path"]).read_text(encoding="utf-8"))
            self.assertEqual(output["total"], 2)
            self.assertEqual([item["sender"] for item in payload["messages"]], ["me", "them"])

    def test_markdown_to_report_pipeline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            markdown = root / "chat.md"
            markdown.write_text(
                "[2026-08-10 20:10] 我: 早点休息\n"
                "[2026-08-10 20:11] 小王: 好的，你也是\n"
                "[2026-08-12 08:00] 小王: 早安\n",
                encoding="utf-8",
            )
            contacts = root / "contacts"
            subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "convert_markdown.py"),
                "--input", str(markdown), "--my-name", "我",
                "--contact", "小王", "--output-dir", str(contacts),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            messages_path = next(contacts.glob("*/messages.json"))
            bundle_dir = messages_path.parent

            subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "stats_analyzer.py"),
                "--input", str(messages_path), "--output", str(bundle_dir / "stats.json"),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "build_chat_history.py"),
                "--input", str(messages_path), "--output", str(bundle_dir / "chat_history.txt"),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (bundle_dir / "analysis.json").write_text(json.dumps({
                "personality": {
                    "partner_attachment": {
                        "value": "安全型",
                        "evidence_level": "medium",
                        "reason": "回应稳定",
                    }
                }
            }, ensure_ascii=False), encoding="utf-8")
            report_dir = bundle_dir / "reports"
            subprocess.run([
                sys.executable, str(SCRIPTS_DIR / "generate_html_report.py"),
                "--stats", str(bundle_dir / "stats.json"),
                "--analysis", str(bundle_dir / "analysis.json"),
                "--contact", "小王", "--output", str(report_dir),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            report = next(report_dir.glob("*.html")).read_text(encoding="utf-8")
            self.assertIn("安全型", report)
            self.assertNotIn("{'value'", report)


if __name__ == "__main__":
    unittest.main()
