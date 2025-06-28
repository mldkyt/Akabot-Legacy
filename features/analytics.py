
import datetime
import discord
from database import get_client


class Analytics(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot
        
    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        client = get_client()

        await client['AnalyticsActiveUsers'].update_one({
            'UserID': str(msg.author.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
        await client['AnalyticsActiveChannels'].update_one({
            'ChannelID': str(msg.channel.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)

        await client.client.close()
        
    @discord.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        client = get_client()

        await client['AnalyticsActiveUsers'].update_one({
            'UserID': str(user.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
        await client['AnalyticsActiveChannels'].update_one({
            'ChannelID': str(reaction.message.channel.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
