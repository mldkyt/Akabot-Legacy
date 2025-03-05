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
from bson import ObjectId
from discord.ext import commands as discord_commands_ext
from discord.ext import pages as dc_pages

from database import client
from utils.languages import get_translation_for_key_localized as trl


class AutoResponse(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        super().__init__()
        self.bot = bot

    auto_response_group = discord.SlashCommandGroup(name="auto_response", description="Auto response settings")

    @auto_response_group.command(name="add", description="New auto response setting")
    @discord.option(name="trigger", description="The trigger of the message. Can be any text. Case insensitive.")
    @discord.option(name="reply", description="What to reply with. This exact text will be sent")
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord_commands_ext.bot_has_permissions(read_message_history=True, add_reactions=True)
    @discord.default_permissions(manage_messages=True)
    async def add_auto_response(self, ctx: discord.ApplicationContext, trigger: str, reply: str):
        try:
            client['AutoResponse'].insert_one(
                {'GuildID': str(ctx.guild.id), 'TriggerText': trigger, 'ReplyText': reply})

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "auto_response_add_success").format(trigger=trigger, reply=reply),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @auto_response_group.command(name="list", description="List auto response settings")
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord_commands_ext.bot_has_permissions(read_message_history=True, add_reactions=True)
    @discord.default_permissions(manage_messages=True)
    async def list_auto_responses(self, ctx: discord.ApplicationContext):
        try:
            # Define a message variable
            message_groups = []
            current_group = 0
            current_group_msg = ""

            # List

            all_settings = client['AutoResponse'].find({'GuildID': str(ctx.guild.id)}).to_list()
            if len(all_settings) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_list_empty"), ephemeral=True)
                return

            for i in all_settings:
                # Format: **{id}**: {trigger} -> {reply}
                # current_group_msg += f"**ID: `{i[0]}`**: Trigger: `{i[2]}` -> Will say `{i[3]}`\n"
                current_group_msg += trl(ctx.user.id, ctx.guild.id, "auto_response_list_row").format(id=str(i['_id']),
                                                                                                     trigger=i[
                                                                                                         'TriggerText'],
                                                                                                     reply=i[
                                                                                                         'ReplyText'])
                current_group += 1

                # Split message group
                if current_group == 5:
                    message_groups.append(current_group)
                    current_group = 0
                    current_group_msg = ""

            # Add last group
            if current_group != 0:
                message_groups.append(current_group_msg)

            # Reply with a paginator
            paginator = dc_pages.Paginator(message_groups)
            await paginator.respond(ctx.interaction, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @auto_response_group.command(name="edit_trigger", description="Change trigger for a setting")
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord_commands_ext.bot_has_permissions(read_message_history=True, add_reactions=True)
    @discord.default_permissions(manage_messages=True)
    async def edit_trigger_auto_response(self, ctx: discord.ApplicationContext, id: str, new_trigger: str):
        try:
            if not ObjectId.is_valid(id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_setting_not_found"),
                                  ephemeral=True)
                return

            result = client['AutoResponse'].update_one({'_id': ObjectId(id), 'GuildID': str(ctx.guild.id)},
                                                       {'$set': {'TriggerText': new_trigger}})

            if result.matched_count == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_setting_not_found"),
                                  ephemeral=True)
                return

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_keyword_updated"), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @auto_response_group.command(name="delete", description="Delete an auto response setting")
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord_commands_ext.bot_has_permissions(read_message_history=True, add_reactions=True)
    @discord.default_permissions(manage_messages=True)
    async def delete_auto_response(self, ctx: discord.ApplicationContext, id: str):
        try:
            if not ObjectId.is_valid(id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_setting_not_found"),
                                  ephemeral=True)
                return

            result = client['AutoResponse'].delete_one({'_id': ObjectId(id), 'GuildID': str(ctx.guild.id)})

            if result.deleted_count == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_setting_not_found"),
                                  ephemeral=True)
                return

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_delete_success"), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @auto_response_group.command(name="edit_response", description="Change response for a setting")
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord_commands_ext.bot_has_permissions(read_message_history=True, add_reactions=True)
    @discord.default_permissions(manage_messages=True)
    async def edit_response_auto_response(self, ctx: discord.ApplicationContext, id: str, new_response: str):
        try:
            if not ObjectId.is_valid(id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_setting_not_found"),
                                  ephemeral=True)
                return

            result = client['AutoResponse'].update_one({'_id': ObjectId(id), 'GuildID': str(ctx.guild.id)},
                                                       {'$set': {'ReplyText': new_response}})

            if result.matched_count == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_setting_not_found"),
                                  ephemeral=True)
                return

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "auto_response_text_updated"), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try:
            # Check if it's the bot
            if msg.author.bot:
                return

            # Find all created settings
            data = client['AutoResponse'].find({'GuildID': str(msg.guild.id)})
            for i in data:
                # If it contains the message
                if i['TriggerText'] in msg.content:
                    # Reply to it
                    await msg.reply(i['ReplyText'])
        except Exception as e:
            sentry_sdk.capture_exception(e)
