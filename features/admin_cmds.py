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
import os

import discord
import sentry_sdk

from utils.announcement_channels import db_get_all_announcement_channels
from utils.config import get_key
# Let's say that trl is the short form of get_translation_for_key_localized across the codebase
from utils.languages import get_translation_for_key_localized as trl
from database import get_client

ADMIN_GUILD = int(get_key("Admin_GuildID", "0"))
OWNER_ID = int(get_key("Admin_OwnerID", "0"))
ANNOUNCEMENT_CHANNEL = int(get_key("Admin_AnnouncementChannel", "0"))


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

            client = get_client()

            active_channels = await client['AnalyticsActiveChannels'].count_documents({'LastUseTime': {'$gt': datetime.datetime.now() - datetime.timedelta(days=7)}})
            active_users = await client['AnalyticsActiveUsers'].count_documents({'LastUseTime': {'$gt': datetime.datetime.now() - datetime.timedelta(days=7)}})
            active_akabot_users = await client['AnalyticsAkabotUsers'].count_documents({'LastBotUse': {'$gt': datetime.datetime.now() - datetime.timedelta(days=7)}})

            await client.client.close()

            await ctx.respond(
                (await trl(ctx.user.id, ctx.guild.id, "bot_status_message")).format(servers=str(servers),
                                                                            channels=str(channels),
                                                                            activechannel=str(active_channels),
                                                                            activeuser=str(active_users),
                                                                            akabotuser=str(active_akabot_users),
                                                                            users=str(members)), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "command_error_generic")).format(e), ephemeral=True)

    @admin_subcommand.command(name="create_announcement", description="List all announcement channels")
    async def create_announcement(self, ctx: discord.ApplicationContext, announcement_file: discord.Attachment,
                                  extra_attachment: discord.Attachment = None):
        try:
            await ctx.defer()

            if ANNOUNCEMENT_CHANNEL == 0:
                await ctx.respond(content=trl(ctx.user.id, ctx.guild.id, "announcement_not_set"), ephemeral=True)
                return

            if not announcement_file.filename.endswith(".md"):
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "announcement_file_not_md"), ephemeral=True)
                return

            await announcement_file.save("temp.md")
            await extra_attachment.save(extra_attachment.filename)

            with open("temp.md", "r") as f:
                announcement = f.read()

            if len(announcement) > 2000:
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "announcement_too_long"), ephemeral=True)
                return

            msg: discord.Message | None = await ctx.followup.send(content="Creating announcement...")
            if not msg:
                return

            first_channel = self.bot.get_channel(ANNOUNCEMENT_CHANNEL)
            if not first_channel:
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "announcement_channel_not_found"), ephemeral=True)
                return

            await first_channel.send(announcement, file=discord.File(extra_attachment.filename))

            await msg.edit(content=await trl(ctx.user.id, ctx.guild.id, "announcement_sent_sending_to_subscribed"))
            channels = await db_get_all_announcement_channels()
            i = 0
            for channel in channels:
                i += 1

                if i % 10 == 0:
                    await msg.edit(
                        content=(await trl(ctx.user.id, ctx.guild.id,
                                    "announcement_sent_sending_to_subscribed_progress")).format(
                            progress=str(i), count=str(len(channels))))

                try:
                    channel = self.bot.get_channel(channel[1])
                    if not channel:
                        continue

                    await channel.send(announcement, file=discord.File(extra_attachment.filename))
                except discord.Forbidden:
                    continue

            await msg.edit(content=await trl(ctx.user.id, ctx.guild.id, "announcement_sent"))

            os.remove("temp.md")
            os.remove(extra_attachment.filename)
            os.remove(announcement_file.filename)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "command_error_generic")).format(e), ephemeral=True)
