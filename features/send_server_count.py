#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 mldchan
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


import aiohttp
import discord
import sentry_sdk
from discord.ext import tasks

from utils.config import get_key

SEND_SECONDS = int(get_key("Send_Server_Count_Seconds", "0"))
SEND_MINUTES = int(get_key("Send_Server_Count_Minutes", "0"))
SEND_HOURS = int(get_key("Send_Server_Count_Hours", "0"))

SEND = get_key("Send_Server_Count_API", "false") == "true"
SEND_METHOD = get_key("Send_Server_Count_Method", "post")
SEND_URL = get_key("Send_Server_Count_URL", "http://localhost")

TOPGG_SEND = get_key("TopGG_Send", "false") == "true"
TOPGG_TOKEN = get_key("TopGG_Token", "None")
TOPGG_BOT_ID = get_key("TopGG_Bot_ID", "None")

if SEND_URL == "None":
    SEND_URL = None

if TOPGG_TOKEN == "None":
    TOPGG_TOKEN = None

if TOPGG_BOT_ID == "None":
    TOPGG_BOT_ID = None


class SendServerCount(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        if SEND:
            self.send_server_count.start()
        if TOPGG_SEND:
            self.send_topgg_server_count.start()

    @tasks.loop(seconds=SEND_SECONDS, minutes=SEND_MINUTES, hours=SEND_HOURS)
    async def send_server_count(self):
        try:
            async with aiohttp.ClientSession() as session:
                if SEND_METHOD == "get":
                    await session.get(SEND_URL, params={"count": len(self.bot.guilds)})
                elif SEND_METHOD == "post":
                    await session.post(SEND_URL, json={"count": len(self.bot.guilds)})
                elif SEND_METHOD == "put":
                    await session.put(SEND_URL, json={"count": len(self.bot.guilds)})
                else:
                    raise ValueError("Invalid method")
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @tasks.loop(seconds=SEND_SECONDS, minutes=SEND_MINUTES, hours=SEND_HOURS)
    async def send_topgg_server_count(self):
        headers = {
            "Authorization": f"Bearer {TOPGG_TOKEN}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"https://top.gg/api/bots/{TOPGG_BOT_ID}/stats", headers=headers,
                                   json={"server_count": len(self.bot.guilds)})
        except Exception as e:
            sentry_sdk.capture_exception(e)
