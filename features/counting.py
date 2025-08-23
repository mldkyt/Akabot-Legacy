import asyncio
import re

import discord

from database import client
from utils.denylist import akabot_logger
from utils.languages import get_translation_for_key_localized as trl
from utils.per_server_settings import get_setting, set_setting


def attempt_to_parse_number(guild_id: int, text: str) -> list[int]:
    if not get_setting(guild_id, "counting_any_count", False):
        if not text.isnumeric():
            return []

        return [int(text)]

    numbers_in_message = []

    # Simple number parsing first
    for i in re.finditer(r'([0-9]+)', text):
        numbers_in_message.append(int(i.groups()[0]))

    # Count of words
    if get_setting(guild_id, "counting_words", False):
        numbers_in_message.append(len(text.split(" ")))

    if get_setting(guild_id, "counting_word_frequency", False):
        # Count of words that repeat
        words = {}
        for i in text.split(" "):
            if not i in words:
                words[i] = 0
            words[i] += 1

        a = get_setting(guild_id, "counting_word_frequency_minimal", 2)
        for k in words.keys():
            if words[k] < a:
                del words[k]

        words = {k: v for k, v in sorted(words.items(), key=lambda x: x[1], reverse=True)}
        numbers_in_message.extend([i for i in words.values()])

    return numbers_in_message


class Counting(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    async def handle_fail(self, message: discord.Message, data: dict):
        try:
            await message.add_reaction("❌")
            if data['Count'] > 2:
                await message.reply(
                    trl(0, message.guild.id, "counting_failed", user=message.author.mention,
                                                                       count=str(data["Count"] - 1)))

            client["Counting"].update_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id), },
                                          {'$set': {'Count': 1, 'LastMember': '0'}})
        except Exception as e:
            akabot_logger.exception("An error occured:")

    async def fetch_counting_channel(self, guild_id: str, channel_id: str):
        try:
            guild = await self.bot.fetch_guild(int(guild_id))
            if guild is None:
                return

            channel = await guild.fetch_channel(int(channel_id))
            if channel is None:
                return

            await channel.history(limit=100).flatten()
        except Exception as e:
            akabot_logger.exception("An error occured:")

    @discord.Cog.listener()
    async def on_ready(self):
        try:
            tasks = []

            for i in client["Counting"].find():
                tasks.append(asyncio.create_task(self.fetch_counting_channel(i["GuildID"], i["ChannelID"])))

            await asyncio.gather(*tasks)
        except Exception as e:
            akabot_logger.exception("An error occured:")

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):

        try:
            if message.guild is None or message.channel is None:
                return
            if message.author.bot:
                return
            if isinstance(message.channel, discord.DMChannel) or isinstance(message.channel, discord.GroupChannel) or \
                isinstance(message.channel, discord.PartialMessageable) or isinstance(message.channel, discord.Thread):
                return

            client["Counting"].update_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)},
                                          {'$inc': {'Count': 1}})

            data = client["Counting"].find_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)})

            if data is None:
                return

            if data["LastMember"] == str(message.author.id):
                await self.handle_fail(message, data)
                return

            if not any([i == (data['Count'] - 1) for i in attempt_to_parse_number(message.guild.id, message.content)]):
                await self.handle_fail(message, data)
                return

            if message.guild.me.guild_permissions.manage_webhooks and \
                    message.channel.permissions_for(message.guild.me).manage_webhooks:
                # Use a webhook to create the "profile" of the user

                # Get the first webhook or create one if neccessary
                webhooks = await message.channel.webhooks()
                if len(webhooks) > 0:
                    webhook = webhooks[0]
                else:
                    webhook = await message.channel.create_webhook(name="Counting Webhook",
                                                                   reason="Webhook for counting messages. Created automatically.")

                # Send message using webhook
                await webhook.send(content=message.content, username=message.author.display_name,
                                   avatar_url=message.author.display_avatar.url)

                # Delete the message
                await message.delete()
            else:
                await message.add_reaction('✅')

            client["Counting"].update_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)},
                                          {'$set': {'LastMember': str(message.author.id)}})
        except Exception as e:
            akabot_logger.exception("An error occured:")

    @discord.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        try:
            if after.author.bot:
                return

            data = client["Counting"].find_one({'GuildID': str(after.guild.id), 'ChannelID': str(after.channel.id)})

            if data is None:
                return

            await self.handle_fail(after, data)
        except Exception as e:
            akabot_logger.exception("An error occured:")

    counting = discord.SlashCommandGroup(name="counting_channels", description="Configuration for counting channels")

    @counting.command(name="add_channel", description="Add a channel to counting channels")
    async def add_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            existing = client["Counting"].find_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})

            if existing is not None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_already_added"), ephemeral=True)
                return

            client["Counting"].insert_one(
                {'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id), 'Count': 1, 'LastMember': '0'})

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_added", append_tip=True), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @counting.command(name="remove_channel", description="Remove a channel from counting channels")
    async def remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            existing = client["Counting"].find_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})

            if existing is None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_not_found"), ephemeral=True)
                return

            client["Counting"].delete_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_removed"), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @counting.command(name="any_count_settings", description="Set any count settings")
    @discord.option(name="any_count", description="Enable any counting mode", type=bool)
    @discord.option(name="count_words", description="The total count of words is a number", type=bool)
    @discord.option(name="count_words_frequency", description="Count the occurrences of each word", type=bool)
    @discord.option(name="words_frequency_minimal", description="Minimum occurrences needed for each word", type=int)
    async def any_count_settings(self, ctx: discord.ApplicationContext, any_count: bool | None = None,
                                 count_words: bool | None = None,
                                 count_words_frequency: bool | None = None, words_frequency_minimal: int | None = None):

        if words_frequency_minimal is not None:
            if 1 > words_frequency_minimal or words_frequency_minimal > 10:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "any_count_invalid_min_count_frequency"), ephemeral=True)
                return

        if any_count is not None:
            set_setting(ctx.guild.id, "counting_any_count", any_count)
        if count_words is not None:
            set_setting(ctx.guild.id, "counting_words", count_words)
        if count_words_frequency is not None:
            set_setting(ctx.guild.id, "counting_word_frequency", count_words_frequency)
        if words_frequency_minimal is not None:
            set_setting(ctx.guild.id, "counting_word_frequency_minimal", words_frequency_minimal)
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "any_count_saved"), ephemeral=True)
