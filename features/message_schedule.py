import discord
import sentry_sdk
from bson import ObjectId
from discord.ext import tasks

from database import client
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl
from utils.module_toggling import is_module_enabled
from utils.settings import get_setting
from utils.tzutil import get_now_for_server


def number_to_day_of_week(number: int):
    number = number - 1
    if number < 0:
        number = 0
    if number > 6:
        number = number % 7
    return ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[number]


class MessageSchedule(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    grp = discord.SlashCommandGroup(name="message_schedule", description="Schedule messages to be sent")

    @discord.Cog.listener()
    async def on_ready(self):
        self.handle_message_schedule.start()

    @grp.command(name="daily")
    @is_module_enabled("schedule")
    async def schedule_daily(self, ctx: discord.ApplicationContext, text: str):
        try:
            if client['ScheduledMessages'].count_documents({'GuildID': str(ctx.guild.id)}) >= int(
                    get_key("MAX_SCHEDULED_MESSAGES", "5")):
                await ctx.respond(trl(ctx.guild.id, ctx.user.id, "message_schedule_max_reached"), ephemeral=True)
                return

            inserted = client['ScheduledMessages'].insert_one(
                {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Type': 'Daily', 'Content': text})

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_daily_added", append_tip=True).format(
                id=str(inserted.inserted_id)), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @grp.command(name="weekly")
    @is_module_enabled("schedule")
    async def schedule_weekly(self, ctx: discord.ApplicationContext, day_of_week: discord.Option(int,
                                                                                                 description="Day of week to send the message at (1 - Monday, 7 - Sunday)"),
                              text: discord.Option(str, description="Text to send")):
        try:
            if client['ScheduledMessages'].count_documents({'GuildID': str(ctx.guild.id)}) >= int(
                    get_key("MAX_SCHEDULED_MESSAGES", "5")):
                await ctx.respond(trl(ctx.guild.id, ctx.user.id, "message_schedule_max_reached"), ephemeral=True)
                return

            inserted = client['ScheduledMessages'].insert_one(
                {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Type': 'Weekly', 'Day': day_of_week,
                 'Content': text})

            day_of_week_word = number_to_day_of_week(day_of_week)

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_weekly_added", append_tip=True).format(
                day_of_week=day_of_week_word, id=str(inserted.inserted_id)), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @grp.command(name="monthly")
    @is_module_enabled("schedule")
    async def schedule_monthly(self, ctx: discord.ApplicationContext,
                               day: discord.Option(int, description="Day of month to send at"),
                               text: discord.Option(str, description="Text to send")):
        try:
            if client['ScheduledMessages'].count_documents({'GuildID': str(ctx.guild.id)}) >= int(
                    get_key("MAX_SCHEDULED_MESSAGES", "5")):
                await ctx.respond(trl(ctx.guild.id, ctx.user.id, "message_schedule_max_reached"), ephemeral=True)
                return

            inserted = client['ScheduledMessages'].insert_one(
                {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Type': 'Monthly', 'Day': day,
                 'Content': text})

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "message_schedule_monthly_added", append_tip=True).format(day=day,
                                                                                                         id=str(
                                                                                                             inserted.inserted_id)),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @grp.command(name="yearly")
    @is_module_enabled("schedule")
    async def schedule_yearly(self, ctx: discord.ApplicationContext,
                              month: discord.Option(int, description="Month to send message at"),
                              day: discord.Option(int, description="Day of month to send message at"),
                              text: discord.Option(str, description="Text to send")):
        try:
            if client['ScheduledMessages'].count_documents({'GuildID': str(ctx.guild.id)}) >= int(
                    get_key("MAX_SCHEDULED_MESSAGES", "5")):
                await ctx.respond(trl(ctx.guild.id, ctx.user.id, "message_schedule_max_reached"), ephemeral=True)
                return

            inserted = client['ScheduledMessages'].insert_one(
                {'GuildID': str(ctx.guild.id), 'ChannelID': str(ctx.channel.id), 'Type': 'Yearly', 'Day': day,
                 'Month': month, 'Content': text})

            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "message_schedule_yearly_added", append_tip=True).format(month=month,
                                                                                                        day=day, id=str(
                        inserted.inserted_id)), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @grp.command(name="update_content")
    @is_module_enabled("schedule")
    async def update_content(self, ctx: discord.ApplicationContext,
                             object_id: discord.Option(str, description="ID of the message to update"),
                             new_text: discord.Option(str, description="New text to send")):
        try:
            if not ObjectId.is_valid(object_id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_invalid_id"), ephemeral=True)
                return

            update_result = client['ScheduledMessages'].update_one({'_id': ObjectId(object_id)},
                                                                   {'$set': {'Content': new_text}})

            if update_result.modified_count > 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_updated_content", append_tip=True),
                                  ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_not_found"), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @grp.command(name="delete")
    @is_module_enabled("schedule")
    async def delete(self, ctx: discord.ApplicationContext,
                     object_id: discord.Option(str, description="ID of the message to update")):

        try:
            if not ObjectId.is_valid(object_id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_invalid_id"), ephemeral=True)
                return

            delete_result = client['ScheduledMessages'].delete_one({'_id': ObjectId(object_id)})

            if delete_result.deleted_count > 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_deleted", append_tip=True),
                                  ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_schedule_not_found"), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @grp.command(name="list", description="List scheduled messages")
    @is_module_enabled("schedule")
    async def list(self, ctx: discord.ApplicationContext):

        try:
            list_for_server = client['ScheduledMessages'].find({'GuildID': str(ctx.guild.id)}).to_list()

            message_content = trl(ctx.user.id, ctx.guild.id, "message_schedule_list_title") + '\n'

            for i in list_for_server:
                channel = ctx.guild.get_channel(int(i['ChannelID']))
                if channel is None:
                    continue

                if i['Type'] == 'Daily':
                    date = 'Every day'
                elif i['Type'] == 'Weekly':
                    date = f'Every {number_to_day_of_week(i["Day"])}'
                elif i['Type'] == 'Monthly':
                    date = f'Every {i["Day"]} day of month'
                elif i['Type'] == 'Yearly':
                    date = f'Every {i["Month"]}/{i["Day"]}'
                else:
                    date = 'Unknown'

                brief_content = i['Content']
                if len(brief_content) > 60:
                    brief_content = i['Content'][:60] + '...'

                message_content += (
                            trl(ctx.user.id, ctx.guild.id, "message_schedule_list_row").format(channel=channel.mention,
                                                                                               id=str(i['_id']),
                                                                                               date=date,
                                                                                               brief_content=brief_content,
                                                                                               type=i['Type']) + '\n')

            await ctx.respond(message_content, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tasks.loop(minutes=1)
    async def handle_message_schedule(self):
        try:
            # Check if it is 12 PM
            schedules_list = client['ScheduledMessages'].find({}).to_list()

            for schedule in schedules_list:
                guild = self.bot.get_guild(int(schedule['GuildID']))
                if guild is None:
                    continue

                if not get_setting(guild.id, "module_schedule_enabled", True):
                    continue

                now = get_now_for_server(guild.id)
                if now.hour != 12 or now.minute != 0:
                    continue

                channel = guild.get_channel(int(schedule['ChannelID']))
                if channel is None:
                    continue

                # Daily messages

                if schedule['Type'] == 'Daily':
                    # Send it
                    await channel.send(content=schedule['Content'])

                # Weekly messages

                if schedule['Type'] == 'Weekly' and schedule['Day'] == (now.weekday() + 1):
                    # Send it
                    await channel.send(content=schedule['Content'])

                # Monthly messages

                if schedule['Type'] == 'Monthly' and schedule['Day'] == now.day:
                    # Send it
                    await channel.send(content=schedule['Content'])

                # Yearly messages

                if schedule['Type'] == 'Yearly' and schedule['Month'] == now.month and schedule['Day'] == now.day:
                    # Send it
                    await channel.send(content=schedule['Content'])
        except Exception as e:
            sentry_sdk.capture_exception(e)
