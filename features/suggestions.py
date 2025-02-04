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
from discord.ext import commands

from database import client
from utils.languages import get_translation_for_key_localized as trl
from utils.settings import get_setting, set_setting

class Suggestions(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return

            if client['SuggestionChannels'].count_documents({'ChannelID': str(message.channel.id)}) > 0:
                emojis = get_setting(message.guild.id, 'suggestion_emoji', '👍👎')
                if emojis == '👍👎':
                    await message.add_reaction('👍')
                    await message.add_reaction('👎')
                elif emojis == '✅❌':
                    await message.add_reaction('✅')
                    await message.add_reaction('❌')

                if get_setting(message.guild.id, "suggestion_reminder_enabled", "false") == "true":
                    to_send = get_setting(message.guild.id, "suggestion_reminder_message", "")
                    sent = await message.reply(to_send)
                    await sent.delete(delay=5)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    suggestions_group = discord.SlashCommandGroup(name='suggestions', description='Suggestion commands')

    @suggestions_group.command(name='add_channel', description='Add a suggestion channel')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_add_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            if client['SuggestionChannels'].count_documents({'ChannelID': str(ctx.guild.id)}) == 0:
                client['SuggestionChannels'].insert_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(channel.id)})
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'suggestions_channel_added', append_tip=True).format(
                    channel=channel.mention), ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'suggestions_channel_already_exists'), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='remove_channel', description='Remove a suggestion channel')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            if client['SuggestionChannels'].count_documents({'ChannelID': str(ctx.guild.id)}) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "suggestions_channel_not_found"), ephemeral=True)
            else:
                client['SuggestionChannels'].delete_one({'ChannelID': str(ctx.guild.id)})
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "suggestions_channel_removed", append_tip=True).format(
                    channel=channel.mention), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='emoji', description='Choose emoji')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @discord.option(name='emoji', description='The emoji to use', choices=['👎👍', '✅❌'])
    async def cmd_choose_emoji(self, ctx: discord.ApplicationContext, emoji: str):
        try:
            set_setting(ctx.guild.id, 'suggestion_emoji', emoji)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "suggestions_emoji_set").format(emoji=emoji),
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='message_reminder', description="Message reminder for people posting suggestions")
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_message_reminder(self, ctx: discord.ApplicationContext, enabled: bool, message: str):
        try:
            if len(message) < 1:
                await ctx.respond("Invalid message input.", ephemeral=True)
            set_setting(ctx.guild.id, 'suggestion_reminder_enabled', str(enabled).lower())
            set_setting(ctx.guild.id, 'suggestion_reminder_message', message)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, 'suggestions_message_reminder_set', append_tip=True).format(
                    enabled=enabled, message=message), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
