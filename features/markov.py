import datetime

import discord
from markovify import NewlineText
import sentry_sdk

from discord.ext import commands

from database import client


class MarkovBot(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    async def generate_markov_post(self, channel: discord.TextChannel):
        try:
            data = client['MarkovChannel'].find_one({
                'ChannelID': str(channel.id)
            })

            if data is None:
                return

            client['MarkovChannel'].update_one({
                'ChannelID': str(channel.id)
            }, {
                '$inc': {
                    'MessageCount': 1
                }
            })

            if data['MessageCount'] < 10:
                return

            if (datetime.datetime.now() - data['LastSend']).total_seconds() < 60:
                return

            chain_data = []

            async for i in channel.history(limit=data['Messages']):
                if i.author.bot:
                    continue

                if len(i.content.strip()) > 0:
                    chain_data.append(i.content)

                if len(i.embeds) > 0:
                    for embed in i.embeds:
                        if embed.title is not None and len(embed.title.strip()) > 0:
                            chain_data.append(embed.title)
                        if embed.description is not None and len(embed.description.strip()) > 0:
                            chain_data.append(embed.description)

                        for field in embed.fields:
                            if field.name is not None and len(field.name.strip()) > 0:
                                chain_data.append(field.name)
                            if field.value is not None and len(field.value.strip()) > 0:
                                chain_data.append(field.value)

                for attachment in i.attachments:
                    if attachment.description is not None and len(attachment.description.strip()) > 0:
                        chain_data.append(attachment.description)

            model = NewlineText('\n'.join(chain_data))

            a = model.make_sentence(test_output=False, tries=500)

            if a is None:
                return

            await channel.send(a)

            # client['MarkovChannel'].update_one({
            #     'ChannelID': str(channel.id)
            # }, {
            #     '$set': {
            #         'MessageCount': 0,
            #         'LastSend': datetime.datetime.now()
            #     }
            # })
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return

            await self.generate_markov_post(message.channel)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    markov_commands = discord.SlashCommandGroup(name="markov")

    @markov_commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @discord.default_permissions(manage_guild=True)
    async def add_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, messages: int = 100):
        try:
            data = client['MarkovChannel'].find_one({
                'ChannelID': str(channel.id)
            })

            if data is not None:
                await ctx.respond("Channel has markov posts already enabled", ephemeral=True)
                return

            client['MarkovChannel'].insert_one({
                'ChannelID': str(channel.id),
                'MessageCount': 0,
                'LastSend': datetime.datetime.now() - datetime.timedelta(minutes=60),
                'Messages': messages
            })

            await ctx.respond("Enabled generation of Markov posts, send 10 messages for the first one to generate", ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond("An error occurred", ephemeral=True)

    @markov_commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @discord.default_permissions(manage_guild=True)
    async def remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            data = client['MarkovChannel'].find_one({
                'ChannelID': str(channel.id)
            })

            if data is None:
                await ctx.respond("Channel has markov posts already disabled", ephemeral=True)
                return

            client['MarkovChannel'].delete_one({
                'ChannelID': str(channel.id)
            })

            await ctx.respond("Disabled generation of Markov posts", ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond("An error occurred", ephemeral=True)

