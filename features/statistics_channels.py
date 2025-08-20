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
import asyncio
import logging

import discord
from discord.ext import tasks, pages

from utils.denylist import akabot_logger
from utils.languages import get_translation_for_key_localized as _
from utils.statistic_channels import db_get_statistic_channels, db_set_statistic_channel, db_remove_statistic_channel, \
    db_get_all_statistic_channels


def format_text(guild: discord.Guild, text: str):
    text = text.replace("{members}", str(guild.member_count))
    text = text.replace("{members.bots}", str(len([x for x in guild.members if x.bot])))
    text = text.replace("{guild.name}", guild.name)
    text = text.replace("{guild.id}", str(guild.id))
    text = text.replace("{guild.owner}", guild.owner.display_name)
    text = text.replace("{guild.owner.id}", str(guild.owner.id))
    text = text.replace("{guild.owner.name}", guild.owner.name)

    return text


async def update_statistic_channels_for_guild(guild: discord.Guild):
    try:
        statistic_channels = db_get_statistic_channels(guild.id)

        for i in statistic_channels:
            channel = guild.get_channel(int(i['ChannelID']))
            if not channel:
                logging.warning('Channel %s not found, skipping', i['ChannelID'])
                continue

            formatted_name: str = i['StatisticText']
            formatted_name = format_text(guild, formatted_name)

            if formatted_name == channel.name:
                continue

            try:
                await channel.edit(name=formatted_name)
            except discord.Forbidden:
                pass
            except Exception as e:
                akabot_logger.exception("An error occured:")

    except Exception as e:
        akabot_logger.exception("An error occured:")


class StatisticChannels(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.update_statistic_channels.start()

    statistic_channels_grp = discord.SlashCommandGroup(name="statistic_channels",
                                                       description="Manage statistic channels")

    @statistic_channels_grp.command(name="set", description="Set statistic channel settings")
    async def set_statistic_channel_settings(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel,
                                             statistic_text: str):
        try:
            db_set_statistic_channel(ctx.guild.id, channel.id, statistic_text)
            await ctx.respond("Settings updated.", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(_(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @statistic_channels_grp.command(name="help", description="Formatting help")
    async def statistic_channel_help(self, ctx: discord.ApplicationContext):
        try:
            await ctx.respond(
                _(ctx.user.id, ctx.guild.id, "statistic_channels_help", append_tip=True, members=ctx.guild.member_count,
                bots=len([x for x in ctx.guild.members if x.bot]),
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                guild_owner=ctx.guild.owner.display_name,
                guild_owner_id=ctx.guild.owner.id,
                  guild_owner_name=ctx.guild.owner.name),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(_(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @statistic_channels_grp.command(name="list", description="List statistic channels")
    async def list_statistic_channels(self, ctx: discord.ApplicationContext):
        try:
            statistic_channels = db_get_statistic_channels(ctx.guild.id)

            if len(statistic_channels) == 0:
                await ctx.respond(_(ctx.user.id, ctx.guild.id, "statistic_channels_list_empty", append_tip=True),
                                  ephemeral=True)
                return

            pg = []

            for i in range(0, len(statistic_channels), 10):
                c = ""
                for j in statistic_channels[i:i + 10]:
                    c = c + _(ctx.user.id, ctx.guild.id, "statistic_channels_list_row",
                              channel=ctx.guild.get_channel(int(j['ChannelID'])).mention,
                        formatted=format_text(ctx.guild, j['StatisticText']),
                              template=j['StatisticText']) + "\n"

                pg.append(c)

            paginator = pages.Paginator(pages=pg)
            await paginator.respond(ctx.interaction, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(_(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @statistic_channels_grp.command(name="remove", description="Remove statistic channel")
    async def delete_statistic_channel(self, ctx: discord.ApplicationContext):
        try:
            db_remove_statistic_channel(ctx.guild.id, ctx.channel.id)
            await ctx.respond(_(ctx.user.id, ctx.guild.id, 'statistic_channel_remove'), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(_(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @tasks.loop(minutes=1)
    async def update_statistic_channels(self):
        try:
            tasks_to_run = []

            data = db_get_all_statistic_channels()

            for i in data:
                guild = self.bot.get_guild(int(i['GuildID']))
                if guild is None:
                    continue

                tasks_to_run.append(update_statistic_channels_for_guild(guild))

            await asyncio.gather(*tasks_to_run)
        except Exception as e:
            akabot_logger.exception("An error occured:")
