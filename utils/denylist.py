import logging

import discord
from discord.ui import View

from database import client

akabot_logger = logging.getLogger("akabot")


class DenylistViewDB:
    def __init__(self):
        self.list = []

    def register_view(self, view: View):
        x = [i for i in self.list if type(view).__name__ == i['name']]
        if len(x) > 0:
            akabot_logger.warning("Re-registering view %s in DenylistViewDB", x[0]['name'])
            return

        self.list.append({
            'name': type(view).__name__,
            'view': view
        })

    def get_view(self, view: View | str | None) -> View | None:
        if view is None:
            return None
        if isinstance(view, str):
            x = [i for i in self.list if view == i["name"]]
        else:
            x = [i for i in self.list if type(view).__name__ == i["name"]]
        return x[0]["view"] if len(x) > 0 else None


denylist_view_db = DenylistViewDB()

def add_channel_to_denylist(channel_id: int):
    if client['Denylisted'].count_documents({'ChannelID': str(channel_id)}) > 0:
        return

    client['Denylisted'].insert_one({'ChannelID': str(channel_id)})

def remove_channel_from_denylist(channel_id: int):
    if client['Denylisted'].count_documents({'ChannelID': str(channel_id)}) == 0:
        return

    client['Denylisted'].delete_one({'ChannelID': str(channel_id)})

def is_denylisted(channel_id: int):
    return client['Denylisted'].count_documents({'ChannelID': str(channel_id)}) > 0

# Sending queue

async def queue_send_message(message: discord.Message, content: str | None = None,
                             embeds: list[discord.Embed] | None = None, delete_after: int = 0,
                             reply_to_message: bool = True, view: View | None = None):
    try:
        # Check if the channel is NOT in the denylist
        if not is_denylisted(message.channel.id):
            if reply_to_message:
                sent_msg = await message.reply(content=content, embeds=embeds, view=view)
            else:
                sent_msg = await message.channel.send(content=content, embeds=embeds, view=view)

            if delete_after != 0:
                await sent_msg.delete(delay=delete_after)
            return

        # Add the content to the queue
        add_to_queue(message.author, message.guild, content, embeds, delete_after, reply_to_message,
                     type(view).__name__)
    except Exception as e:
        akabot_logger.exception("An error occured:")

def add_to_queue(user: discord.User | discord.Member, guild: discord.Guild, content: str | None = None, embeds: list[discord.Embed] | None = None, delete_after: int = 0,
                 reply_to_message: bool = True, view: View | None = None):
    try:
        # Add the content to the queue
        client['DenylistMessageQueue'].insert_one({
            'MemberID': str(user.id),
            'GuildID': str(guild.id),
            'Message': content or '',
            'Embeds': [{
                'Title': embed.title,
                'Description': embed.description,
                'Author': {
                    'Name': embed.author.name,
                    'URL': embed.author.url,
                    'IconURL': embed.author.icon_url
                } if embed.author else None,
                'Fields': [{
                    'Name': i.name,
                    'Value': i.value,
                    'Inline': i.inline
                } for i in embed.fields],
                'Footer': {
                    'Text': embed.footer.text,
                    'IconURL': embed.footer.icon_url
                } if embed.footer else None
            } for embed in (embeds or [])],
            'DeleteAfter': delete_after,
            'ReplyToMessage': reply_to_message,
            'View': view
        })
    except Exception as e:
        akabot_logger.exception("An error occured:")
