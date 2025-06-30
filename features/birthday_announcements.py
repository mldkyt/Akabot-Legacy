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

import discord
import sentry_sdk
from discord.ext import tasks, commands

from database import client
from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.languages import get_translation_for_key_localized as trl
from utils.module_toggling import is_module_enabled
from utils.per_user_settings import get_per_user_setting
from utils.per_server_settings import set_setting, get_setting


class BirthdayAnnouncements(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        super().__init__()

    birthday_announcements_group = discord.SlashCommandGroup(name="birthday_announcements",
                                                             description="Birthday Announcements commands")

    @discord.Cog.listener()
    async def on_ready(self):
        self.birthday_announcements.start()

    @tasks.loop(seconds=60)
    async def birthday_announcements(self):
        await self.handle_birthday_announcements()

    async def handle_birthday_announcements(self):
        # Check for birthdays
        now = datetime.datetime.now()
        if now.hour != 12 or now.minute != 0:
            return

        birthdays = client['UserBirthday'].find({'Birth.Month': now.month, 'Birth.Day': now.day}).to_list()
        for birthday in birthdays:
            try:
                member = self.bot.get_user(int(birthday["UserID"]))
                if member is None:
                    continue
                # Test DM
                try:
                    if get_per_user_setting(member.id, 'birthday_send_dm', True):
                        await member.send(trl(member.id, 0, 'birthday_dm'))
                except discord.Forbidden:
                    pass

                # Broadcast to Discord servers where this was allowed
                for guild_id in birthday['AllowedServers']:
                    guild = self.bot.get_guild(int(guild_id))
                    if guild is None:
                        continue

                    if not get_setting(guild.id, "module_birthday_announcements_enabled", True):
                        continue

                    channel_id = get_setting(int(guild_id), 'birthday_announcements_channel', '0')
                    channel = guild.get_channel(int(channel_id))
                    if channel is None:
                        continue

                    bd_msg = str(get_setting(guild_id, "birthday_announcements_message",
                                             trl(0, guild_id, "birthday_server")))

                    age = now.year - int(birthday["Birth"]["Year"])

                    bd_msg = bd_msg.replace("{member}", member.mention)
                    bd_msg = bd_msg.replace("{member_name}", member.display_name)
                    bd_msg = bd_msg.replace("{member_display_name}", member.display_name)
                    bd_msg = bd_msg.replace("{member_user_name}", member.name)
                    bd_msg = bd_msg.replace("{guild}", guild.name)
                    bd_msg = bd_msg.replace("{guild_id}", str(guild.id))
                    bd_msg = bd_msg.replace("{member_id}", str(member.id))
                    bd_msg = bd_msg.replace("{age}", str(age))
                    bd_msg = bd_msg.replace("{day}", str(now.day))
                    bd_msg = bd_msg.replace("{month}", str(now.month))
                    bd_msg = bd_msg.replace("{year}", str(now.year))
                    bd_msg = bd_msg.replace("{birth_year}", str(birthday["Birth"]["Year"]))

                    if len(bd_msg.strip()) == 0:
                        continue

                    await channel.send(bd_msg)
            except Exception as e:
                sentry_sdk.capture_exception(e)

    @birthday_announcements_group.command(name="channel", description="Set the channel for birthday announcements")
    @is_module_enabled("birthday_announcements")
    @discord.default_permissions(manage_guild=True)
    @discord.option(name="channel", description="The channel to send birthday announcements in")
    @commands.has_permissions(manage_guild=True)
    @analytics("birthday_announcements channel")
    @blocklist()
    async def set_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        set_setting(ctx.guild.id, "birthday_announcements_channel", str(channel.id))
        await ctx.respond(
            trl(ctx.user.id, ctx.guild.id, "birthday_announcements_channel_set", append_tip=True).format(
                channel=channel.mention),
            ephemeral=True)

    @birthday_announcements_group.command(name="message", description="Customize the birthday announcement message")
    @is_module_enabled("birthday_announcements")
    @discord.option(name="message", description="The message to send on birthdays")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @analytics("birthday_announcements message")
    @blocklist()
    async def birthday_announcements_message(self, ctx: discord.ApplicationContext, message: str):
        set_setting(ctx.guild.id, "birthday_announcements_message", message)
        await ctx.respond("Birthday announcement message set", ephemeral=True)
