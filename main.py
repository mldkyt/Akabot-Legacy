# Akabot is a general purpose bot with a ton of features.
# Copyright (C) 2023-2025 lunya.pet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import logging
import os.path

akabot_logger = logging.getLogger("akabot")
akabot_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

akabot_logger.setLevel(logging.DEBUG)

if not os.path.exists("logs"):
    os.mkdir("logs")

file_handler = logging.FileHandler(filename="logs/akabot.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(akabot_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(akabot_formatter)

akabot_logger.addHandler(file_handler)
akabot_logger.addHandler(console_handler)

import discord
from discord.ext import commands as discord_commands_ext
from dotenv import load_dotenv

import utils.blocklist
from utils import module_toggling

load_dotenv()

from features import welcoming, leveling, antiraid, chat_streaks, chat_revive, chat_summary, reaction_roles, \
    logging_mod, admin_cmds, giveaways, feedback_cmd, moderation, verification, roles_on_join, \
    heartbeat, automod_actions, per_user_settings, server_settings, \
    auto_react, auto_response, tickets, birthday_announcements, \
    send_server_count, suggestions, temporary_vc, word_scrambler, statistics_channels, \
    anonymous_quefessions, analytics, economy, message_time_capsule, sticky_message, counting, denylist, \
    message_schedule, voice_channel_alerts, module_toggling_mod, private_temporary_vc, markov
from utils.config import get_key
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

akabot_logger.setLevel(log_level)

BOT_VERSION = get_key("Bot_Version", "1.4")

intents = discord.Intents.default()
intents.message_content = get_key('Message_Intent', "false") == "true"
intents.members = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    akabot_logger.info(f"Akabot v{BOT_VERSION} started")
    akabot_logger.info(f"Logged in as {bot.user.display_name} :3")

    bot.add_view(verification.VerificationView())
    bot.add_view(tickets.TicketCreateView(""))
    bot.add_view(tickets.TicketMessageView())
    if get_key('Message_Intent', "false") == "true":
        bot.add_view(suggestions.V2SuggestionView())
    else:
        bot.add_view(anonymous_quefessions.CreateButtonView())
    bot.add_view(anonymous_quefessions.InfoButtonView(0, 0))
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
                trl(ctx.user.id, ctx.guild.id, "cooldown_2", minutes=str(minutes), seconds=str(seconds)),
                ephemeral=True)
        else:
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "cooldown_1", seconds=str(seconds)), ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.MissingPermissions):
        await ctx.respond(
            trl(ctx.user.id, ctx.guild.id, "command_no_permission", permissions=', '.join(error.missing_permissions)),
            ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.NoPrivateMessage):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_no_private"), ephemeral=True)
        return

    if isinstance(error, discord_commands_ext.BotMissingPermissions):
        await ctx.respond(
            trl(ctx.user.id, ctx.guild.id, "command_bot_no_perm", permissions=', '.join(error.missing_permissions)),
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

    if isinstance(error, module_toggling.ModuleNotEnabled):
        emb = discord.Embed(
            title="Disabled",
            description=str(error),
            color=discord.Color.red()
        )

        await ctx.respond(embed=emb, ephemeral=True)
        return

    logging.exception("An error occurred:")
    try:
        # respond
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
    except Exception as e:
        logging.error("Failed to respond to message")
    raise error


bot.add_cog(welcoming.Welcoming(bot))
bot.add_cog(leveling.Leveling(bot))
bot.add_cog(antiraid.AntiRaid(bot))
bot.add_cog(chat_streaks.ChatStreaks(bot))
bot.add_cog(chat_revive.ChatRevive(bot))
bot.add_cog(chat_summary.ChatSummary(bot))
bot.add_cog(reaction_roles.ReactionRoles(bot))
bot.add_cog(logging_mod.Logging(bot))
bot.add_cog(admin_cmds.AdminCommands(bot))
bot.add_cog(giveaways.Giveaways(bot))
bot.add_cog(feedback_cmd.SupportCmd(bot))
bot.add_cog(moderation.Moderation(bot))
bot.add_cog(verification.Verification(bot))
bot.add_cog(roles_on_join.RolesOnJoin(bot))
bot.add_cog(heartbeat.Heartbeat())
bot.add_cog(automod_actions.AutomodActions(bot))
bot.add_cog(per_user_settings.PerUserSettings(bot))
bot.add_cog(server_settings.ServerSettings())
bot.add_cog(tickets.Tickets(bot))
bot.add_cog(birthday_announcements.BirthdayAnnouncements(bot))
bot.add_cog(send_server_count.SendServerCount(bot))
bot.add_cog(suggestions.Suggestions(bot))
bot.add_cog(temporary_vc.TemporaryVC(bot))
bot.add_cog(statistics_channels.StatisticChannels(bot))
bot.add_cog(anonymous_quefessions.AnonymousQuefessions(bot))
bot.add_cog(analytics.Analytics(bot))
bot.add_cog(economy.Economy(bot))
bot.add_cog(message_time_capsule.MessageTimeCapsule(bot))
bot.add_cog(sticky_message.StickyMessage(bot))
bot.add_cog(counting.Counting(bot))
bot.add_cog(denylist.ChannelDenylist(bot))
bot.add_cog(message_schedule.MessageSchedule(bot))
bot.add_cog(voice_channel_alerts.VoiceChannelAlerts(bot))
bot.add_cog(module_toggling_mod.ModuleToggling(bot))
bot.add_cog(private_temporary_vc.PrivateTemporaryVC(bot))

if get_key('Message_Intent', "false") == "true":
    bot.add_cog(auto_react.AutoReact(bot))
    bot.add_cog(auto_response.AutoResponse(bot))
    bot.add_cog(word_scrambler.WordScrambler(bot))
    bot.add_cog(markov.MarkovBot(bot))

bot.run(get_key("Bot_Token"))
