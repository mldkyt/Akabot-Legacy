import asyncio
import re

import discord

from database import client
from utils.denylist import akabot_logger
from utils.languages import get_translation_for_key_localized as trl


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
            if message.author.bot:
                return

            client["Counting"].update_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)},
                                          {'$inc': {'Count': 1}})

            data = client["Counting"].find_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)})

            if data is None:
                return

            if re.match("^[0-9]+$", message.content.strip()) is None:
                await self.handle_fail(message, data)
                return

            if (data["Count"] - 1) != int(message.content.strip()):
                await self.handle_fail(message, data)
                return

            if data["LastMember"] == str(message.author.id):
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
                await webhook.send(content=str(data['Count'] - 1), username=message.author.display_name,
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
