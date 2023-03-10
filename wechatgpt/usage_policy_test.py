import unittest
from datetime import datetime

from .usage_policy import UsagePolicy, CommandFormatError


class UsagePolicyTest(unittest.TestCase):
    def test_chat_limit_clear(self):
        return_date = datetime(2023, 1, 1, 10, 10, 10)

        def current_date():
            return return_date

        up = UsagePolicy(["a"], user_chat_count_per_day={"b": 2}, current_date=current_date, token="c")
        up.on_chat("b")
        up.on_chat("b")
        self.assertTrue(up.reached_limit("b"))
        self.assertTrue(up.reached_limit("b"))
        return_date = datetime(2023, 1, 2, 0, 0, 0)
        self.assertFalse(up.reached_limit("b"))
        up.on_chat("b")
        up.on_chat("b")
        self.assertTrue(up.reached_limit("b"))

    def test_chat_limit(self):
        up = UsagePolicy(["a"], user_chat_count_per_day={"b": 2}, default_user_chat_count_per_day=3, token="c")
        up.on_chat("b")
        up.on_chat("b")
        self.assertTrue(up.reached_limit("b"))

        up.on_chat("c")
        up.on_chat("c")
        self.assertFalse(up.reached_limit("c"))
        up.on_chat("c")
        self.assertTrue(up.reached_limit("c"))

        self.assertFalse(up.handle_usage_change_command("a", "some normal msg"))
        self.assertFalse(up.handle_usage_change_command("b", "some normal msg"))

        self.assertRaises(Exception, lambda: up.handle_usage_change_command("b", "admin-command:c\nset_limit"))
        self.assertRaises(CommandFormatError, lambda: up.handle_usage_change_command("a", "admin-command:c\nset_limit"))

        self.assertTrue(up.handle_usage_change_command("a", "admin-command:c\nset_limit\nd,10"))
        self.assertEqual(up.user_chat_count_per_day["d"], 10)
