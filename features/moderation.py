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
from discord.ext import commands as commands_ext

from database import client
from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.config import get_key
from utils.generic import pretty_time_delta
from utils.languages import get_translation_for_key_localized as trl, get_language
from utils.logging_util import log_into_logs
from utils.per_user_settings import get_per_user_setting
from utils.per_server_settings import get_setting, set_setting
from utils.tips import append_tip_to_message
from utils.tzutil import get_now_for_server
from utils.warning import add_warning, db_get_warning_actions, db_add_warning_action, db_get_warnings, \
    db_remove_warning_action, db_remove_warning


def is_a_moderator(ctx: discord.ApplicationContext):
    roles = client['ModeratorRoles'].find({'GuildID': str(ctx.guild.id)})
    for role in roles:
        if int(role['RoleID']) in [role.id for role in ctx.user.roles]:
            return True
    return False


class UnbanView(discord.ui.View):
    def __init__(self, guild: discord.Guild, user: discord.User, reason: str):
        super().__init__(timeout=60)
        self.user = user
        self.guild = guild
        self.reason = reason

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.guild.unban(self.user, reason=self.reason)
        await interaction.respond(
            trl(interaction.user.id, self.guild.id, "moderation_unban_response", append_tip=True).format(
                mention=self.user.mention, reason=self.reason), ephemeral=True)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()
        await interaction.edit(view=self)


