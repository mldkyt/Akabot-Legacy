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

import datetime
import logging

import discord
import sentry_sdk
from discord.ext import commands as commands_ext
from discord.ext import tasks

from database import client
from utils.analytics import analytics
from utils.languages import get_translation_for_key_localized as trl
from utils.logging_util import log_into_logs
from utils.settings import get_setting, set_setting
from utils.tzutil import get_now_for_server


def init(msg: discord.Message):
    if client['ChatSummary'].count_documents(
            {'GuildID': str(msg.guild.id), 'ChannelID': str(msg.channel.id)}) == 0:
        client['ChatSummary'].insert_one({
            'GuildID': str(msg.guild.id),
            'ChannelID': str(msg.channel.id),
            'Enabled': False,
            'MessageCount': 0,
            'Keywords': []
        })
        client['YearlyChatSummary'].insert_one({
            'GuildID': str(msg.guild.id),
            'ChannelID': str(msg.channel.id),
            'MessageCount': 0
        })
        client['MonthlyChatSummary'].insert_one({
            'GuildID': str(msg.guild.id),
            'ChannelID': str(msg.channel.id),
            'MessageCount': 0
        })


def inc(msg: discord.Message):
    kwds = client['ChatSummary'].find_one({'GuildID': str(msg.guild.id), 'ChannelID': str(msg.channel.id)})
    if kwds is not None and 'Keywords' in kwds:
        kwds = kwds['Keywords']
    else:
        kwds = []

    upd = {
        '$inc': {f'Messages.{msg.author.id}': 1, 'MessageCount': 1}
    }

    for kwd in kwds:
        if kwd in msg.content:
            upd['$inc'][f'KeywordsCounting.{kwd}'] = 1

    client['ChatSummary'].update_one({'GuildID': str(msg.guild.id), 'ChannelID': str(msg.channel.id)}, upd)
    client['YearlyChatSummary'].update_one({'GuildID': str(msg.guild.id), 'ChannelID': str(msg.channel.id)}, upd)
    client['MonthlyChatSummary'].update_one({'GuildID': str(msg.guild.id), 'ChannelID': str(msg.channel.id)}, upd)


async def special_chat_summary(channel, date, guild, i, override_month: bool = False, override_year: bool = False):
    # Check for year first

    now = get_now_for_server(channel.guild.id)

    if (now.month == 1 and now.day == 1) or override_year: # 1st January
        i = client['YearlyChatSummary'].find_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})
        return await normal_chat_summary(channel, date, guild, i, summary_title="yearly")
    elif now.day == 1 or override_month:
        i = client['MonthlyChatSummary'].find_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})
        return await normal_chat_summary(channel, date, guild, i, summary_title="monthly")
    else:
        return await normal_chat_summary(channel, date, guild, i)


async def normal_chat_summary(channel, date, guild, i, summary_title: str = ""):
    chat_summary_title_key = "chat_summary_title"
    chat_summary_top_count_key = "chatsummary_top_count"
    chat_summary_top_count_default = 5
    db = "ChatSummary"
    if summary_title == "yearly":
        chat_summary_title_key = "yearly_chat_summary_title"
        chat_summary_top_count_key = "chatsummary_yearly_top_count"
        chat_summary_top_count_default = 10
        db = "YearlyChatSummary"
    elif summary_title == "monthly":
        chat_summary_title_key = "monthly_chat_summary_title"
        chat_summary_top_count_key = "chatsummary_monthly_top_count"
        chat_summary_top_count_default = 10
        db = "MonthlyChatSummary"

    chat_summary_message = trl(0, guild.id, chat_summary_title_key).format(date=date)
    chat_summary_message += '\n'
    chat_summary_message += trl(0, guild.id, "chat_summary_messages").format(
        messages=str(i['MessageCount']))
    top_members = {k: v for k, v in sorted(i['Messages'].items(), key=lambda item: item[1], reverse=True)}
    j = 0  # idk
    for k, v in top_members.items():
        j += 1
        member = guild.get_member(int(k))
        if member is not None:
            chat_summary_message += trl(0, guild.id, "chat_summary_line").format(position=j,
                                                                                 name=member.display_name,
                                                                                 messages=v)
        else:
            chat_summary_message += trl(0, guild.id, "chat_summary_line_unknown_user").format(position=j,
                                                                                              id=k,
                                                                                              messages=v)

        if j >= int(get_setting(guild.id, chat_summary_top_count_key, chat_summary_top_count_default)):
            break
    # Keywords
    kwd_cnt = i.get('KeywordsCounting', {})
    logging.debug('Getting keywords')
    kwd_cnt = {k: v for k, v in sorted(kwd_cnt.items(), key=lambda item: item[1], reverse=True)}
    logging.debug('Found %d keywords in the list', len(kwd_cnt))
    if len(kwd_cnt) > 0:
        chat_summary_message += trl(0, guild.id, "chat_summary_keywords_title")
        for k, v in kwd_cnt.items():
            if v == 0:
                continue
            logging.debug('Appending keyword %s with count %d', k, v)
            chat_summary_message += trl(0, guild.id, "chat_summary_keywords_line").format(keyword=k,
                                                                                          count=v)
    try:
        await channel.send(chat_summary_message)
    except Exception as e:
        sentry_sdk.capture_exception(e)
    client[db].update_one({'GuildID': str(guild.id), 'ChannelID': str(channel.id)},
                                     {'$set': {'Messages': {}, 'MessageCount': 0, 'KeywordsCounting': {}}})


