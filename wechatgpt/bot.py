import hashlib
import json
import math
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from .logger import get_logger


class ChatMessage:
    def __init__(self, role: str, content: str, at: int) -> None:
        self.role, self.content = role, content
        self.at = at

    def __str__(self) -> str:
        return json.dumps(
            {
                "role": self.role,
                "content": self.content,
                "at": datetime.utcfromtimestamp(self.at).strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=False,
        )

    def __repr__(self) -> str:
        return str(self)

    def as_gpt_msg(self) -> Dict:
        return {"role": self.role, "content": self.content}


class UserChats:
    def __init__(
        self,
        session_minutes: int = 30,
        initial_msgs: Optional[List[ChatMessage]] = None,
    ) -> None:
        self.session_minutes = session_minutes
        self.chats: Dict[str, List[ChatMessage]] = {}
        self.initial_msgs = initial_msgs or []
        self.chat_tokens: Dict[str, int] = {}
        self.last_clear_time = datetime.now()

    def _init_user_chats(self, user: str):
        if user not in self.chats:
            self.chats[user] = self.initial_msgs.copy()
            self.chat_tokens[user] = 0

    def try_clear_session_chats(self, clear_all: bool = False):
        if (datetime.now() - self.last_clear_time).total_seconds() / 60 < self.session_minutes:
            return
        self.last_clear_time = datetime.now()
        get_logger().info("start to clear session chats")
        cleared_count = 0
        for user, chats in self.chats.items():
            if not chats:
                continue
            now_secs = math.floor(time.mktime(datetime.now().timetuple()))
            last_message_session_timeout = (now_secs - chats[-1].at) / 60.0 > self.session_minutes
            if clear_all or last_message_session_timeout:
                get_logger().info(f"Session timed out for user {user}. Chats cleared (tokens_count={self.chat_tokens[user]}): {chats}")
                self.chats[user] = []
                self.chat_tokens[user] = 0
                cleared_count += 1
        get_logger().info(f"finisned to clear session chats, cleared {cleared_count} sessions")

    def clear_session(self, user: str):
        if user in self.chats:
            get_logger().info(f"finisned to clear session for user {user}. Chats cleared (tokens_count={self.chat_tokens[user]}): {self.chats[user]}")
            self.chats[user] = []
            self.chat_tokens[user] = 0

    def add_assistant_chat(self, user: str, content: str, total_tokens: int, at: Optional[int] = None):
        return self._add_chat(user, "assistant", content, total_tokens, at)

    def add_user_chat(self, user: str, content: str):
        return self._add_chat(user, "user", content)

    def _add_chat(
        self,
        user: str,
        role: str,
        content: str,
        total_tokens: Optional[int] = None,
        at: Optional[int] = None,
    ):
        self._init_user_chats(user)
        msgs = self.chats[user]
        self.chat_tokens[user] = total_tokens or self.chat_tokens[user]
        msg = ChatMessage(
            role=role,
            content=content,
            at=at or math.floor(time.mktime(datetime.now().timetuple())),
        )
        msgs.append(msg)
        get_logger().info(f"add chat for user {user}: {msg}")

    def to_gpt_chats(self, user: str) -> List[Dict]:
        self._init_user_chats(user)
        msgs = [m.as_gpt_msg() for m in self.chats[user]]
        return msgs


class Bot:
    def answer(self, user: str, question: str) -> str:
        raise NotImplementedError()


class ChatgptBot(Bot):
    def __init__(
        self,
        token: str,
        chats: UserChats,
        proxy: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        # get your token from: https://platform.openai.com/account/api-keys
        self.token = token
        self.url = "https://api.openai.com/v1/chat/completions"
        self.chats = chats
        self.proxy = proxy
        self.max_tokens = max_tokens
        self.token_exceeded_msg = "抱歉，这个话题我们已经聊了太多了。我没法再聊下去了。或许您可以总结一下前面的内容，然后我们再尝试往下聊！"
        self.system_error_msg = "抱歉，系统错误，请稍候再试！"

    def _user_id(self, user: str) -> str:
        md5 = hashlib.md5()
        md5.update(user.encode())
        return md5.hexdigest()

    def answer(self, user: str, question: str) -> str:
        self.chats.try_clear_session_chats()
        self.chats.add_user_chat(user, question)
        msgs = self.chats.to_gpt_chats(user)
        data = {"model": "gpt-3.5-turbo", "user": self._user_id(user), "messages": msgs}
        if self.max_tokens:
            data["max_tokens"] = self.max_tokens
        get_logger().info(f"send question for user {user} (hash: {data['user']}) to gpt: {question}")
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy is not None else None
        r = requests.post(
            self.url,
            json=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
            proxies=proxies,
        )
        if r.status_code != 200:
            response_text = r.text
            get_logger().error(f"Found error: status={r.status_code}, body={response_text}")
            if r.status_code == 400:
                try:
                    resp = json.loads(response_text)
                    if resp.get("error", {}).get("code", None) == "context_length_exceeded":
                        get_logger().info("token exceeds, will clear session and guide user to start another chat session.")
                        self.chats.clear_session(user)
                        return self.token_exceeded_msg
                except Exception:
                    get_logger().error("unknown error happened: ", exc_info=True)
                    return self.system_error_msg
            else:
                return self.system_error_msg

        try:
            resp = r.json()
            get_logger().info(f"got response from gpt: {json.dumps(resp, ensure_ascii=False)}")
            total_tokens = resp["usage"]["total_tokens"]
            message = resp["choices"][0]["message"]["content"]
            self.chats.add_assistant_chat(user, message, total_tokens)
            return message
        except:
            get_logger().error(f"Unable to parse response: status={r.status_code}, body={r.text}")
            return self.system_error_msg
