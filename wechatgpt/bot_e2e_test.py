import os
import unittest
from .bot import ChatgptBot, UserChats


class ChatgptBotTest(unittest.TestCase):
    @unittest.skip("integration test")
    def test(self):
        bot = ChatgptBot(os.environ["chat_gpt_token"], UserChats())
        bot.answer("user-1", "你好啊")
        bot.answer("user-1", "我是一本书")
        bot.answer("user-2", "我今天不太高兴")
        bot.answer("user-1", "复述一下我刚刚说过的话")
        bot.answer("user-2", "复述一下我刚刚说过的话")
