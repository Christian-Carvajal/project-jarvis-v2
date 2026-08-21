import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai_engine import AIEngine, PCAutomationEngine, DeviceAction, AssistantIntentResponse


class TestPCNavigation(unittest.TestCase):
    def setUp(self):
        self.ai = AIEngine()

    def test_spotify_open(self):
        res = self.ai.parse_command("open my spotify")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "spotify")
        self.assertEqual(act.action, "open_app")

    def test_spotify_play_something(self):
        res = self.ai.parse_command("play something in spotify")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "spotify")
        self.assertEqual(act.action, "play_music")
        self.assertIn(act.value, [None, ""])

    def test_spotify_play_song(self):
        res = self.ai.parse_command("play blinding lights in spotify")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "spotify")
        self.assertEqual(act.action, "play_music")
        self.assertEqual(act.value.lower(), "blinding lights")

    def test_spotify_play_24k_magic(self):
        res = self.ai.parse_command("play 24k magic on spotify")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "spotify")
        self.assertEqual(act.action, "play_music")
        self.assertEqual(act.value.lower(), "24k magic")

    def test_youtube_open(self):
        res = self.ai.parse_command("open youtube")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "youtube")
        self.assertEqual(act.action, "open_website")
        self.assertIn(act.value, [None, ""])

    def test_youtube_play_something(self):
        res = self.ai.parse_command("open youtube and play something")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "youtube")
        self.assertEqual(act.action, "open_website")
        self.assertIn(act.value, [None, ""])

    def test_youtube_play_query(self):
        res = self.ai.parse_command("open youtube and play mr beast")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "youtube")
        self.assertEqual(act.action, "open_website")
        self.assertEqual(act.value.lower(), "mr beast")

    def test_browser_open(self):
        res = self.ai.parse_command("open my browser")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "browser")
        self.assertEqual(act.action, "open_app")

    def test_chrome_open(self):
        res = self.ai.parse_command("open chrome")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "chrome")
        self.assertEqual(act.action, "open_app")

    def test_discord_open(self):
        res = self.ai.parse_command("open discord")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "discord")
        self.assertEqual(act.action, "open_app")

    def test_steam_open(self):
        res = self.ai.parse_command("open steam")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "steam")
        self.assertEqual(act.action, "open_app")

    def test_notepad_open(self):
        res = self.ai.parse_command("open notepad")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "notepad")
        self.assertEqual(act.action, "open_app")

    def test_calculator_open(self):
        res = self.ai.parse_command("open calculator")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "calculator")
        self.assertEqual(act.action, "open_app")

    def test_vscode_open(self):
        res = self.ai.parse_command("open vs code")
        self.assertTrue(len(res.actions) >= 1)
        act = res.actions[0]
        self.assertEqual(act.domain, "pc_automation")
        self.assertEqual(act.device_or_target, "vscode")
        self.assertEqual(act.action, "open_app")


if __name__ == "__main__":
    unittest.main()