class ChatSummary(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        super().__init__()
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.summarize.start()

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.guild is None:
                return

            if message.author.bot:
                return

            init(message)

            inc(message)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message_edit(self, old_message: discord.Message, new_message: discord.Message):
        try:
            if new_message.guild is None:
                return

            if new_message.author.bot:
                return

            countedits = get_setting(new_message.guild.id, "chatsummary_countedits", "False")
            if countedits == "False":
                return

            init(new_message)
            inc(new_message)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @tasks.loop(minutes=1)
    async def summarize(self):
        try:
            logging.info('Running summarize task')
            res = client['ChatSummary'].find({'Enabled': True}).to_list()
            for i in res:
                now = get_now_for_server(i['GuildID'])

                if now.hour != 0 or now.minute != 0:
                    continue

                guild = self.bot.get_guild(int(i['GuildID']))
                if guild is None:
                    logging.warning('Couldn\'t find guild %s', i['GuildID'])
                    continue

                channel = guild.get_channel(int(i['ChannelID']))
                if channel is None:
                    logging.warning('Couldn\'t find channel %s', i['ChannelID'])
                    continue

                logging.info('Summarizing %s in %s', channel.name, guild.name)

                if not channel.can_send():
                    continue

                yesterday = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)  # Get yesterday

                # Get date format
                date_format = get_setting(guild.id, "chatsummary_dateformat", "YYYY/MM/DD")

                # Better formatting for day
                day = str(yesterday.day)
                if len(day) == 1:
                    day = "0" + day

                # Better formatting for the month
                month = str(yesterday.month)
                if len(month) == 1:
                    month = "0" + month

                # Select appropriate date format
                if date_format == "DD/MM/YYYY":
                    date = f"{day}/{month}/{yesterday.year}"
                elif date_format == "DD. MM. YYYY":
                    date = f"{day}. {month}. {yesterday.year}"
                elif date_format == "YYYY/DD/MM":
                    date = f"{yesterday.year}/{day}/{month}"
                elif date_format == "MM/DD/YYYY":
                    date = f"{month}/{day}/{yesterday.year}"
                elif date_format == "YYYY年MM月DD日":
                    date = f"{yesterday.year}年{month}月{day}日"
                else:
                    date = f"{yesterday.year}/{month}/{day}"

                setting = get_setting(guild.id, "chatsummary_mode", "normal")

                if setting == "normal":
                    await normal_chat_summary(channel, date, guild, i)
                elif setting == "special":
                    await special_chat_summary(channel, date, guild, i)

        except Exception as e:
            sentry_sdk.capture_exception(e)

    chat_summary_subcommand = discord.SlashCommandGroup(
        name='chatsummary', description='Chat summary')

    @chat_summary_subcommand.command(name="add", description="Add a channel to count to chat summary")
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.bot_has_permissions(send_messages=True)
    @analytics("chatsummary add")
    async def command_add(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            res = client['ChatSummary'].update_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(channel.id)},
                                                   {'$set': {'Enabled': True}})
            if res.modified_count == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "chat_summary_add_already_added"), ephemeral=True)
                return

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "chat_summary_add_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_channel"), value=f"{channel.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")

            # Log into logs
            await log_into_logs(ctx.guild, logging_embed)

            # Send response
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "chat_summary_add_added", append_tip=True), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @chat_summary_subcommand.command(name="remove", description="Remove a channel from being counted to chat summary")
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @analytics("chatsummary remove")
    async def command_remove(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            res = client['ChatSummary'].update_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(channel.id)},
                                                   {'$set': {'Enabled': False}})
            if res.modified_count == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'chat_summary_remove_already_removed'), ephemeral=True)

            # Logging embed
            logging_embed = discord.Embed(title=trl(ctx.user.id, ctx.guild.id, "chat_summary_remove_log_title"))
            logging_embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_channel"),
                                    value=f"{channel.mention}")
            logging_embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_user"),
                                    value=f"{ctx.user.mention}")

            # Send
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "chat_summary_remove_removed", append_tip=True),
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @chat_summary_subcommand.command(name="dateformat", description="Set the date format of Chat Streak messages.")
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name="date_format", description="Format",
                    choices=["YYYY/MM/DD", "DD/MM/YYYY", "DD. MM. YYYY", "YYYY/DD/MM", "MM/DD/YYYY", "YYYY年MM月DD日"])
    @analytics("chatsummary dateformat")
    async def summary_dateformat(self, ctx: discord.ApplicationContext, date_format: str):
        try:
            # Get old setting
            old_date_format = get_setting(ctx.guild.id, "chatsummary_dateformat", "YYYY/MM/DD")

            # Save setting
            set_setting(ctx.guild.id, "chatsummary_dateformat", date_format)

            # Create logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "chat_summary_dateformat_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "chat_summary_dateformat_log_dateformat"),
                                    value=f"{old_date_format} -> {date_format}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"),
                                    value=f"{ctx.user.mention}")

            # Send
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "chat_summary_dateformat_set", append_tip=True).format(
                    format=date_format),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @chat_summary_subcommand.command(name="top_count", description="Set the amount of people to show in summary messages.")
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name='normal_count', description='The normal Chat Summary count of people')
    @discord.option(name='monthly_count', description='The monthly Chat Summary count of people')
    @discord.option(name='yearly_count', description='The yearly Chat Summary count of people')
    @analytics("chatsummary top_count")
    async def summary_top_count(self, ctx: discord.ApplicationContext, normal_count: int = -1, monthly_count: int = -1, yearly_count: int = -1):
        try:
            # Old settings
            old_top_count = get_setting(ctx.guild.id, "chatsummary_top_count", 5 if normal_count == -1 else normal_count)
            old_yearly_top_count = get_setting(ctx.guild.id, "chatsummary_yearly_top_count", 10 if yearly_count == -1 else yearly_count)
            old_monthly_top_count = get_setting(ctx.guild.id, "chatsummary_monthly_top_count", 10 if monthly_count == -1 else monthly_count)

            if normal_count == -1:
                normal_count = old_top_count
            if monthly_count == -1:
                monthly_count = old_monthly_top_count
            if yearly_count == -1:
                yearly_count = old_yearly_top_count

            # Set new settings
            set_setting(ctx.guild.id, "chatsummary_top_count", normal_count)
            set_setting(ctx.guild.id, "chatsummary_yearly_top_count", yearly_count)
            set_setting(ctx.guild.id, "chatsummary_monthly_top_count", monthly_count)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "chat_summary_top_count_set", append_tip=True).format(
                    normal=str(normal_count),
                    monthly=str(monthly_count),
                    yearly=str(yearly_count)
                ), ephemeral=True)

        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @chat_summary_subcommand.command(name="countedits",
                                     description="Enable or disable counting of message edits as sent messages.")
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @analytics("chatsummary countedits")
    async def chatsummary_countedits(self, ctx: discord.ApplicationContext, countedits: bool):
        try:
            # Get old setting
            old_count_edits = get_setting(ctx.guild.id, "chatsummary_count_edits", str(False))

            # Save setting
            set_setting(ctx.guild.id, "chatsummary_countedits", str(countedits))

            # Create logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "chat_summary_count_edits_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "chat_summary_count_edits_log_count_edits"),
                                    value="{old} -> {new}".format(old=("Yes" if old_count_edits == "True" else "No"),
                                                                  new=("Yes" if countedits else "No")))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"),
                                    value=f"{ctx.user.mention}")

            # Send
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "chat_summary_count_edits_on", append_tip=True) if countedits else
                trl(ctx.user.id, ctx.guild.id, "chat_summary_count_edits_off", append_tip=True),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @chat_summary_subcommand.command(name='add_keyword', description='Add a keyword to be counted')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @analytics("chatsummary add_keyword")
    async def chatsummary_add_kwd(self, ctx: discord.ApplicationContext, kwd: str):
        if 1 < len(kwd.split(' ')) < 1:
            logging.debug('Keyword was made of %d words', len(kwd.split(' ')))
            await ctx.respond('Please provide a single keyword.', ephemeral=True)
            return

        res = client['ChatSummary'].update_one(
            {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Keywords': {'$exists': False}},
            {'$set': {'Keywords': []}})
        logging.debug('Added Keywords field to %s, matched %d, modified %d', ctx.guild.id, res.matched_count,
                      res.modified_count)

        res = client['ChatSummary'].find_one(
            {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Keywords': kwd})

        if res is not None:
            logging.debug('Keyword %s already added', kwd)
            await ctx.respond('Keyword already added.', ephemeral=True)
            return

        res = client['ChatSummary'].update_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id)},
                                               {'$push': {'Keywords': kwd}})
        logging.debug('Added keyword %s, affected %d, matched %d', kwd, res.modified_count, res.matched_count)

        await ctx.respond('Keyword added.', ephemeral=True)

    @chat_summary_subcommand.command(name='remove_keyword', description='Remove a keyword from being counted')
    @commands_ext.guild_only()
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @analytics("chatsummary remove_keyword")
    async def chatsummary_remove_kwd(self, ctx: discord.ApplicationContext, kwd: str):
        logging.debug('Removing keyword %s', kwd)
        res = client['ChatSummary'].find_one(
            {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Keywords': kwd})

        if res is None:
            logging.debug('Keyword wasn\'t found')
            await ctx.respond('Keyword not found.', ephemeral=True)
            return

        res = client['ChatSummary'].update_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id)},
                                               {'$pull': {'Keywords': kwd}, '$unset': {f'KeywordsCounting.{kwd}': ''}})
        logging.debug('Removed %s, affected %d, matched %d', kwd, res.modified_count, res.matched_count)

        await ctx.respond('Keyword removed.', ephemeral=True)

    # The commented code below is for testing purposes
    # @chat_summary_subcommand.command(name="test", description="Test command for testing purposes")
    # @commands_ext.guild_only()
    # @discord.default_permissions(manage_guild=True)
    # @commands_ext.has_permissions(manage_guild=True)
    # async def test_summarize(self, ctx: discord.ApplicationContext):

    #     cur = db.cursor()
    #     cur.execute('SELECT guild_id, channel_id, messages FROM chat_summary WHERE enabled = 1')
    #     for i in cur.fetchall():
    #         guild = self.bot.get_guild(i[0])
    #         if guild is None:
    #             continue

    #         channel = guild.get_channel(i[1])
    #         if channel is None:
    #             continue

    #         if not channel.can_send():
    #             continue

    #         now = datetime.datetime.now(datetime.timezone.utc)

    #         # Get date format
    #         date_format = get_setting(guild.id, "chatsummary_dateformat", "YYYY/MM/DD")

    #         # Better formatting for day
    #         day = str(now.day)
    #         if len(day) == 1:
    #             day = "0" + day

    #         # Better formatting for the month
    #         month = str(now.month)
    #         if len(month) == 1:
    #             month = "0" + month

    #         # Select appropriate date format
    #         if date_format == "DD/MM/YYYY":
    #             date = f"{day}/{month}/{now.year}"
    #         elif date_format == "DD. MM. YYYY":
    #             date = f"{day}. {month}. {now.year}"
    #         elif date_format == "YYYY/DD/MM":
    #             date = f"{now.year}/{day}/{month}"
    #         elif date_format == "MM/DD/YYYY":
    #             date = f"{month}/{day}/{now.year}"
    #         else:
    #             date = f"{now.year}/{month}/{day}"

    #         chat_summary_message = f'# Chat Summary for {date}:\n'
    #         chat_summary_message += '\n'
    #         chat_summary_message += f'**Messages**: {i[2]}\n'

    #         cur.execute(
    #             'SELECT member_id, messages FROM chat_summary_members WHERE guild_id = ? AND channel_id = ? ORDER BY '
    #             'messages DESC LIMIT 5', (i[0], i[1]))

    #         jndex = 0  # idk
    #         for j in cur.fetchall():
    #             jndex += 1
    #             member = guild.get_member(j[0])
    #             if member is not None:
    #                 chat_summary_message += f'{jndex}. {member.display_name} at {j[1]} messages\n'
    #             else:
    #                 chat_summary_message += f'{jndex}. User({j[0]}) at {j[1]} messages\n'

    #         try:
    #             await channel.send(chat_summary_message)
    #         except Exception as e:
    #            sentry_sdk.capture_exception(e)

    #         cur.execute('UPDATE chat_summary SET messages = 0 WHERE guild_id = ? AND channel_id = ?', (i[0], i[1]))
    #         cur.execute(
    #             'DELETE FROM chat_summary_members WHERE guild_id = ? AND channel_id = ?', (i[0], i[1]))

    #     cur.close()
    #     db.commit()

    #     await ctx.respond("Done.", ephemeral=True)
