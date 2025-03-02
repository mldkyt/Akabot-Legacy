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

import os

import discord

from utils.analytics import analytics

class Help(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    help_group = discord.SlashCommandGroup(name='help', description='Help commands')

    @help_group.command(name="anti_raid", description="Help with Anti Raid feature")
    @analytics("help anti_raid")
    async def anti_raid(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Anti_Raid", ephemeral=True)

    @help_group.command(name="automod_actions", description="Help with Auto Role feature")
    @analytics("help automod_actions")
    async def automod_actions(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Automod_Actions", ephemeral=True)

    @help_group.command(name="chat_revive", description="Help with Chat Revive feature")
    @analytics("help chat_revive")
    async def chat_revive(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Chat_Revive", ephemeral=True)

    @help_group.command(name="chat_streaks", description="Help with Chat Streaks feature")
    @analytics("help chat_streaks")
    async def chat_streaks(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Chat_Streaks", ephemeral=True)

    @help_group.command(name="chat_summary", description="Help with Chat Summary feature")
    @analytics("help chat_summary")
    async def chat_summary(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Chat_Summary", ephemeral=True)

    @help_group.command(name="giveaways", description="Help with Giveaways feature")
    @analytics("help giveaways")
    async def giveaways(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Giveaways", ephemeral=True)

    @help_group.command(name="leveling", description="Help with Leveling feature")
    @analytics("help leveling")
    async def leveling(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Leveling", ephemeral=True)

    @help_group.command(name="logging", description="Help with Logging feature")
    @analytics("help logging")
    async def logging(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Logging", ephemeral=True)

    @help_group.command(name="moderation", description="Help with Moderation feature")
    @analytics("help moderation")
    async def moderation(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Moderation", ephemeral=True)

    @help_group.command(name="reaction_roles", description="Help with Reaction Roles feature")
    @analytics("help reaction_roles")
    async def reaction_roles(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Reaction_Roles", ephemeral=True)

    @help_group.command(name="verification", description="Help with Verification feature")
    @analytics("help verification")
    async def verification(self, ctx: discord.ApplicationContext):
        await ctx.respond("Please read the documentation located at this link: https://wiki.mldchan.dev//index.php/Akabot#Verification", ephemeral=True)
