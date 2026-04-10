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

import logging

import aiohttp
import discord
from discord.ext import commands

from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.per_server_settings import get_setting, set_setting

akabot_logger = logging.getLogger("akabot")

async def get_le_image(type: str) -> tuple[str, str | None]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://nekos.best/api/v2/{type}") as req:
            a = await req.json()
            return a['results'][0]['url'], a['results'][0]['source_url'] if 'source_url' in a['results'][0] else None

class InteractBack(discord.ui.View):
    def __init__(self, action: str, u_1: discord.User | discord.Member, u_2: discord.User | discord.Member):
        super().__init__(timeout=5*60, disable_on_timeout=True)

        self.action = action
        self.users = [u_1, u_2]
        self.interact_back_button = discord.ui.Button(label=f"{action.title()} Back")
        self.interact_back_button.callback = self.interact_back
        self.add_item(self.interact_back_button)

    async def interact_back(self, interaction: discord.Interaction):
        if interaction.user != self.users[1]:
            await interaction.respond(f"{self.action} back isn't available for other people", ephemeral=True)
            return

        img, src = await get_le_image(self.action)

        embed = discord.Embed(title=self.action.title(), description=f"**{self.users[1].display_name}** {self.action}s **{self.users[0].display_name}** back!", color=discord.Color.nitro_pink())
        embed.set_image(url=img)
        if src is not None:
            embed.set_footer(text=src)

        await interaction.respond(content=f"{self.users[1].mention} {self.action}s {self.users[0].mention} back!", embed=embed)

class RoleplayCommands(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    rp_admin_group = discord.SlashCommandGroup("rp_admin", "Admin roleplay commands")
    rp_group = discord.SlashCommandGroup("rp", "Roleplay commands",
        integration_types=[discord.IntegrationType.guild_install, discord.IntegrationType.user_install])

    @rp_group.command(name="hug")
    @analytics("rp hug")
    @blocklist()
    async def hug(self, ctx, member: discord.Member):
        """Hug a member"""
        try:
            if ctx.guild is not None:
                if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                    await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                    return

            gif, source = await get_le_image("hug")
            embed = discord.Embed(title="Hug", description=f"**{ctx.author.display_name}** hugs **{member.display_name}**!", color=discord.Color.nitro_pink())
            embed.set_image(url=gif)
            if source is not None:
                embed.set_footer(text=source)

            await ctx.respond(content=f"{ctx.author.mention} hugs {member.mention}!", embed=embed, view=InteractBack("hug", ctx.user, member))
        except Exception as e:
            akabot_logger.exception("Error: ")
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_group.command(name="kiss")
    @analytics("rp kiss")
    @blocklist()
    async def kiss(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Kiss a member"""
        try:
            if ctx.guild is not None:
                if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                    await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                    return

            gif, source = await get_le_image("kiss")
            embed = discord.Embed(title="Kiss", description=f"**{ctx.author.display_name}** kisses **{member.display_name}**!", color=discord.Color.nitro_pink())
            embed.set_image(url=gif)
            if source is not None:
                embed.set_footer(text=source)

            await ctx.respond(content=f"{ctx.author.mention} kisses {member.mention}!", embed=embed, view=InteractBack("kiss", ctx.user, member))
        except Exception as e:
            akabot_logger.exception("Error: ")
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_group.command(name="bite")
    @analytics("rp bite")
    @blocklist()
    async def bite(self, ctx: discord.ApplicationContext, member: discord.Member):
        """Bite a member"""
        try:
            if ctx.guild is not None:
                if get_setting(ctx.guild.id, "roleplay_enabled", "true") == "false":
                    await ctx.respond(content="Roleplay commands are disabled for this server", ephemeral=True)
                    return

            gif, source = await get_le_image("bite")
            embed = discord.Embed(title="Bite", description=f"{ctx.author.display_name} bites {member.display_name}!",
                                  color=discord.Color.nitro_pink())
            embed.set_image(url=gif)
            if source is not None:
                embed.set_footer(text=source)

            await ctx.respond(content=f"{ctx.author.mention} bites {member.mention}!", embed=embed, view=InteractBack("bite", ctx.user, member))
        except Exception as e:
            akabot_logger.exception("Error: ")
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_admin_group.command(name="enabled")
    @analytics("rp_admin enabled")
    @commands.has_permissions(manage_guild=True)
    @blocklist()
    async def rp_enable(self, ctx, enable: bool):
        """Enable or disable roleplay commands"""
        try:
            set_setting(ctx.guild.id, "roleplay_enabled", str(enable).lower())
            await ctx.respond(content=f"Roleplay commands have been {'enabled' if enable else 'disabled'}",
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("Error: ")
            await ctx.respond(content="Something went wrong", ephemeral=True)

    @rp_admin_group.command(name="list")
    @analytics("rp_admin list")
    @blocklist()
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
            akabot_logger.exception("Error: ")
            await ctx.respond(content="Something went wrong", ephemeral=True)
