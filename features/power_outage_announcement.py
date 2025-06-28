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

import os.path
import time

import discord
import sentry_sdk
from discord.ext import tasks

from utils.config import get_key
from utils.generic import pretty_time_delta, pretty_time


class PowerOutageAnnouncement(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.started = False

    @discord.Cog.listener()
    async def on_ready(self):
        try:
            if self.started:
                return
            self.started = True

            if not os.path.exists("data/current_time.txt"):
                self.save_current_time.start()
                return

            channel_id = get_key("PowerOutageAnnouncements_ChannelID", "0")
            with open("data/current_time.txt", "r") as f:
                current_time = float(f.read())
            with open("configs/power_outage_announcement_message.txt", "r") as f:
                power_outage_message = str(f.read())

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                self.save_current_time.start()
                return

            # format things like {pretty_time} and other things into the message
            power_outage_message = power_outage_message.replace("{pretty_time}",
                                                                await pretty_time_delta(time.time() - current_time,
                                                                                  server_id=0,
                                                                                  user_id=0))
            power_outage_message = power_outage_message.replace("{outage_time}", pretty_time(current_time))
            power_outage_message = power_outage_message.replace("{now_time}", pretty_time(time.time()))

            await channel.send(power_outage_message)
            self.save_current_time.start()
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @tasks.loop(minutes=1)
    async def save_current_time(self):
        with open("data/current_time.txt", "w") as f:
            f.write(str(time.time()))
