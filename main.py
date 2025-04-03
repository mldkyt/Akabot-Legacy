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

import logging

import discord
from discord.ui.button import B
import sentry_sdk
from discord.ext import commands as discord_commands_ext
from dotenv import load_dotenv
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration

import utils.blocklist

load_dotenv()

from features import welcoming, leveling, antiraid, chat_streaks, chat_revive, chat_summary, reaction_roles, \
    logging_mod, admin_cmds, giveaways, feedback_cmd, moderation, verification, roles_on_join, \
    heartbeat, automod_actions, power_outage_announcement, per_user_settings, server_settings, \
    auto_react, auto_response, bot_help, announcement_channels, tickets, debug_commands, birthday_announcements, \
    send_server_count, suggestions, temporary_vc, rp, word_scrambler, statistics_channels, \
    anonymous_quefessions, analytics, economy, message_time_capsule, sticky_message
from utils.config import get_key
from utils.db_converter import update
from utils.languages import get_translation_for_key_localized as trl

log_level = get_key("Log_Level", "info")
if log_level == "debug":
    log_level = logging.DEBUG
elif log_level == "info":
    log_level = logging.INFO
elif log_level == "warning":
    log_level = logging.WARNING
elif log_level == "error":
    log_level = logging.ERROR
else:
    log_level = logging.INFO
    print('Invalid log mode, defaulting to info')

print("Setting log level", log_level, flush=True)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger().setLevel(log_level)

BOT_VERSION = get_key("Bot_Version", "3.5")

if get_key("Sentry_Enabled", "false") == "true":
    sentry_sdk.init(get_key("Sentry_DSN"),
                    integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
                                  AioHttpIntegration(),
                                  AsyncioIntegration(),
                                  PyMongoIntegration()],
                    traces_sample_rate=1.0,
                    profiles_sample_rate=1.0)

intents = discord.Intents.default()
intents.message_content = get_key('Message_Intent', "false") == "true"
intents.members = True

update()

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    bot.add_view(verification.VerificationView())
    bot.add_view(tickets.TicketCreateView(""))
    bot.add_view(tickets.TicketMessageView())
    if get_key('Message_Intent', "false") == "true":
        bot.add_view(suggestions.V2SuggestionView())
    else:
        bot.add_view(anonymous_quefessions.CreateButtonView())
    bot.add_view(anonymous_quefessions.InfoButtonView())
    bot.add_view(chat_summary.OpenPaginatorView())
    bot.add_view(message_time_capsule.AddYoursView())
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"v{BOT_VERSION}"))


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, discord_commands_ext.CommandOnCooldown):
        minutes = int(error.retry_after / 60)
        seconds = int(error.retry_after % 60)
        if minutes > 0:
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "cooldown_2").format(minutes=str(minutes), seconds=str(seconds)),
                ephemeral=True)
        else:
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "cooldown_1").format(seconds=str(seconds)), ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.MissingPermissions):
        await ctx.respond(
            trl(ctx.user.id, ctx.guild.id, "command_no_permission").format(
                permissions=', '.join(error.missing_permissions)),
            ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.NoPrivateMessage):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_no_private"), ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.BotMissingPermissions):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_bot_no_perm").format(
            permissions=', '.join(error.missing_permissions)),
            ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.PrivateMessageOnly):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_private"), ephemeral=True)
        return

    if isinstance(error, utils.blocklist.BlocklistError):
        emb = discord.Embed(
            title="Blocklisted",
            description=str(error),
            color=discord.Color.red()
        )

        await ctx.respond(embed=emb, ephemeral=True)
        return

    sentry_sdk.capture_exception(error)
    try:
        # respond
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
    except Exception as e:
        logging.error("Failed to respond to message")
        sentry_sdk.capture_exception(e)
    raise error


if get_key("Feature_WelcomeGoodbye", "true") == "true":
    bot.add_cog(welcoming.Welcoming(bot))
if get_key("Feature_Leveling", "true") == "true":
    bot.add_cog(leveling.Leveling(bot))
if get_key("Feature_AntiRaid", "true") == "true":
    bot.add_cog(antiraid.AntiRaid(bot))
if get_key("Feature_ChatStreaks", "true") == "true":
    bot.add_cog(chat_streaks.ChatStreaks(bot))
