
import datetime
import logging
import discord
from database import client
from discord.ext import tasks

akabot_logger = logging.getLogger("akabot")

class StickyMessage(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot
        self.processing_channels = []

    @discord.Cog.listener()
    async def on_ready(self):
        self.check_sticky_message.start()

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        try:
            if message.channel.id in self.processing_channels:
                logging.debug("Channel is already processing")
                return

            logging.debug("Starting processing of channel %s", str(message.channel.id))
            self.processing_channels.append(message.channel.id)

            await self.move_message_down(message.channel)
        except Exception as e:
            akabot_logger.exception("An error occured:")
        finally:
            logging.debug("Finishing processing of channel %s", str(message.channel.id))
            self.processing_channels.remove(message.channel.id)
        
    sticky_message_group = discord.SlashCommandGroup(name="sticky_message", description="Sticky message commands")

    @sticky_message_group.command(name="set", description="Set sticky message")
    async def add_sticky_message(self, ctx: discord.ApplicationContext, message: str):
        try:
            client['StickyMessages'].update_one({
                'ChannelID': str(ctx.channel.id),
            }, {
                '$set': {
                    'Message': message
                }
            }, upsert=True)

            await self.move_message_down(ctx.channel)

            await ctx.respond(f"Sticky message set", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Failed to set sticky message", ephemeral=True)

    @sticky_message_group.command(name="remove", description="Remove sticky message")
    async def remove_sticky_message(self, ctx: discord.ApplicationContext):
        try:
            existing_settings = client['StickyMessages'].find_one({
                'ChannelID': str(ctx.channel.id)
            })
            if not existing_settings:
                await ctx.respond("No sticky message set", ephemeral=True)
                return
            
            if 'ExistingMessageID' in existing_settings:
                existing_message = await ctx.channel.fetch_message(int(existing_settings['ExistingMessageID']))
                if existing_message:
                    await existing_message.delete()

            client['StickyMessages'].delete_one({
                'ChannelID': str(ctx.channel.id)
            })
            await ctx.respond(f"Sticky message removed", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Failed to remove sticky message", ephemeral=True)

    async def move_message_down(self, channel: discord.TextChannel):
        try:
            existing_settings = client['StickyMessages'].find_one({
                'ChannelID': str(channel.id)
            })
            if existing_settings is None:
                return

            if 'NextSendDate' in existing_settings:
                if datetime.datetime.fromisoformat(existing_settings['NextSendDate']).replace(tzinfo=datetime.timezone.utc) > datetime.datetime.now(datetime.timezone.utc):
                    logging.debug("Too soon to send another sticky message")
                    client['StickyMessages'].update_one({
                        'ChannelID': str(channel.id),
                    }, {
                        '$set': {
                            'NewMessage': True
                        }
                    })
                    return

            if 'ExistingMessageID' in existing_settings:
                existing_message = await channel.fetch_message(int(existing_settings['ExistingMessageID']))
                if existing_message:
                    await existing_message.delete()

            new_message = await channel.send(existing_settings['Message'])

            client['StickyMessages'].update_one({
                'ChannelID': str(channel.id),
            }, {
                '$set': {
                    'ExistingMessageID': str(new_message.id),
                    'NextSendDate': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)).isoformat(),
                    'NewMessage': False
                }
            }, upsert=True)

        except Exception as e:
            akabot_logger.exception("An error occured:")

    @tasks.loop(seconds=5)
    async def check_sticky_message(self):
        for i in client['StickyMessages'].find({
            'NewMessage': True
        }):
            try:
                channel = self.bot.get_channel(int(i['ChannelID']))
                if channel is None:
                    continue

                logging.debug('Handling channel #%s', str(channel.name))

                if channel.type != discord.ChannelType.text or channel.type == discord.ChannelType.private:
                    continue

                logging.debug("Found message")
                await self.move_message_down(channel)
                logging.debug("Message moved down")
            except Exception as e:
                akabot_logger.exception("An error occured:")
