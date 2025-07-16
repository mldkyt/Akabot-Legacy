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

import datetime
import logging

import discord

from database import client
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl

ADMIN_GUILD = int(get_key("Admin_GuildID", "0"))
OWNER_ID = int(get_key("Admin_OwnerID", "0"))
ANNOUNCEMENT_CHANNEL = int(get_key("Admin_AnnouncementChannel", "0"))

akabot_logger = logging.getLogger("akabot")

class AdminCommands(discord.Cog):

    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    admin_subcommand = discord.SlashCommandGroup(name="admin", description="Manage the bot", guild_ids=[ADMIN_GUILD])

    @admin_subcommand.command(name="server_count", description="How many servers is the bot in?")
    async def admin_servercount(self, ctx: discord.ApplicationContext):
        try:
            servers = len(self.bot.guilds)
            channels = len([channel for channel in self.bot.get_all_channels()])
            members = len(set([member for member in self.bot.get_all_members()]))
            
            active_channels = client['AnalyticsActiveChannels'].count_documents({'LastUseTime': {'$gt': datetime.datetime.now() - datetime.timedelta(days=7)}})
            active_users = client['AnalyticsActiveUsers'].count_documents({'LastUseTime': {'$gt': datetime.datetime.now() - datetime.timedelta(days=7)}})
            active_akabot_users = client['AnalyticsAkabotUsers'].count_documents({'LastBotUse': {'$gt': datetime.datetime.now() - datetime.timedelta(days=7)}})

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "bot_status_message").format(servers=str(servers),
                                                                            channels=str(channels),
                                                                            activechannel=str(active_channels),
                                                                            activeuser=str(active_users),
                                                                            akabotuser=str(active_akabot_users),
                                                                            users=str(members)), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured in /server_count:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic").format(e), ephemeral=True)