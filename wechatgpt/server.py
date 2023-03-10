import sys
import traceback
import uuid
import logging
import os

from flask import Flask, make_response
from flask import request as flask_request
from flask import Request as FlaskRequest
from . import logger as commonLogger

from .wechat_handler import Request, Response, WechatEchoMsgHandler, WechatMsgHandler, UsagePolicy
from .bot import ChatgptBot, UserChats


class RequestFormatter(logging.Formatter):
    def format(self, record):
        record.url = flask_request.path
        record.request_id = flask_request.request_id  # type: ignore
        record.remote_addr = flask_request.remote_addr
        return super(RequestFormatter, self).format(record)


class LoggingHelpFlaskRequest(FlaskRequest):
    def __init__(self, environ, populate_request=True, shallow=False):
        super(LoggingHelpFlaskRequest, self).__init__(environ, populate_request, shallow)
        self.request_id = str(uuid.uuid4())


Flask.request_class = LoggingHelpFlaskRequest

app = Flask("wechatgpt")
logger = app.logger
commonLogger.set_logger(logger)


bot = ChatgptBot(os.environ["chat_gpt_token"], UserChats(), os.environ["http_proxy"])
up = UsagePolicy(
    os.environ["admin_user_ids"].split(","), user_white_list=set(os.environ["white_list_user_ids"].split(",")), token=os.environ["token"]
)
admin_email = os.environ["admin_email"]
wechat_msg_handler = WechatMsgHandler(bot, up, admin_email)
wechat_echo_handler = WechatEchoMsgHandler()


@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    request = Request(
        flask_request.method,
        flask_request.full_path,
        flask_request.stream.read().decode("utf8"),
    )
    logger.info("request received: %s", request)
    try:
        if flask_request.method == "POST":
            response = wechat_msg_handler.handle(request)
        else:
            response = wechat_echo_handler.handle(request)
    except Exception as e:
        traceback.print_exc()
        response = Response(None, 500, "")
    res = make_response(response.body, response.status_code)
    for k, v in response.headers.items():
        res.headers[k] = v
    logger.info("request handled: %s", response)
    return res


def _set_logger(flaskapp):
    del flaskapp.logger.handlers[:]
    handler = logging.StreamHandler(sys.stdout)
    if flaskapp.config.get("DEBUG"):
        handler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)
    handler.setFormatter(
        RequestFormatter(
            "[%(asctime)s][%(processName)s:%(threadName)s][%(levelname)s][%(remote_addr)s][%(request_id)s][%(url)s][%(module)s.%(funcName)s:%(lineno)d]: %(message)s"
        )
    )
    app.logger.addHandler(handler)


_set_logger(app)
