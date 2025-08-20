
import datetime
import io
import logging

import discord
from discord.ext import tasks
from discord.ext.commands import dm_only, guild_only
from discord.ext.pages import Paginator
from pytimeparse import parse

from database import client
from utils.languages import get_translation_for_key_localized as trl
from utils.leveling import add_xp
from utils.module_toggling import is_module_enabled
from utils.per_server_settings import get_setting

akabot_logger = logging.getLogger("akabot")

class AddYoursModal(discord.ui.Modal):
    def __init__(self, message_id: str):
        super().__init__(title="Add Yours", timeout=180)
        self.message_id = message_id

        self.message = discord.ui.InputText(label="Message", style=discord.InputTextStyle.long)
        self.add_item(self.message)

    async def callback(self, interaction: discord.Interaction):
        if interaction.channel is None:
            await interaction.respond(trl(interaction.user.id, interaction.guild.id, "command_error_generic"),
                                      ephemeral=True)
            return

        if self.message.value is None or interaction.user is None:
            await interaction.respond(trl(0, interaction.guild.id, "message_cannot_be_empty"), ephemeral=True)
            return

        if len(self.message.value) == 0:
            await interaction.respond(trl(interaction.user.id, interaction.guild.id, "message_cannot_be_empty"),
                                      ephemeral=True)
            return

        if len(self.message.value) > 280:
            await interaction.respond(trl(interaction.user.id, interaction.guild.id, "message_cannot_be_long"),
                                      ephemeral=True)
            return

        client['CollectionMessageCapsule'].update_many({"MessageID": {"$eq": self.message_id}}, {"$push": {"Replies": {
            "UserID": str(interaction.user.id),
            "Message": self.message.value
        }}})

        await interaction.respond(trl(interaction.user.id, interaction.guild.id, "message_added_to_collection"),
                                  ephemeral=True)


