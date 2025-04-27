import datetime
import random
import string

import discord
import sentry_sdk
from discord.ext import tasks

from database import client
from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl


def generate_code():
    a = string.ascii_letters + string.digits
    return ''.join(random.choices(a, k=8))


class WebUI(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.handle_update_channels.start()
        self.handle_update_emojis.start()

    @discord.slash_command(name="settings", description="NEW! Get a link to the web UI configuration!")
    @analytics("webui")
    @blocklist()
    async def webui(self, ctx: discord.ApplicationContext):
        try:
            # Try get existing code
            x = client['WebUICodes'].find_one({
                'GuildID': str(ctx.guild.id),
                'Expiry': {
                    '$gt': datetime.datetime.now(datetime.timezone.utc)
                }
            })

            if x is not None:
                await ctx.respond(f"{get_key('WEBUI_DOMAIN', 'http://localhost')}/{x['Code']}", ephemeral=True)
                return

            code = generate_code()

            # Create new code
            client['WebUICodes'].insert_one({
                'GuildID': str(ctx.guild.id),
                'Expiry': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
                'Code': code
            })

            await ctx.respond(f"{get_key('WEBUI_DOMAIN', 'http://localhost')}/{code}", ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tasks.loop(minutes=5)
    async def handle_update_channels(self):
        print('Handle update channels')
        for i in self.bot.guilds:
            for j in i.channels:
                if j.type not in [discord.ChannelType.voice, discord.ChannelType.stage_voice, discord.ChannelType.text,
                                  discord.ChannelType.news]:
                    continue

                print(f'Upserting #{j.name} from {i.name}')
                client['WebUIChannels'].update_one({
                    'GuildID': str(i.id),
                    'ChannelID': str(j.id),
                }, {
                    '$set': {
                        'ChannelName': j.name,
                        'ChannelType': str(j.type),
                    }
                }, upsert=True)

    @tasks.loop(minutes=5)
    async def handle_update_emojis(self):
        print('Handle update emojis')
        for i in self.bot.guilds:
            for j in i.emojis:
                print(f'Upserting {j.name} from {i.name}')
                client['WebUIEmojis'].update_one({
                    'GuildID': str(i.id),
                    'ID': str(j.id),
                }, {
                    '$set': {
                        'Emoji': j.name,
                        'URL': j.url
                    }
                }, upsert=True)
