#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 lunya.pet
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import discord
import requests
import sentry_sdk
from discord.ext import tasks

from utils.config import get_key


class Heartbeat(discord.Cog):
    def __init__(self) -> None:
        self.interval_cnt = int(get_key("Heartbeat_Interval", '60'))
        super().__init__()

        if get_key("Heartbeat_Enabled", "false") == "true":
            self.heartbeat_task.start()

    @tasks.loop(seconds=1)
    async def heartbeat_task(self):
        try:
            self.interval_cnt += 1
            if self.interval_cnt >= int(get_key("Heartbeat_Interval", '60')):
                self.interval_cnt = 0
                # Send heartbeat
                method = get_key("Heartbeat_HTTPMethod", 'post').lower()
                url = get_key('Heartbeat_URL', 'https://example.com')
                if method == "get":
                    requests.get(url)
                elif method == "post":
                    requests.post(url)
                elif method == "put":
                    requests.put(url)
                elif method == "delete":
                    requests.delete(url)
        except Exception as e:
            sentry_sdk.capture_exception(e)
