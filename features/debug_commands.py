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

from database import get_client
from features.chat_summary import normal_chat_summary, special_chat_summary
from utils.config import get_key
from utils.tzutil import get_now_for_server

BLOCKLIST_WORDS = [i.strip() for i in get_key("BLOCKLIST_WORDS", "", required=False).split(";") if len(i.strip()) > 0]
BLOCKLIST_SERVERS = [i.strip() for i in get_key("BLOCKLIST_SERVERS", "", required=False).split(";") if len(i.strip()) > 0]
BLOCKLIST_USERS = [i.strip() for i in get_key("BLOCKLIST_USERS", "", required=False).split(";") if len(i.strip()) > 0]

PERM_BLOCKLIST_WORDS = [i.strip() for i in get_key("PERMANENT_BLOCKLIST_WORDS", "", required=False).split(";") if len(i.strip()) > 0]
PERM_BLOCKLIST_SERVERS = [i.strip() for i in get_key("PERMANENT_BLOCKLIST_SERVERS", "", required=False).split(";") if len(i.strip()) > 0]
PERM_BLOCKLIST_USERS = [i.strip() for i in get_key("PERMANENT_BLOCKLIST_USERS", "", required=False).split(";") if len(i.strip()) > 0]

class DebugCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    dev_commands_group = discord.SlashCommandGroup(name="dev_commands", description="Developer commands")

    @dev_commands_group.command(name="ping", description="Get ping to Discord API")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    @dev_commands_group.command(name="now", description="Get now for server")
    async def now(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Current time: {(await get_now_for_server(ctx.guild.id)).isoformat()}", ephemeral=True)

    @dev_commands_group.command(name='test_chat_summary', description='Test Chat Summary')
    async def test_chat_summary(self, ctx: discord.ApplicationContext, mode: int):
        # 0: Normal
        # 1: Monthly
        # 2: Yearly

        channel = ctx.channel
        date = await get_now_for_server(ctx.guild.id)
        guild = ctx.guild
        client = get_client()

        i = await client['ChatSummary'].find_one({'ChannelID': str(channel.id), 'GuildID': str(guild.id)})

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

    @dev_commands_group.command(name='get_blocklist_settings', description='Get Blocklist Settings')
    async def get_blocklist_settings(self, ctx: discord.ApplicationContext):

        message = (f'# Blocklist\n'
                   f'BLOCKLIST_WORDS: {";".join(BLOCKLIST_WORDS)}\n'
                   f'BLOCKLIST_SERVERS: {";".join(BLOCKLIST_SERVERS)}\n'
                   f'BLOCKLIST_USERS: {";".join(BLOCKLIST_USERS)}\n'
                   f'\n'
                   f'PERM_BLOCKLIST_WORDS: {";".join(PERM_BLOCKLIST_WORDS)}\n'
                   f'PERM_BLOCKLIST_USERS: {";".join(PERM_BLOCKLIST_USERS)}\n'
                   f'PERM_BLOCKLIST_SERVERS: {";".join(PERM_BLOCKLIST_SERVERS)}\n'
                   f'\n'
                   f'-# Akabot 1.2.1')

        await ctx.respond(message, ephemeral=True)
