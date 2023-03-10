from __future__ import annotations
import hashlib

import random
import time
from typing import Optional, Dict
from urllib import parse

from wechatgpt.usage_policy import CommandFormatError, UsagePolicy
from wechatgpt.wechat_msg import TextMessageContent, WechatMsg

from .bot import ChatgptBot
from .logger import get_logger


class Response:
    def __init__(self, headers: Optional[Dict[str, str]], status_code: int, body: str):
        self.headers = headers or {"Content-Type": "text/xml"}
        self.status_code = status_code
        self.body = body

    def __str__(self):
        return "{headers=%s, status_code=%s, body=%s}" % (
            self.headers,
            self.status_code,
            self.body,
        )


class Request:
    def __init__(self, method, full_path, body):
        self.method = method
        self.full_path = full_path
        self.body = body
        req = parse.urlparse(full_path)
        query = req.query.strip()
        query_components = dict(qc.split("=") for qc in query.split("&")) if query not in ["", ""] else {}
        query_components = dict([(k, parse.unquote(str(v))) for k, v in query_components.items()])
        self.path = req.path
        self.query = query_components

    def __str__(self):
        return "{method=%s, full_path=%s, body=%s}" % (
            self.method,
            self.full_path,
            self.body,
        )


class WechatMsgHandler:
    def __init__(self, bot: ChatgptBot, usage_policy: UsagePolicy, admin_email: str):
        self.bot = bot
        self.usage_policy = usage_policy
        self.admin_email = admin_email
        self.chating_users: Dict[str, bool] = {}
        self.chating_user_asks: Dict[str, str] = {}
        self.chating_user_answers: Dict[str, WechatMsg] = {}
        self.wait_timeout_msg_creator = lambda to_user, from_user: WechatMsg(
            to_user,
            from_user,
            "这个问题有点难，助手还在思考中...\n\n回复“1”查看回复。",
            msg_type="text",
        )
        self.ask_too_fast_msg_creator = lambda to_user, from_user: WechatMsg(
            to_user,
            from_user,
            "抱歉，您的回复太快啦，助手还在思考前一个问题呢！\n\n回复“1”查看前一个问题的回复。",
            msg_type="text",
        )
        self.system_error_msg_creator = lambda to_user, from_user: WechatMsg(
            to_user,
            from_user,
            "抱歉，系统错误，请稍候再试！",
            msg_type="text",
        )
        self.rate_limit_msg_creator = lambda to_user, from_user: WechatMsg(
            to_user,
            from_user,
            f"抱歉，您今日的聊天次数已达上限，请明日再来！\n\n如希望解除限制，请发送您的ID({to_user})至邮箱 {self.admin_email} ，并附上一个充分的理由。",
            msg_type="text",
        )
        self.command_handle_success_msg_creator = lambda to_user, from_user, msg: WechatMsg(
            to_user,
            from_user,
            f"操作成功！\n\n{msg}" if msg else "操作成功！",
            msg_type="text",
        )
        self.command_handle_failed_msg_creator = lambda to_user, from_user, msg: WechatMsg(
            to_user,
            from_user,
            f"操作失败，命令格式错误：" + msg,
            msg_type="text",
        )

    def xml_response(self, req: WechatMsg, response_text: str) -> str:
        response_msg = WechatMsg(req.from_user_name, req.to_user_name, response_text)
        return response_msg.xml_str()

    def accept(self, request):
        return request.path == "/wechat" and request.method == "POST"

    def handle(self, request) -> Response:
        headers = {"Content-Type": "text/xml"}
        status_code = 200
        try:
            request_msg = WechatMsg.from_raw_xml(request.body)
        except Exception as e:
            get_logger().info("unable to parse message, will ignore it.")
            return Response(headers, status_code, "")

        if not isinstance(request_msg.content, TextMessageContent):
            get_logger().info("found unknown message, will ignore it.")
            return Response(headers, status_code, "")

        try:
            msg = self.usage_policy.handle_usage_change_command(request_msg.from_user_name, request_msg.content.text)
            if isinstance(msg, str) or msg is True:
                return Response(
                    headers,
                    status_code,
                    self.command_handle_success_msg_creator(
                        request_msg.from_user_name, request_msg.to_user_name, msg if isinstance(msg, str) else ""
                    ).xml_str(),
                )
        except CommandFormatError as e:
            get_logger().info("command format error found: " + e.args[0])
            return Response(
                headers,
                status_code,
                self.command_handle_failed_msg_creator(request_msg.from_user_name, request_msg.to_user_name, e.args[0]).xml_str(),
            )

        if self.usage_policy.reached_limit(request_msg.from_user_name):
            return Response(headers, status_code, self.rate_limit_msg_creator(request_msg.from_user_name, request_msg.to_user_name).xml_str())

        # if there is a waiting message
        if request_msg.from_user_name in self.chating_users:
            # if user is asking some other things, just reply that it's too fast.
            if request_msg.content.text != "1" and request_msg.content.text != self.chating_user_asks.get(request_msg.from_user_name, None):
                return Response(headers, status_code, self.ask_too_fast_msg_creator(request_msg.from_user_name, request_msg.to_user_name).xml_str())

            # wechat server send 3 times for response or user typed '1' to get a reply
            # wait a moment for the answer, if still no, reply a following hint.
            wait_count = 0
            while request_msg.from_user_name in self.chating_users:
                if wait_count >= 3:
                    get_logger().info("already waited for 3s, will return a pre-defined message.")
                    return Response(
                        headers, status_code, self.wait_timeout_msg_creator(request_msg.from_user_name, request_msg.to_user_name).xml_str()
                    )
                time.sleep(1)
                wait_count += 1
            return Response(headers, status_code, self.chating_user_answers[request_msg.from_user_name].xml_str())

        # if user would like to get the recent reply
        if request_msg.content.text == "1" and request_msg.from_user_name in self.chating_user_answers:
            # This is to resolve a issue with wechat server. If we keep return the same correct msg, wechat will recognize it as an error.
            # Dont know why right now. We just return a correct message randomly here.
            if random.random() < 0.5:
                return Response(headers, status_code, self.wait_timeout_msg_creator(request_msg.from_user_name, request_msg.to_user_name).xml_str())
            msg = self.chating_user_answers[request_msg.from_user_name]
            msg = msg.copy()
            return Response(headers, status_code, msg.xml_str())

        # normal flow
        self.chating_users[request_msg.from_user_name] = True
        self.chating_user_asks[request_msg.from_user_name] = request_msg.content.text
        try:
            msg_type, msg_content = self.answer_for_question(request_msg.from_user_name, request_msg.content.text)  # type: ignore
            response_msg = WechatMsg(
                request_msg.from_user_name,
                request_msg.to_user_name,
                msg_content,
                msg_type=msg_type,
            )
            self.chating_user_answers[request_msg.from_user_name] = response_msg
            return Response(headers, status_code, response_msg.xml_str())
        except Exception as e:
            get_logger().error("Error found: " + str(e), exc_info=True)
            return Response(headers, status_code, self.system_error_msg_creator(request_msg.from_user_name, request_msg.to_user_name).xml_str())
        finally:
            self.usage_policy.on_chat(request_msg.from_user_name)
            del self.chating_users[request_msg.from_user_name]

    def answer_for_question(self, user: str, question: str):
        answer = self.bot.answer(user, question)
        if isinstance(answer, tuple):
            return answer[0], answer
        return "text", answer.strip()


class WechatEchoMsgHandler:
    def __init__(self):
        pass

    def accept(self, request):
        return request.path == "/wechat" and request.method == "GET"

    def handle(self, request):
        headers = {"Content-Type": "text/xml"}
        status_code = 200
        return Response(headers, status_code, request.query["echostr"])


def check_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    data = "".join(sorted([token, timestamp, nonce]))
    expected_sig = hashlib.sha1(data.encode()).hexdigest()
    return expected_sig == signature
