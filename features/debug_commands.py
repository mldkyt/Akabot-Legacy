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

from database import client
from features.chat_summary import normal_chat_summary, special_chat_summary
from utils.tzutil import get_now_for_server


class DebugCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    dev_commands_group = discord.SlashCommandGroup(name="dev_commands", description="Developer commands")

    @dev_commands_group.command(name="ping", description="Get ping to Discord API")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    @dev_commands_group.command(name="now", description="Get now for server")
    async def now(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Current time: {get_now_for_server(ctx.guild.id).isoformat()}", ephemeral=True)

    @dev_commands_group.command(name='test_chat_summary', description='Test Chat Summary')
    async def test_chat_summary(self, ctx: discord.ApplicationContext, mode: int):
        # 0: Normal
        # 1: Monthly
        # 2: Yearly

        channel = ctx.channel
        date = get_now_for_server(ctx.guild.id)
        guild = ctx.guild
        i = client['ChatSummary'].find_one({'ChannelID': str(channel.id), 'GuildID': str(guild.id)})

        if mode == 0:
            await ctx.respond("Running normal chat summary...", ephemeral=True)
            await normal_chat_summary(channel, date, guild, i)
        elif mode == 1:
            await ctx.respond("Running monthly chat summary...", ephemeral=True)
            await special_chat_summary(channel, date, guild, i, override_month=True)
        elif mode == 2:
            await ctx.respond("Running yearly chat summary", ephemeral=True)
            await special_chat_summary(channel, date, guild, i, override_year=True)
        else:
            await ctx.respond("Mode not found", ephemeral=True)
