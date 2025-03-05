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

import json
import random

import discord
import sentry_sdk
from discord.ext import commands

from utils.analytics import analytics
from utils.settings import get_setting, set_setting


def pick_hug_gif():
    with open("configs/rp.json", "r") as f:
        data = json.load(f)
    return random.choice(data["hug_gifs"])


def pick_kiss_yaoi_gif():
    with open("configs/rp.json", "r") as f:
        data = json.load(f)
    return random.choice(data["kiss_yaoi_gifs"])


def pick_kiss_yuri_gif():
    with open("configs/rp.json", "r") as f:
        data = json.load(f)
    return random.choice(data["kiss_yuri_gifs"])


def pick_bite_gif():
    with open("configs/rp.json", "r") as f:
        data = json.load(f)
    return random.choice(data["bite_gifs"])


def get_footer_msg():
    footers = [
        "This feature is still in development",
        "Drop suggestions using /feedback suggest",
        "Drop gif suggestions in #akabot-suggestions in the support server",
        "Please be respectful to everyone in the server",
    ]

    return random.choice(footers)


def get_unbite_img():
    with open("configs/rp.json", "r") as f:
        data = json.load(f)
    return data["unbite_img"]


class RoleplayCommands(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    rp_admin_group = discord.SlashCommandGroup("rp_admin", "Admin roleplay commands")
    rp_group = discord.SlashCommandGroup("rp", "Roleplay commands")

    @rp_group.command(name="hug")
    @analytics("rp hug")
    async def hug(self, ctx, member: discord.Member):
        """Hug a member"""
        try:

            if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                return

            gif = pick_hug_gif()
            embed = discord.Embed(title=f"{ctx.author.display_name} hugs {member.display_name}!",
                                  footer=discord.EmbedFooter(text=get_footer_msg()))
            embed.set_image(url=gif)
            await ctx.respond(content=f"{ctx.author.mention} hugs {member.mention}!", embed=embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_group.command(name="kiss")
    @analytics("rp kiss")
    async def kiss(self, ctx, member: discord.Member):
        """Kiss a member"""
        try:

            if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                return

            gif = pick_kiss_yaoi_gif()
            embed = discord.Embed(title=f"{ctx.author.display_name} kisses {member.display_name}!",
                                  footer=discord.EmbedFooter(text=get_footer_msg()))
            embed.set_image(url=gif)
            await ctx.respond(content=f"{ctx.author.mention} kisses {member.mention}!", embed=embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_group.command(name="bite")
    @analytics("rp bite")
    async def bite(self, ctx, member: discord.Member):
        """Bite a member"""
        try:
            if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                return

            gif = pick_bite_gif()
            embed = discord.Embed(title=f"{ctx.author.display_name} bites {member.display_name}!",
                                  footer=discord.EmbedFooter(text=get_footer_msg()))
            embed.set_image(url=gif)
            await ctx.respond(content=f"{ctx.author.mention} bites {member.mention}!", embed=embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_group.command(name="unbite")
    @analytics("rp unbite")
    async def unbite(self, ctx, member: discord.Member):
        """Unbite a member"""
        try:
            if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                return

            embed = discord.Embed(title=f"{ctx.author.display_name} unbites {member.display_name}!",
                                  footer=discord.EmbedFooter(text=get_footer_msg()))
            embed.set_image(url=get_unbite_img())
            await ctx.respond(content=f"{ctx.author.mention} unbites {member.mention}!", embed=embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_admin_group.command(name="enabled")
    @analytics("rp_admin enabled")
    async def rp_enable(self, ctx, enable: bool):
        """Enable or disable roleplay commands"""
        try:
            set_setting(ctx.guild.id, "roleplay_enabled", str(enable).lower())
            await ctx.respond(content=f"Roleplay commands have been {'enabled' if enable else 'disabled'}",
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_admin_group.command(name="list")
    @analytics("rp_admin list")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @discord.guild_only()
    async def rp_list(self, ctx):
        """List all settings for roleplay"""
        try:
            rp_enabled = get_setting(ctx.guild.id, "roleplay_enabled", "false") == "true"
            embed = discord.Embed(title="Roleplay settings")
            embed.add_field(name="Enabled", value='Yes' if rp_enabled else 'No', inline=False)
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(content="Something went wrong", ephemeral=True)
