import discord
import sentry_sdk

from database import get_client

async def add_channel_to_denylist(channel_id: int):
    client = get_client()
    if await client['Denylisted'].count_documents({'ChannelID': str(channel_id)}) > 0:
        return

    await client['Denylisted'].insert_one({'ChannelID': str(channel_id)})

async def remove_channel_from_denylist(channel_id: int):
    client = get_client()
    if await client['Denylisted'].count_documents({'ChannelID': str(channel_id)}) == 0:
        return

    await client['Denylisted'].delete_one({'ChannelID': str(channel_id)})

async def is_denylisted(channel_id: int):
    client = get_client()
    a = await client['Denylisted'].count_documents({'ChannelID': str(channel_id)}) > 0
    await client.client.close()
    return a

# Sending queue

async def queue_send_message(message: discord.Message, content: str | None = None, embeds: list[discord.Embed] | None = None, delete_after: int = 0):
    try:
        # Check if the channel is NOT in the denylist
        if not await is_denylisted(message.channel.id):
            sent_msg = await message.reply(content=content, embeds=embeds)
            if delete_after != 0:
                await sent_msg.delete(delay=delete_after)
            return

        # Add the content to the queue
        await add_to_queue(message.author, message.guild, content, embeds, delete_after)
    except Exception as e:
        sentry_sdk.capture_exception(e)

async def add_to_queue(user: discord.User | discord.Member, guild: discord.Guild, content: str | None = None, embeds: list[discord.Embed] | None = None, delete_after: int = 0):
    try:
        client = get_client()
        # Add the content to the queue
        await client['DenylistMessageQueue'].insert_one({
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
            'DeleteAfter': delete_after
        })
        await client.client.close()
    except Exception as e:
        sentry_sdk.capture_exception(e)
