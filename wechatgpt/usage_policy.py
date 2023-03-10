from __future__ import annotations

import json
import re
import time
from datetime import datetime
from threading import Thread
from typing import Callable, Dict, List, Optional, Set, Union

from .logger import get_logger


class UserChatStat:
    def __init__(
        self,
        user: str,
        current_date: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.user = user
        self.chat_count = 0
        self.total_chat_count = 0
        self.last_chat_at: Optional[datetime] = None
        default_current_date = lambda: datetime.now()
        self.current_date = current_date or default_current_date

    def on_chat(self):
        self.chat_count += 1
        self.total_chat_count += 1
        self.last_chat_at = self.current_date()

    def under_limit(self, limit: int):
        return self.chat_count < limit

    def reset_stat(self):
        self.chat_count = 0
        self.last_chat_at = None


class CommandFormatError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class UsagePolicy:
    def __init__(
        self,
        admin_users: List[str],
        user_white_list: Optional[Set[str]] = None,
        user_chat_count_per_day: Optional[Dict[str, int]] = None,
        default_user_chat_count_per_day: int = 20,
        token: Optional[str] = None,
        current_date: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.admin_users = admin_users
        self.user_chat_stat: Dict[str, UserChatStat] = {}
        self.user_white_list = user_white_list or set()
        for user in admin_users:
            self.user_white_list.add(user)
        self.user_chat_count_per_day = user_chat_count_per_day or {}
        self.default_user_chat_count_per_day = default_user_chat_count_per_day
        self.token = token
        default_current_date = lambda: datetime.now()
        self.current_date = current_date or default_current_date
        self.saving_list_thread = Thread(target=self.save_config, daemon=True)
        self.saving_list_thread.start()

    def as_dict(self) -> dict:
        return {
            "admin_users": self.admin_users,
            "user_white_list": list(self.user_white_list),
            "user_chat_count_per_day": self.user_chat_count_per_day,
            "default_user_chat_count_per_day": self.default_user_chat_count_per_day,
        }

    def save_config(self):
        while True:
            time.sleep(10 * 60)
            config_file_path = "/app/usage-policy.json"
            try:
                with open(config_file_path, "w") as f:
                    f.write(json.dumps(self.as_dict(), ensure_ascii=False))
                print("updated usage policy config.")
            except Exception as e:
                import traceback

                print("save config error!")
                traceback.print_exc()

    def get_stat(self) -> dict:
        user_total_chat_count = [u.total_chat_count for u in self.user_chat_stat.values()]
        now = datetime.now()
        today = datetime(now.year, now.month, now.day)
        today_user_chat_count = [u.chat_count for u in self.user_chat_stat.values() if u.last_chat_at and u.last_chat_at >= today]
        return {
            "total_user_count": len(self.user_chat_stat),
            "total_chat_count": sum(user_total_chat_count),
            "max_user_chat_count": max(user_total_chat_count) if len(user_total_chat_count) else 0,
            "min_user_chat_count": min(user_total_chat_count) if len(user_total_chat_count) else 0,
            "avg_user_chat_count": sum(user_total_chat_count) / len(self.user_chat_stat) if len(user_total_chat_count) else 0,
            "today_chat_user_count": len(today_user_chat_count),
            "today_chat_count": sum(today_user_chat_count),
            "today_max_user_chat_count": max(today_user_chat_count) if len(today_user_chat_count) else 0,
            "today_min_user_chat_count": min(today_user_chat_count) if len(today_user_chat_count) else 0,
            "today_avg_user_chat_count": sum(today_user_chat_count) / len(today_user_chat_count) if len(today_user_chat_count) else 0,
        }

    def handle_usage_change_command(self, user: str, msg: str) -> Union[bool, str]:
        lines = [line.strip() for line in msg.split("\n") if line.strip()]
        if len(lines) > 0 and lines[0] == "user_command:get_msg_count":
            return str(self.user_chat_stat.get(user, UserChatStat(user)).chat_count)

        if lines[0] == f"admin-command:{self.token}":
            if user not in self.admin_users:
                get_logger().warn(f"found user {user} try to use admin commands! msg: {msg}")
                raise Exception("Not enough privilege!")
            if len(lines) != 3:
                raise CommandFormatError(f"Must be lines to set command and args, found {len(lines)} lines (should be 3)")
            cmd = lines[1]
            if cmd == "add_white_list":
                users = [u.strip() for u in lines[2].split(",") if u.strip()]
                for u in users:
                    self.add_white_list(u)
            elif cmd == "remove_white_list":
                users = [u.strip() for u in lines[2].split(",") if u.strip()]
                for u in users:
                    self.add_white_list(u)
            elif cmd == "set_limit":
                user_limit = [u.strip() for u in lines[2].split(",") if u.strip()]
                if len(user_limit) != 2 or not re.match(r"^[\d]+$", user_limit[1]):
                    raise CommandFormatError(f"Args for set limit must be `{{user_id}}, {{count}}`, found {lines[2]}")
                self.set_limit(user_limit[0], int(user_limit[1]))
            elif cmd == "set_token":
                token = lines[2].strip()
                if not token:
                    raise CommandFormatError(f"Args for set limit must be `{{user_id}}, {{count}}`, found {lines[2]}")
                self.token = token
            elif cmd == "get_config":
                return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)
            elif cmd == "get_stat":
                return json.dumps(self.get_stat(), ensure_ascii=False, indent=2)
            else:
                raise CommandFormatError("Unknown command: " + cmd)
            return True
        return False

    def add_white_list(self, user: str):
        get_logger().info(f"add user to white list: {user}")
        self.user_white_list.add(user)

    def remove_white_list(self, user: str):
        get_logger().info(f"remove user from white list: {user}")
        self.user_white_list.remove(user)

    def set_limit(self, user: str, limit: int):
        get_logger().info(f"set user chat count per day from {self.user_chat_count_per_day.get(user, None)} to {limit}")
        self.user_chat_count_per_day[user] = limit

    def on_chat(self, user: str):
        if user not in self.user_chat_stat:
            self.user_chat_stat[user] = UserChatStat(user, current_date=self.current_date)
        chat_stat = self.user_chat_stat[user]
        chat_stat.on_chat()

    def reached_limit(self, user: str) -> bool:
        if user not in self.user_chat_stat:
            return False
        if user in self.user_white_list:
            return False
        chat_stat = self.user_chat_stat[user]
        if chat_stat.last_chat_at and self.current_date().day != chat_stat.last_chat_at.day:
            chat_stat.reset_stat()
        if user in self.user_chat_count_per_day:
            return not chat_stat.under_limit(self.user_chat_count_per_day[user])
        else:
            return not chat_stat.under_limit(self.default_user_chat_count_per_day)