class Moderation(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    moderation_subcommand = discord.SlashCommandGroup(name='moderation', description='Moderation commands')

    @discord.slash_command(name='kick', description='Kick a user from the server')
    @commands_ext.guild_only()
    @discord.default_permissions(kick_members=True)
    @commands_ext.bot_has_permissions(kick_members=True)
    @discord.option(name='user', description='The user to kick', type=discord.Member)
    @discord.option(name='reason', description='The reason for kicking', type=str)
    @analytics("kick")
    @blocklist()
    async def kick_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            if user.id == self.bot.user.id:  # Check if the user is the bot
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_kick_error_self_bot"), ephemeral=True)
                return

            if user.id == ctx.user.id:  # Check if the user is the author
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_kick_error_self_user"), ephemeral=True)
                return

            if user.top_role >= ctx.user.top_role:  # Check if the user has a higher role
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_kick_error_insufficient_role"),
                                  ephemeral=True)
                return

            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.defer(ephemeral=ephemerality == "true")

            try:
                await user.send(
                    trl(0, ctx.guild.id, "moderation_kick_dm").format(guild=ctx.guild.name, reason=reason,
                                                                      moderator=ctx.user.display_name))
            except Exception as e:
                sentry_sdk.capture_exception(e, scope="kick_user_dm")  # TO HANDLE LATER
                pass

            await user.kick(reason=reason)

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_kick_response", append_tip=True).format(mention=user.mention,
                                                                                                   reason=reason))

            log_embed = discord.Embed(title="User Kicked",
                                      description=f"{user.mention} has been kicked by {ctx.user.mention} for {reason}")
            log_embed.add_field(name="Kicked User", value=user.mention)
            log_embed.add_field(name="Kicked By", value=ctx.user.mention)
            log_embed.add_field(name="Kicked Reason", value=reason)
            log_embed.add_field(name="Kicked Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @discord.slash_command(name='ban', description='Ban a user from the server')
    @commands_ext.guild_only()
    @discord.default_permissions(ban_members=True)
    @commands_ext.bot_has_permissions(ban_members=True)
    @discord.option(name='user', description='The user to ban')
    @discord.option(name='reason', description='The reason for banning', type=str)
    @discord.option(name='send_dm', description='Send a DM to the user', type=bool)
    @analytics("ban")
    @blocklist()
    async def ban_user(self, ctx: discord.ApplicationContext, user: discord.User, reason: str):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            if user.id == self.bot.user.id:  # Check if the user is the bot
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_ban_error_self_bot"), ephemeral=True)
                return

            if user.id == ctx.user.id:  # Check if the user is the author
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_ban_error_self_user"), ephemeral=True)
                return

            member = ctx.guild.get_member(user.id)

            if member is not None and member.top_role >= ctx.user.top_role:  # Check if the user has a higher role
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_ban_error_insufficient_role"),
                                  ephemeral=True)
                return

            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.defer(ephemeral=ephemerality == "true")

            try:
                await user.send(
                    trl(ctx.user.id, ctx.guild.id, "moderation_ban_dm").format(guild=ctx.guild.name, reason=reason,
                                                                               moderator=ctx.user.display_name))
            except Exception as e:
                sentry_sdk.capture_exception(e, scope="ban_user_dm")
                pass

            await ctx.guild.ban(user, reason=reason, delete_message_seconds=604800)

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_ban_response", append_tip=True).format(mention=user.mention,
                                                                                                  reason=reason))

            log_embed = discord.Embed(title="User Banned",
                                      description=f"{user.mention} has been banned by {ctx.user.mention} for {reason}")
            log_embed.add_field(name="Banned User", value=user.mention)
            log_embed.add_field(name="Banned By", value=ctx.user.mention)
            log_embed.add_field(name="Banned Reason", value=reason)
            log_embed.add_field(name="Banned Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @discord.slash_command(name='unban', description='Unban a user from the server')
    @commands_ext.guild_only()
    @discord.default_permissions(ban_members=True)
    @commands_ext.bot_has_permissions(ban_members=True)
    @discord.option(name='userid', description='The user ID to unban', required=False)
    @discord.option(name='username', description='The username to unban', required=False)
    @analytics("unban")
    @blocklist()
    async def unban_user(self, ctx: discord.ApplicationContext, reason: str, userid: str = "", username: str = ""):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            await ctx.defer(ephemeral=True)
            # Fetch the banned member

            async for member in ctx.guild.bans():
                if userid != "" and userid == str(member.user.id):
                    await ctx.respond(
                        trl(ctx.user.id, ctx.guild.id, "moderation_unban_ask", append_tip=True).format(
                            mention=member.user.mention, reason=reason), ephemeral=True, view=UnbanView(ctx.guild, member.user, reason))
                    break

                if username != "" and username in member.user.name:
                    await ctx.respond(
                        trl(ctx.user.id, ctx.guild.id, "moderation_unban_ask", append_tip=True).format(
                            mention=member.user.mention, reason=reason), ephemeral=True, view=UnbanView(ctx.guild, member.user, reason))
                    break
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_unban_fail", append_tip=True),
                                  ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @discord.slash_command(name='timeout',
                           description='Time out a user from the server. If a user has a timeout, this will change '
                                       'the timeout.')
    @commands_ext.guild_only()
    @discord.default_permissions(kick_members=True)
    @commands_ext.bot_has_permissions(kick_members=True)
    @discord.option(name='user', description='The user to time out', type=discord.Member)
    @discord.option(name='reason', description='The reason for timing out', type=str)
    @discord.option(name='send_dm', description='Send a DM to the user', type=bool)
    @discord.option(name='days', description='The number of days to time out', type=int)
    @discord.option(name='hours', description='The number of hours to time out', type=int)
    @discord.option(name='minutes', description='The number of minutes to time out', type=int)
    @analytics("timeout")
    @blocklist()
    async def timeout_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str, days: int,
                           hours: int = 0, minutes: int = 0):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            if user.id == self.bot.user.id:  # Check if the user is the bot
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_timeout_error_self_bot"), ephemeral=True)
                return

            if user.id == ctx.user.id:  # Check if the user is the author
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_timeout_error_self_user"), ephemeral=True)
                return

            member = ctx.guild.get_member(user.id)
            if member is None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_timeout_error_member_not_found"),
                                  ephemeral=True)

            if user.top_role >= ctx.user.top_role:  # Check if the user has a higher role
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_timeout_error_insufficient_role"),
                                  ephemeral=True)
                return

            total_seconds = days * 86400 + hours * 3600 + minutes * 60
            if total_seconds > 2419200:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_timeout_error_max_duration"),
                                  ephemeral=True)
                return

            dm_has_updated = False

            if user.timed_out:
                await user.remove_timeout(reason=trl(0, ctx.guild.id, "moderation_timeout_reason_changing"))
                dm_has_updated = True

            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.defer(ephemeral=ephemerality == "true")

            if dm_has_updated:
                try:
                    await user.send(trl(0, ctx.guild.id, "moderation_timeout_dm_changing")
                                    .format(guild=ctx.guild.name, time=pretty_time_delta(total_seconds, user_id=user.id,
                                                                                         server_id=ctx.guild.id),
                                            moderator=ctx.user.display_name, reason=reason))
                except Exception as e:
                    sentry_sdk.capture_exception(e, scope="timeout_user_dm")
                    pass
            else:
                try:
                    await user.send(
                        trl(0, ctx.guild.id, "moderation_timeout_dm").format(guild=ctx.guild.name, reason=reason,
                                                                             moderator=ctx.user.display_name))
                except Exception as e:
                    sentry_sdk.capture_exception(e, scope="timeout_user_dm")
                    pass

            await user.timeout_for(datetime.timedelta(seconds=total_seconds), reason=reason)

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_timeout_response", append_tip=True).format(
                    mention=user.mention, reason=reason))

            log_embed = discord.Embed(title="User Timed Out",
                                      description=f"{user.mention} has been timed out by {ctx.user.mention} for {reason}")
            log_embed.add_field(name="Timed Out User", value=user.mention)
            log_embed.add_field(name="Timed Out By", value=ctx.user.mention)
            log_embed.add_field(name="Timed Out Reason", value=reason)
            log_embed.add_field(name="Timed Out Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @discord.slash_command(name='remove_timeout', description='Remove a timeout from a user on the server')
    @commands_ext.guild_only()
    @discord.default_permissions(kick_members=True)
    @commands_ext.bot_has_permissions(kick_members=True)
    @discord.option(name='user', description='The user to remove the timeout from', type=discord.Member)
    @discord.option(name='reason', description='The reason for removing', type=str)
    @discord.option(name='send_dm', description='Send a DM to the user', type=bool)
    @analytics("remove_timeout")
    @blocklist()
    async def remove_timeout_user(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            if user.id == self.bot.user.id:  # Check if the user is the bot
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_remove_timeout_error_self_bot"),
                                  ephemeral=True)
                return

            if user.id == ctx.user.id:  # Check if the user is the author
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_remove_timeout_error_self_user"),
                                  ephemeral=True)
                return

            if user.top_role >= ctx.user.top_role:  # Check if the user has a higher role
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_remove_timeout_error_insufficient_role"),
                                  ephemeral=True)
                return

            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.defer(ephemeral=ephemerality == "true")

            try:
                await user.send(
                    trl(ctx.user.id, ctx.guild.id, "moderation_remove_timeout_dm")
                    .format(guild=ctx.guild.name, reason=reason, moderator=ctx.user.display_name))
            except discord.Forbidden:
                pass

            await user.remove_timeout(reason=reason)

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_remove_timeout_response", append_tip=True).format(
                    mention=user.mention,
                    reason=reason))

            log_embed = discord.Embed(title="User Timeout Removed",
                                      description=f"{user.mention} has had their timeout removed by {ctx.user.mention} for {reason}")
            log_embed.add_field(name="Timeout Removed User", value=user.mention)
            log_embed.add_field(name="Timeout Removed By", value=ctx.user.mention)
            log_embed.add_field(name="Timeout Removed Reason", value=reason)
            log_embed.add_field(name="Timeout Removed Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @discord.slash_command(name='purge', description='Purge messages from a channel')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_messages=True)
    @commands_ext.bot_has_permissions(manage_messages=True)
    @discord.option(name='amount', description='The number of messages to purge')
    @discord.option(name='include_user', description='Include messages from this user')
    @discord.option(name='exclude_user', description='Exclude messages from this user')
    @analytics("purge")
    @blocklist()
    async def purge_messages(self, ctx: discord.ApplicationContext, amount: int, include_user: discord.User = None,
                             exclude_user: discord.User = None):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.defer(ephemeral=ephemerality == "true")
            if amount > int(get_key("Moderation_MaxPurge", "1000")):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_purge_max_messages").format(amount),
                                  ephemeral=True)
                return

            messages = []
            async for message in ctx.channel.history(limit=amount):
                if include_user and message.author != include_user:
                    continue
                if exclude_user and message.author == exclude_user:
                    continue
                if (datetime.datetime.now(datetime.timezone.utc) - message.created_at).total_seconds() >= 1209600:
                    continue
                messages.append(message)

            chunks = [messages[i:i + 100] for i in range(0, len(messages), 100)]
            for chunk in chunks:
                await ctx.channel.delete_messages(chunk)

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_purge_response", append_tip=True).format(
                    messages=str(len(messages))),
                ephemeral=True)

            log_embed = discord.Embed(title="Messages Purged",
                                      description=f"{ctx.user.mention} has purged {len(messages)} messages from {ctx.channel.mention}")
            log_embed.add_field(name="Purged Messages", value=str(len(messages)))
            log_embed.add_field(name="Purged By", value=ctx.user.mention)
            log_embed.add_field(name="Purged Channel", value=ctx.channel.mention)
            log_embed.add_field(name="Purged Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    warning_group = discord.SlashCommandGroup(name='warn', description='Warning commands')

    @warning_group.command(name='add', description='Add a warning to a user')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_messages=True)
    @discord.option(name='user', description='The user to warn', type=discord.Member)
    @discord.option(name='reason', description='The reason for warning', type=str)
    @analytics("warn add")
    @blocklist()
    async def add_warning(self, ctx: discord.ApplicationContext, user: discord.Member, reason: str):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            warning_id = await add_warning(user, ctx.guild, reason)
            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "warn_add_response", append_tip=True).format(mention=user.mention,
                                                                                            reason=reason,
                                                                                            id=str(warning_id)),
                ephemeral=ephemerality == "true")

            log_embed = discord.Embed(title="Warning Added",
                                      description=f"{user.mention} has been warned by {ctx.user.mention} for {reason}")
            log_embed.add_field(name="Warned User", value=user.mention)
            log_embed.add_field(name="Warned By", value=ctx.user.mention)
            log_embed.add_field(name="Warned Reason", value=reason)
            log_embed.add_field(name="Warned Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @warning_group.command(name='remove', description='Remove a warning from a user')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_messages=True)
    @discord.option(name='user', description='The user to remove the warning from', type=discord.Member)
    @discord.option(name='id', description='The ID of the warning', type=str)
    @analytics("warn remove")
    @blocklist()
    async def remove_warning(self, ctx: discord.ApplicationContext, user: discord.Member, warning_id: str):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            # check: warning exists
            warnings = db_get_warnings(ctx.guild.id, user.id)
            if not warnings:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "warn_list_no_warnings"), ephemeral=True)
                return

            if warning_id not in [str(warning['_id']) for warning in warnings]:
                await ctx.respond(
                    trl(ctx.user.id, ctx.guild.id, "warn_remove_error_warning_not_found").format(id=warning_id),
                    ephemeral=True)
                return

            db_remove_warning(ctx.guild.id, warning_id)
            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "warn_remove_response", append_tip=True).format(id=warning_id,
                                                                                               user=user.mention),
                ephemeral=ephemerality == "true")

            log_embed = discord.Embed(title="Warning Removed",
                                      description=f"{user.mention} has had warning {warning_id} removed by {ctx.user.mention}")
            log_embed.add_field(name="Warning Removed User", value=user.mention)
            log_embed.add_field(name="Warning Removed By", value=ctx.user.mention)
            log_embed.add_field(name="Warning Removed ID", value=str(warning_id))
            log_embed.add_field(name="Warning Removed Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @warning_group.command(name='list', description='List all warnings for a user')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_messages=True)
    @discord.option(name='user', description='The user to list the warnings for', type=discord.Member)
    @analytics("warn list")
    @blocklist()
    async def list_warnings(self, ctx: discord.ApplicationContext, user: discord.Member):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_not_moderator"), ephemeral=True)
                return

            warnings = db_get_warnings(ctx.guild.id, user.id)
            if not warnings:
                await ctx.respond(f'{user.mention} has no warnings.', ephemeral=True)
                return

            warning_str = trl(ctx.user.id, ctx.guild.id, "warn_list_title").format(user=user.mention)
            for warning in warnings:
                warning_str += trl(ctx.user.id, ctx.guild.id, "warn_list_line").format(id=str(warning['_id']),
                                                                                       reason=warning['Reason'],
                                                                                       date=warning['Timestamp'])

            if get_per_user_setting(ctx.user.id, 'tips_enabled', 'true') == 'true':
                language = get_language(ctx.guild.id, ctx.user.id)
                warning_str = append_tip_to_message(ctx.guild.id, ctx.user.id, warning_str, language)
            await ctx.respond(warning_str, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @warning_group.command(name='message', description='Set the message to be sent to a user when they are warned')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name='enable', description='Enable or disable the warning message', type=bool)
    @discord.option(name='message', description='The message to send to the user.', type=str)
    @analytics("warn message")
    @blocklist()
    async def set_warning_message(self, ctx: discord.ApplicationContext, enable: bool, message: str):
        try:
            # Get old
            old_send_warning_message = get_setting(ctx.guild.id, 'send_warning_message', 'true')
            old_warning_message = get_setting(ctx.guild.id, 'warning_message',
                                              'You have been warned in {guild} for {reason}.')

            # Create logging embed
            log_embed = discord.Embed(
                title=trl(0, ctx.guild.id, "warn_set_message_log_title"),
                color=discord.Color.blue()
            )

            if old_send_warning_message != str(enable).lower():
                log_embed.add_field(name=trl(0, ctx.guild.id, "logging_send_warning_message"),
                                    value=f'{old_send_warning_message} -> {str(enable).lower()}')

            if old_warning_message != message:
                log_embed.add_field(name=trl(0, ctx.guild.id, "logging_message"),
                                    value=f'{old_warning_message} -> {message}')

            # Log the change
            await log_into_logs(ctx.guild, log_embed)

            # Set settings
            set_setting(ctx.guild.id, 'send_warning_message', str(enable).lower())
            set_setting(ctx.guild.id, 'warning_message', message)

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "warn_set_message_response", append_tip=True).format(message=message),
                ephemeral=True)

            log_embed = discord.Embed(title="Warning Message Set",
                                      description=f"{ctx.user.mention} has set the warning message to {message}")
            log_embed.add_field(name="Warning Message", value=message)
            log_embed.add_field(name="Warning Message Enabled", value=str(enable).lower())
            log_embed.add_field(name="Warning Message Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    warning_actions_group = discord.SlashCommandGroup(name='warn_actions', description='Warning action commands')

    @warning_actions_group.command(name='add',
                                   description='Add an action to be taken on a user with a certain number of warnings')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_messages=True)
    @commands_ext.has_permissions(manage_messages=True)
    @discord.option(name='warnings', description='The number of warnings to trigger the action', type=int)
    @discord.option(name='action', description='The action to take', type=str,
                    choices=['kick', 'ban', 'timeout 12h', 'timeout 1d', 'timeout 7d', 'timeout 28d'])
    @analytics("warn_actions add")
    @blocklist()
    async def add_warning_action(self, ctx: discord.ApplicationContext, warnings: int, action: str):
        try:
            db_add_warning_action(ctx.guild.id, action, warnings)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "warn_actions_add_response", append_tip=True).format(action=action,
                                                                                                    warnings=warnings),
                ephemeral=True)

            log_embed = discord.Embed(title="Warning Action Added",
                                      description=f"{ctx.user.mention} has added a warning action to {action} for {warnings} warnings")
            log_embed.add_field(name="Warning Action", value=action)
            log_embed.add_field(name="Warning Action Warnings", value=str(warnings))
            log_embed.add_field(name="Warning Action Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @warning_actions_group.command(name='list',
                                   description='List all actions to be taken on a user with a certain number of '
                                               'warnings')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_messages=True)
    @commands_ext.has_permissions(manage_messages=True)
    @analytics("warn_actions list")
    @blocklist()
    async def list_warning_actions(self, ctx: discord.ApplicationContext):
        try:
            actions = db_get_warning_actions(ctx.guild.id)
            if not actions:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "warn_actions_list_empty"), ephemeral=True)
                return

            action_str = trl(ctx.user.id, ctx.guild.id, "warn_actions_list_title")
            for action in actions:
                action_str += trl(ctx.user.id, ctx.guild.id, "warn_actions_list_line").format(id=action[0],
                                                                                              action=action[1],
                                                                                              warnings=action[2])

            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")

            if get_per_user_setting(ctx.user.id, 'tips_enabled', 'true') == 'true':
                language = get_language(ctx.guild.id, ctx.user.id)
                action_str = append_tip_to_message(ctx.guild.id, ctx.user.id, action_str, language)
            await ctx.respond(action_str, ephemeral=ephemerality == "true")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @warning_actions_group.command(name='remove',
                                   description='Remove an action to be taken on a user with a certain number of '
                                               'warnings')
    @commands_ext.guild_only()
    @discord.option(name='id', description='The ID of the action', type=str)
    @analytics("warn_actions remove")
    @blocklist()
    async def remove_warning_action(self, ctx: discord.ApplicationContext, warning_action_id: str):
        try:
            if not is_a_moderator(ctx):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_no_moderator_role"),
                                  ephemeral=True)
                return

            actions = db_get_warning_actions(ctx.guild.id)
            if not actions:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "warn_actions_list_empty"), ephemeral=True)
                return

            if warning_action_id not in [action[0] for action in actions]:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "warn_actions_doesnt_exist"), ephemeral=True)
                return

            db_remove_warning_action(warning_action_id)
            ephemerality = get_setting(ctx.guild.id, "moderation_ephemeral", "true")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "warn_actions_remove_response", append_tip=True),
                              ephemeral=ephemerality == "true")

            log_embed = discord.Embed(title="Warning Action Removed",
                                      description=f"{ctx.user.mention} has removed a warning action with ID {warning_action_id}")
            log_embed.add_field(name="Warning Action ID", value=str(warning_action_id))
            log_embed.add_field(name="Warning Action Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @moderation_subcommand.command(name="ephemeral", description="Toggle the ephemeral status of a message")
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    async def toggle_ephemeral(self, ctx: discord.ApplicationContext, ephemeral: bool):
        try:
            set_setting(ctx.guild.id, "moderation_ephemeral", str(ephemeral).lower())
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_ephemeral_on", append_tip=True)
                if ephemeral else trl(ctx.user.id, ctx.guild.id, "moderation_ephemeral_off", append_tip=True),
                ephemeral=True)

            log_embed = discord.Embed(title="Ephemeral Toggled",
                                      description=f"{ctx.user.mention} has toggled the ephemeral status to {ephemeral}")
            log_embed.add_field(name="Ephemeral Status", value=str(ephemeral))
            log_embed.add_field(name="Ephemeral Time", value=get_now_for_server(ctx.guild.id).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @moderation_subcommand.command(name='add_moderator_role', description='Add a moderator role to the server')
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    async def add_moderator_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        try:
            if client['ModeratorRoles'].count_documents({'GuildID': str(ctx.guild.id), 'RoleID': str(role.id)}) > 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_moderator_role_already_exists").format(
                    role=role.mention), ephemeral=True)
                return

            client['ModeratorRoles'].insert_one({'GuildID': str(ctx.guild.id), 'RoleID': str(role.id)})

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "moderation_add_moderator_role_response").format(role=role.mention),
                ephemeral=True)

            log_embed = discord.Embed(title="Moderator Role Added",
                                      description=f"{ctx.user.mention} has added the moderator role {role.mention}")
            log_embed.add_field(name="Moderator Role", value=role.mention)

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @moderation_subcommand.command(name='remove_moderator_role', description='Remove a moderator role from the server')
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    async def remove_moderator_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        try:
            if client['ModeratorRoles'].delete_one(
                    {'GuildID': str(ctx.guild.id), 'RoleID': str(role.id)}).deleted_count > 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_remove_moderator_role_response").format(
                    role=role.mention), ephemeral=True)
            else:
                await ctx.respond(
                    trl(ctx.user.id, ctx.guild.id, "moderation_moderator_role_doesnt_exist").format(role=role.mention),
                    ephemeral=True)

            log_embed = discord.Embed(title="Moderator Role Removed",
                                      description=f"{ctx.user.mention} has removed the moderator role {role.mention}")
            log_embed.add_field(name="Moderator Role", value=role.mention)

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @moderation_subcommand.command(name='list_moderator_roles', description='List all moderator roles on the server')
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    async def list_moderator_roles(self, ctx: discord.ApplicationContext):
        try:
            roles = client['ModeratorRoles'].find({'GuildID': str(ctx.guild.id)})

            if not roles:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "moderation_no_moderator_roles"), ephemeral=True)
                return

            message = trl(ctx.user.id, ctx.guild.id, "moderation_moderator_roles_title")

            role_mentions = [trl(ctx.user.id, ctx.guild.id, "moderation_moderator_roles_line").format(
                role=ctx.guild.get_role(int(role['RoleID'])).mention) for role in roles]
            message += "\n".join(role_mentions)
            await ctx.respond(message, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
