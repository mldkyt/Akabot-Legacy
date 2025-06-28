import asyncio
import logging
import re

import discord
import sentry_sdk

from database import get_client
from utils.languages import get_translation_for_key_localized as trl


class Counting(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    async def handle_fail(self, message: discord.Message, data: dict):
        await message.add_reaction("❌")
        if data['Count'] > 2:
            await message.reply(
                (await trl(0, message.guild.id, "counting_failed")).format(user=message.author.mention, count=str(data["Count"] - 1)))

        client = get_client()
        await client["Counting"].update_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id), },
                                      {'$set': {'Count': 1, 'LastMember': '0'}})
        await client.client.close()

    async def fetch_counting_channel(self, guild_id: str, channel_id: str):
        guild = await self.bot.fetch_guild(int(guild_id))
        if guild is None:
            return

        channel = await guild.fetch_channel(int(channel_id))
        if channel is None:
            return

        await channel.history(limit=100).flatten()

    @discord.Cog.listener()
    async def on_ready(self):
        tasks = []

        client = get_client()
        for i in client["Counting"].find():
            tasks.append(asyncio.create_task(self.fetch_counting_channel(i["GuildID"], i["ChannelID"])))

        await client.client.close()

        logging.info("Gathering %s tasks", str(len(tasks)))
        await asyncio.gather(*tasks)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):

        try:
            if message.author.bot:
                return

            client = get_client()
            client["Counting"].update_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)},
                                          {'$inc': {'Count': 1}})

            data = client["Counting"].find_one({'GuildID': str(message.guild.id), 'ChannelID': str(message.channel.id)})

            if data is None:
                await client.client.close()
                return

            if re.match("^[0-9]+$", message.content.strip()) is None:
                await self.handle_fail(message, data)
                await client.client.close()
                return

            if (data["Count"] - 1) != int(message.content.strip()):
                await self.handle_fail(message, data)
                await client.client.close()
                return

            if data["LastMember"] == str(message.author.id):
                await self.handle_fail(message, data)
                await client.client.close()
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
            await client.client.close()
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot:
            return

        client = get_client()
        data = client["Counting"].find_one({'GuildID': str(after.guild.id), 'ChannelID': str(after.channel.id)})
        await client.client.close()

        if data is None:
            return

        await self.handle_fail(after, data)

    counting = discord.SlashCommandGroup(name="counting_channels", description="Configuration for counting channels")

    @counting.command(name="add_channel", description="Add a channel to counting channels")
    async def add_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            client = get_client()
            existing = client["Counting"].find_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})

            if existing is not None:
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "counting_channel_already_added"), ephemeral=True)
                await client.client.close()
                return

            client["Counting"].insert_one(
                {'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id), 'Count': 1, 'LastMember': '0'})

            await client.client.close()
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_added", append_tip=True), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @counting.command(name="remove_channel", description="Remove a channel from counting channels")
    async def remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            client = get_client()
            existing = await client["Counting"].find_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})

            if existing is None:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_not_found"), ephemeral=True)
                await client.client.close()
                return

            await client["Counting"].delete_one({'GuildID': str(channel.guild.id), 'ChannelID': str(channel.id)})

            await client.client.close()
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "counting_channel_removed"), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