class AddYoursView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Yours", style=discord.ButtonStyle.green, custom_id="add_yours")
    async def add_yours(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.message is None or interaction.user is None:
            await interaction.respond(trl(interaction.user.id, interaction.guild.id, "command_error_generic"),
                                      ephemeral=True)
            return

        data = client['CollectionMessageCapsule'].find_one({"MessageID": str(interaction.message.id)})
        if data is None:
            await interaction.respond(trl(interaction.user.id, interaction.guild.id, "message_not_found"),
                                      ephemeral=True)
            return

        if any(i["UserID"] == str(interaction.user.id) for i in data["Replies"]):
            await interaction.respond(trl(interaction.user.id, interaction.guild.id, "you_already_added_your_message"),
                                      ephemeral=True)
            return

        if data['Time'] < datetime.datetime.now():
            await interaction.respond(
                trl(interaction.user.id, interaction.guild.id, "you_cant_add_your_message_in_the_past"), ephemeral=True)
            return

        await interaction.response.send_modal(AddYoursModal(str(interaction.message.id)))

class MessageTimeCapsule(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.get_cog("Config")

    @discord.Cog.listener()
    async def on_ready(self):
        self.check_dm_messages.start()
        self.check_guild_messages.start()
        self.check_collection_messages.start()

    schedule_group = discord.SlashCommandGroup("schedule", "Schedule message commands")

    @schedule_group.command(name="message", description="Schedule a message")
    @is_module_enabled("time_capsule")
    @guild_only()
    async def schedule_message(self, ctx: discord.ApplicationContext, time: str, message: str):
        """Schedule a message"""
        try:
            time_parsed = parse(time)
            if time_parsed is None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "invalid_time_format"), ephemeral=True)
                return

            target_time = datetime.datetime.now() + datetime.timedelta(seconds=time_parsed)

            client['MessageCapsule'].insert_one({
                "UserID": str(ctx.author.id),
                "GuildID": str(ctx.guild.id),
                "ChannelID": str(ctx.channel.id),
                "Message": message,
                "Time": target_time
            })

            target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "message_scheduled_on", time=target_time_str),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @schedule_group.command(name="messages", description="List all messages")
    @is_module_enabled("time_capsule")
    @guild_only()
    async def schedule_messages(self, ctx: discord.ApplicationContext):
        """List all messages"""
        messages = client['MessageCapsule'].find({"GuildID": str(ctx.guild.id)}).to_list()

        if len(messages) == 0:
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "no_messages"), ephemeral=True)
            return

        pages = []
        current_page = ""

        for i, message in enumerate(messages):
            current_page += f"{i+1}. {message['Message']}\n"
            if i % 10 == 0:
                pages.append(current_page)
                current_page = ""

        if current_page != "":
            pages.append(current_page)

        if len(pages) == 0:
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "no_messages"), ephemeral=True)
            return

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @schedule_group.command(name="reminder", description="Schedule a reminder")
    @dm_only()
    async def schedule_reminder(self, ctx: discord.ApplicationContext, time: str, message: str):
        """Schedule a reminder"""
        try:
            # Check DM ability
            try:
                sent_msg = await ctx.author.send(trl(ctx.user.id, ctx.guild.id, "dm_test_message"))
            except discord.Forbidden:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "I don't have permission to send messages in DM's"),
                                  ephemeral=True)
                return

            time_parsed = parse(time)
            if time_parsed is None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "invalid_time_format"), ephemeral=True)
                return

            target_time = datetime.datetime.now() + datetime.timedelta(seconds=time_parsed)

            client['DMMessageCapsule'].insert_one({
                "UserID": str(ctx.author.id),
                "ChannelID": str(ctx.channel.id),
                "Message": message,
                "Time": datetime.datetime.now() + datetime.timedelta(seconds=time_parsed)
            })

            target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "reminder_scheduled", time=target_time_str),
                              ephemeral=True)
            await sent_msg.delete(delay=10)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @schedule_group.command(name="reminders", description="List all reminders")
    @dm_only()
    async def schedule_reminders(self, ctx: discord.ApplicationContext):
        """List all reminders"""
        try:
            reminders = client['DMMessageCapsule'].find({"UserID": str(ctx.author.id)}).to_list()

            if len(reminders) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "no_reminders"), ephemeral=True)
                return

            pages = []
            current_page = ""

            for i, reminder in enumerate(reminders):
                current_page += f"{i+1}. {reminder['Message']}\n"
                if i % 10 == 0:
                    pages.append(current_page)
                    current_page = ""

            if current_page != "":
                pages.append(current_page)

            if len(pages) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "no_reminders"), ephemeral=True)
                return

            paginator = Paginator(pages)
            await paginator.respond(ctx.interaction, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @schedule_group.command(name="collection", description="Schedule a collection message")
    @is_module_enabled("time_capsule")
    @guild_only()
    async def schedule_collection(self, ctx: discord.ApplicationContext, time: str, message: str):
        """Schedule a collection message"""
        try:
            if ctx.channel.type != discord.ChannelType.text:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "only_text_channels"), ephemeral=True)
                return

            time_parsed = parse(time)
            if time_parsed is None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "invalid_time_format"), ephemeral=True)
                return

            target_time = datetime.datetime.now() + datetime.timedelta(seconds=time_parsed)

            add = client['CollectionMessageCapsule'].insert_one({
                "UserID": str(ctx.author.id),
                "GuildID": str(ctx.guild.id),
                "ChannelID": str(ctx.channel.id),
                "Message": message,
                "Time": target_time,
                "Replies": []
            })

            target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")

            channel: discord.TextChannel = ctx.channel

            sent_msg = await channel.send(f"**Collection**: {message}", view=AddYoursView())

            client['CollectionMessageCapsule'].update_one({"_id": add.inserted_id}, {"$set": {"MessageID": str(sent_msg.id)}})

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "collection_scheduled", time=target_time_str),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_dm_messages(self):
        for i in client['DMMessageCapsule'].find({"Time": {"$lt": datetime.datetime.now()}}).to_list():
            try:
                user = self.bot.get_user(int(i["UserID"]))
                if user is None:
                    client['DMMessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                await user.send(f'Reminder: {i["Message"]}')
                client['DMMessageCapsule'].delete_one({"_id": i["_id"]})
            except Exception as e:
                akabot_logger.exception("An error occured:")

    @tasks.loop(minutes=1)
    async def check_guild_messages(self):
        for i in client['MessageCapsule'].find({"Time": {"$lt": datetime.datetime.now()}}).to_list():
            try:
                guild = self.bot.get_guild(int(i["GuildID"]))
                if guild is None:
                    client['MessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                if not get_setting(guild.id, "module_time_capsule_enabled", True):
                    continue

                channel = guild.get_channel(int(i["ChannelID"]))
                if channel is None:
                    client['MessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                author = self.bot.get_user(int(i["UserID"]))
                if author is None:
                    client['MessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                # Add XP to user
                xp = int(get_setting(guild.id, 'leveling_initial_xp', 3))
                extra = int(get_setting(guild.id, 'leveling_extra_xp', 0))
                extra_trigger = int(get_setting(guild.id, 'leveling_extra_xp_trigger', 1))

                xp += extra * (len(i['Message']) // extra_trigger)

                add_xp(guild.id, author.id, xp)

                embed = discord.Embed(
                    author=discord.EmbedAuthor(
                        name=author.display_name,
                        icon_url=author.display_avatar.url
                    ),
                    description=i["Message"],
                    color=discord.Color.blurple()
                )

                await channel.send(embed=embed)
                client['MessageCapsule'].delete_one({"_id": i["_id"]})
            except Exception as e:
                akabot_logger.exception("An error occured:")

    @tasks.loop(minutes=1)
    async def check_collection_messages(self):
        for i in client['CollectionMessageCapsule'].find({"Time": {"$lt": datetime.datetime.now()}}).to_list():
            try:
                guild = self.bot.get_guild(int(i["GuildID"]))
                if guild is None:
                    client['CollectionMessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                if not get_setting(guild.id, "module_time_capsule_enabled", True):
                    continue

                channel: discord.TextChannel = self.bot.get_channel(int(i["ChannelID"]))
                if channel is None:
                    client['CollectionMessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                author = self.bot.get_user(int(i["UserID"]))
                if author is None:
                    client['CollectionMessageCapsule'].delete_one({"_id": i["_id"]})
                    continue

                responses = "# Collection expired!:\n"

                for j in i["Replies"]:
                    member = self.bot.get_user(int(j["UserID"]))
                    if member is None:
                        responses += f"{j['UserID']}: {j['Message']}\n"
                    else:
                        responses += f"{member.display_name}: {j['Message']}\n"

                    # Add XP to user
                    xp = int(get_setting(guild.id, 'leveling_initial_xp', 3))
                    extra = int(get_setting(guild.id, 'leveling_extra_xp', 0))
                    extra_trigger = int(get_setting(guild.id, 'leveling_extra_xp_trigger', 1))

                    xp += extra * (len(j['Message']) // extra_trigger)

                    add_xp(guild.id, author.id, xp)

                if len(responses) > 2000:
                    await channel.send("**Collection**:", files=[discord.File(fp=io.BytesIO(responses.encode()), filename="collection.txt")])
                else:
                    await channel.send(responses)

                client['CollectionMessageCapsule'].delete_one({"_id": i["_id"]})
            except Exception as e:
                akabot_logger.exception("An error occured:")
