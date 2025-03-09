
import datetime
import discord
from database import client


class Analytics(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot
        
    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        client['AnalyticsActiveUsers'].update_one({
            'UserID': str(msg.author.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
        client['AnalyticsActiveChannels'].update_one({
            'ChannelID': str(msg.channel.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
        
    @discord.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        client['AnalyticsActiveUsers'].update_one({
            'UserID': str(user.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
        client['AnalyticsActiveChannels'].update_one({
            'ChannelID': str(reaction.message.channel.id)
        }, {
            '$set': {
                'LastUseTime': datetime.datetime.now()
            }
        }, upsert=True)
