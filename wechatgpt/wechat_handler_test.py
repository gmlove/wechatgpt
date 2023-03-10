import os
import unittest
from datetime import datetime

import requests

from wechatgpt.bot import ChatgptBot, UserChats

from .usage_policy import UsagePolicy
from .wechat_handler import Request, WechatMsg, WechatMsgHandler


class WechatHandlerTest(unittest.TestCase):
    def test_parse_wechat_msg(self):
        msg = WechatMsg.from_raw_xml(
            """
        <xml>
            <ToUserName><![CDATA[wechat-account-1]]></ToUserName>
            <FromUserName><![CDATA[wechat-account-2]]></FromUserName>
            <CreateTime>1515830851</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[。。]]></Content>
            <MsgId>6510443931858529216</MsgId>
        </xml>"""
        )
        self.assertEqual(msg.to_user_name, "wechat-account-1")
        self.assertEqual(msg.from_user_name, "wechat-account-2")
        self.assertEqual(msg.content.text, "。。")  # type: ignore

    def test_wechat_msg_to_xml_str(self):
        create_time = datetime.now()
        msg = WechatMsg("test_to_user", "test_from_user", "。。我是谁", create_time=create_time)
        parsed_msg = WechatMsg.from_raw_xml(msg.xml_str())
        self.assertEqual(msg.to_user_name, "test_to_user")
        self.assertEqual(msg.from_user_name, "test_from_user")
        self.assertEqual(msg.content.text, "。。我是谁")  # type: ignore

    @unittest.skip("integration test")
    def test_wechat_handler(self):
        request = Request(
            "POST",
            "/wechat",
            """
        <xml>
            <ToUserName><![CDATA[wechat-account-1]]></ToUserName>
            <FromUserName><![CDATA[wechat-account-2]]></FromUserName>
            <CreateTime>1515830851</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[。。]]></Content>
            <MsgId>6510443931858529216</MsgId>
        </xml>""",
        )

        msg_handler = self.create_wechat_msg_handler()

        self.assertTrue(msg_handler.accept(request))

        response = msg_handler.handle(request)

        self.assertDictEqual(response.headers, {"Content-Type": "text/xml"})
        self.assertEqual(response.status_code, 200)
        response_msg = WechatMsg.from_raw_xml(response.body)
        self.assertEqual(response_msg.to_user_name, "wechat-account-2")
        self.assertEqual(response_msg.from_user_name, "wechat-account-1")
        self.assertIsNotNone(response_msg.content)

    def create_wechat_msg_handler(self):
        return WechatMsgHandler(ChatgptBot(os.environ["token"], UserChats()), UsagePolicy([]), "")

    @unittest.skip("integration test")
    def test_chatgpt_chat(self):
        resp = requests.post(
            "https://localhost:10812/wechat",
            data="""
        <xml>
            <ToUserName><![CDATA[wechat-account-1]]></ToUserName>
            <FromUserName><![CDATA[wechat-account-2]]></FromUserName>
            <CreateTime>1515830851</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[hi]]></Content>
            <MsgId>6510443931858529216</MsgId>
        </xml>""",
        )
        print(resp.content)