if get_key("Feature_ChatRevive", "true") == "true":
    bot.add_cog(chat_revive.ChatRevive(bot))
if get_key("Feature_ChatSummary", "true") == "true":
    bot.add_cog(chat_summary.ChatSummary(bot))
if get_key("Feature_ReactionRoles", "true") == "true":
    bot.add_cog(reaction_roles.ReactionRoles(bot))
if get_key("Feature_Logging", "true") == "true":
    bot.add_cog(logging_mod.Logging(bot))
if get_key("Feature_AdminCommands", "true") == "true":
    bot.add_cog(admin_cmds.AdminCommands(bot))
if get_key("Feature_Giveaways", "true") == "true":
    bot.add_cog(giveaways.Giveaways(bot))
if get_key("Feature_FeedbackCmd", "true") == "true":
    bot.add_cog(feedback_cmd.SupportCmd(bot))
if get_key("Feature_Moderation", "true") == "true":
    bot.add_cog(moderation.Moderation(bot))
if get_key("Feature_Verification", "true") == "true":
    bot.add_cog(verification.Verification(bot))
if get_key("Feature_RolesOnJoin", "true") == "true":
    bot.add_cog(roles_on_join.RolesOnJoin(bot))
if get_key("Feature_Heartbeat", "true") == "true":
    bot.add_cog(heartbeat.Heartbeat())
if get_key("Feature_AutomodActions", "true") == "true":
    bot.add_cog(automod_actions.AutomodActions(bot))
if get_key("PowerOutageAnnouncements_Enabled", "false") == "true":
    bot.add_cog(power_outage_announcement.PowerOutageAnnouncement(bot))
if get_key("PerUserSettings_Enabled", "true") == "true":
    bot.add_cog(per_user_settings.PerUserSettings(bot))
if get_key("Feature_ServerSettings", "true") == "true":
    bot.add_cog(server_settings.ServerSettings())
if get_key('Message_Intent', "false") == "true":
    if get_key("Feature_AutoReact", "true") == "true":
        bot.add_cog(auto_react.AutoReact(bot))
    if get_key("Feature_AutoResponse", "true") == "true":
        bot.add_cog(auto_response.AutoResponse(bot))
if get_key("Feature_HelpCommands", "true") == "true":
    bot.add_cog(bot_help.Help(bot))
if get_key("Feature_AnnouncementChannels", "true") == "true":
    bot.add_cog(announcement_channels.AnnouncementChannels(bot))
if get_key("Feature_Tickets", "true") == "true":
    bot.add_cog(tickets.Tickets(bot))
if get_key("Feature_DebugCommands", "false") == "true":
    bot.add_cog(debug_commands.DebugCommands(bot))
if get_key("Feature_BirthdayAnnouncements", "true") == "true":
    bot.add_cog(birthday_announcements.BirthdayAnnouncements(bot))
bot.add_cog(send_server_count.SendServerCount(bot))
if get_key("Feature_SuggestionsEnabled", "true") == "true":
    bot.add_cog(suggestions.Suggestions(bot))
if get_key('Feature_TemporaryVC', 'true') == 'true':
    bot.add_cog(temporary_vc.TemporaryVC(bot))
if get_key("Feature_Roleplay", "true") == "true":
    bot.add_cog(rp.RoleplayCommands(bot))
if get_key('Message_Intent', "false") == "true":
    if get_key("Feature_WordScramble", "true") == "true":
        bot.add_cog(word_scrambler.WordScrambler(bot))
if get_key("Feature_StatisticChannels", "true") == "true":
    bot.add_cog(statistics_channels.StatisticChannels(bot))
if get_key("Feature_AnonymousQuefessions", "true") == "true":
    bot.add_cog(anonymous_quefessions.AnonymousQuefessions(bot))
bot.add_cog(analytics.Analytics(bot))
if get_key("Feature_Economy", "true") == "true":
    bot.add_cog(economy.Economy(bot))
if get_key("Feature_MessageTimeCapsule", "true") == "true":
    bot.add_cog(message_time_capsule.MessageTimeCapsule(bot))
if get_key("Feature_StickyMessage", "true") == "true":
    bot.add_cog(sticky_message.StickyMessage(bot))

bot.run(get_key("Bot_Token"))
