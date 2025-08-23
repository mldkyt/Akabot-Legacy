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
import logging

import discord
from bson import ObjectId
from discord.ext import commands as discord_commands_ext

from database import client
from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl
from utils.warning import add_warning

akabot_logger = logging.getLogger("akabot")

def db_add_automod_action(guild_id: int, rule_id: int, rule_name: str, action: str, additional) -> ObjectId:
    insert_result = client['AutomodActions'].insert_one(
        {'GuildID': str(guild_id), 'RuleID': str(rule_id), 'RuleName': rule_name, 'Action': action,
         'Additional': additional})

    return insert_result.inserted_id


def db_remove_automod_action(action_id: ObjectId):
    client['AutomodActions'].delete_one({'_id': action_id})


def db_get_automod_actions(guild_id: int):
    result = client['AutomodActions'].find({'GuildID': str(guild_id)}).to_list()
    return [(str(i['_id']), i['RuleID'], i['RuleName'], i['Action'], i['Additional']) for i in result]


class AutomodActionsStorage:
    def __init__(self):
        self.events = []

    def add_event(self, rule_id, message_id):
        self.expire_events()
        logging.debug("Adding event %s, %s", str(rule_id), str(message_id))
        self.events.append((rule_id, message_id, datetime.datetime.now()))

    def check_event(self, rule_id, message_id):
        self.expire_events()
        for event in self.events:
            if event[0] == rule_id and event[1] == message_id:
                logging.debug("Event already exists %s", str(event)) 
                return True
        return False

    def expire_events(self):
        for event in self.events:
            if event[2] < datetime.datetime.now() - datetime.timedelta(seconds=1):
                logging.debug("Expired event %s", str(event))
                self.events.remove(event)


class AutomodActions(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage_1 = AutomodActionsStorage()

    @discord.Cog.listener()
    async def on_auto_moderation_action_execution(self, payload: discord.AutoModActionExecutionEvent):
        try:
            if self.storage_1.check_event(payload.rule_id, payload.message_id):
                return

            self.storage_1.add_event(payload.rule_id, payload.message_id)
            automod_actions = db_get_automod_actions(payload.guild_id)
            for automod_action in automod_actions:
                if int(automod_action[1]) == payload.rule_id:

                    extra = str(automod_action[4])

                    extra = extra.replace("{keyword}", payload.matched_keyword)
                    extra = extra.replace("{name}", payload.member.display_name)
                    extra = extra.replace("{guild}", payload.guild.name)

                    if automod_action[3].startswith("timeout"):
                        if payload.member.timed_out:
                            return

                        duration = automod_action[3].split(" ")[1]
                        if duration == "1h":
                            duration = datetime.timedelta(hours=1)
                        elif duration == "12h":
                            duration = datetime.timedelta(hours=12)
                        elif duration == "1d":
                            duration = datetime.timedelta(days=1)
                        elif duration == "7d":
                            duration = datetime.timedelta(days=7)
                        elif duration == "28d":
                            duration = datetime.timedelta(days=28)

                        await payload.member.timeout_for(duration, reason=extra)
                    elif automod_action[3] == "ban":
                        await payload.member.ban(reason=extra, delete_message_seconds=604800)
                    elif automod_action[3] == "kick":
                        await payload.member.kick(reason=extra)
                    elif automod_action[3] == "DM":
                        try:
                            await payload.member.send(extra)
                        except discord.Forbidden:
                            pass
                    elif automod_action[3] == "warning":
                        await add_warning(payload.member, payload.guild, extra)

        except Exception as e:
            akabot_logger.exception("An error occured:")

    automod_actions_subcommands = discord.SlashCommandGroup(name='automod_actions',
                                                            description='Automod actions management.')

    @automod_actions_subcommands.command(name='add', description='Add an automod action.')
    @discord_commands_ext.bot_has_permissions(manage_guild=True)
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord.option(name="rule_name", description="Name of the rule, as it is in the settings.")
    @discord.option(name="action", description="Type of the action.",
                    choices=["ban", "kick", "timeout 1h", "timeout 12h", "timeout 1d", "timeout 7d", "timeout 28d",
                             "DM", "warning"])
    @discord.option(name="message_reason", description="Reason for the action / Message for DM.")
    @analytics("automod action add")
    @blocklist()
    async def automod_actions_add(self, ctx: discord.ApplicationContext, rule_name: str, action: str,
                                  message_reason: str = None):
        try:
            # verify count of rules
            automod_db_actions = db_get_automod_actions(ctx.guild.id)
            if len(automod_db_actions) >= int(get_key("AutomodActions_MaxActions", "5")):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_actions_max_reached"), ephemeral=True)
                return

            automod_actions = await ctx.guild.fetch_auto_moderation_rules()
            # verify rule exists and assign rule_id

            automod_rule = None
            for rule in automod_actions:
                if rule.name == rule_name:
                    automod_rule = rule
                    break

            if not automod_rule:
                valid_rules = ', '.join([f"{rule.name}" for rule in automod_actions])
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_rule_doesnt_exist", rules=valid_rules),
                                  ephemeral=True)
                return

            # Check if there's already a timeout action
            for i in automod_db_actions:
                if i[1] == automod_rule.id and i[3] == action:
                    await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_rule_action_already_exists"),
                                      ephemeral=True)
                    return

                if i[1] == automod_rule.id and i[3].startswith("timeout") and action.startswith("timeout"):
                    await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_rule_timeout_action_already_exists"),
                                      ephemeral=True)
                    return

            # Determine message if not specified
            if action == "DM" and not message_reason:
                message_reason = trl(0, ctx.guild.id, "automod_default_dm")
            elif not message_reason:
                message_reason = trl(0, ctx.guild.id, "automod_default")

            action_id = db_add_automod_action(ctx.guild.id, automod_rule.id, rule_name, action,
                                              additional=message_reason)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "automod_added", append_tip=True, id=str(action_id)),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @automod_actions_subcommands.command(name='remove', description='Remove an automod action.')
    @discord_commands_ext.bot_has_permissions(manage_guild=True)
    @discord_commands_ext.has_permissions(manage_messages=True)
    @discord.option(name="rule_name", description="Name of the rule, as it is in the settings.")
    @analytics("automod action remove")
    @blocklist()
    async def automod_actions_remove(self, ctx: discord.ApplicationContext, action_id: str):
        try:
            # verify action exists, rule_name is NOT rule_id

            if not ObjectId.is_valid(action_id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_rule_doesnt_exist_2"), ephemeral=True)
                return

            automod_actions = db_get_automod_actions(ctx.guild.id)
            automod_rule = None
            for rule in automod_actions:
                if rule[0] == action_id:
                    automod_rule = rule
                    break

            if not automod_rule:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_rule_doesnt_exist_2"), ephemeral=True)
                return

            db_remove_automod_action(ObjectId(action_id))
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_removed", append_tip=True), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @automod_actions_subcommands.command(name='list', description='List automod actions.')
    @discord_commands_ext.bot_has_permissions(manage_guild=True)
    @discord_commands_ext.has_permissions(manage_messages=True)
    @analytics("automod action list")
    @blocklist()
    async def automod_actions_list(self, ctx: discord.ApplicationContext):
        try:
            automod_actions = db_get_automod_actions(ctx.guild.id)
            if not automod_actions:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "automod_actions_list_empty", append_tip=True),
                                  ephemeral=True)
                return

            actions = '\n'.join([f"`{action[0]}`: {action[2]}: {action[3]}" for action in automod_actions])
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "automod_actions_list", append_tip=True, actions=actions),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
