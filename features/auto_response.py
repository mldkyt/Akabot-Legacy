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

import discord
import sentry_sdk
from bson import ObjectId
from discord.ext import commands as discord_commands_ext
from discord.ext import pages as dc_pages

from database import client
from utils.languages import get_translation_for_key_localized as trl


class AutoResponse(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        super().__init__()
        self.bot = bot

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try:
            # Check if it's the bot
            if msg.author.bot:
                return

            # Find all created settings
            data = client['AutoResponse'].find({'GuildID': str(msg.guild.id)})
            for i in data:
                # If it contains the message
                if i['TriggerText'] in msg.content:
                    # Reply to it
                    await msg.reply(i['ReplyText'])
        except Exception as e:
            sentry_sdk.capture_exception(e)
