import discord
import sentry_sdk

from database import client
from utils.denylist import is_denylisted, add_channel_to_denylist, remove_channel_from_denylist
from utils.languages import get_translation_for_key_localized as trl


class ChannelDenylist(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    denylist_subcommand = discord.SlashCommandGroup("denylist", "Set up a denylist of channels where Akabot won't send messages.")

    @denylist_subcommand.command(name="add", description="Add a channel to denylist.")
    async def add_to_denylist(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            if is_denylisted(channel.id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "denylist_already_added").format(mention=channel.mention), ephemeral=True)
                return

            add_channel_to_denylist(channel.id)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "denylist_added").format(mention=channel.mention), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @denylist_subcommand.command(name="remove", description="Remove a channel from the denylist.")
    async def remove_to_denylist(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            if not is_denylisted(channel.id):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "denylist_already_removed").format(mention=channel.mention), ephemeral=True)
                return

            remove_channel_from_denylist(channel.id)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "denylist_removed").format(mention=channel.mention), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try:
            if msg.author.bot:
                return
            if msg.guild is None:
                return
            if is_denylisted(msg.channel.id):
                return

            # Send messages waiting in queue
            messages = client['DenylistMessageQueue'].find({
                'GuildID': str(msg.guild.id),
                'MemberID': str(msg.author.id)
            })

            for data_msg in messages:
                # Construct embeds
                embeds = []
                for i in data_msg['Embeds']:
                    # Check if the embed author was set
                    embed_author = None
                    if 'Author' in i and i['Author'] is not None:
                        embed_author = discord.EmbedAuthor(
                            name=i['Author']['Name'],
                            url=i['Author']['URL'],
                            icon_url=i['Author']['IconURL']
                        )

                    # Check if the embed footer was set
                    embed_footer = None
                    if 'Footer' in i and i['Footer'] is not None:
                        embed_footer = discord.EmbedFooter(
                            text=i['Footer']['Text'],
                            icon_url=i['Footer']['IconURL']
                        )

                    # Check if any fields are present
                    fields = []
                    for j in i['Fields']:
                        fields.append(discord.EmbedField(
                            name=j['Name'],
                            value=j['Value'],
                            inline=j['Inline']
                        ))

                    # Append constructed embed
                    embeds.append(discord.Embed(
                        title=i['Title'],
                        description=i['Description'],
                        author=embed_author,
                        fields=fields,
                        footer=embed_footer
                    ))

                # Reply to the user in the different channel
                if data_msg['ReplyToMessage']:
                    sent_message = await msg.reply(content=data_msg['Message'], embeds=embeds)
                else:
                    sent_message = await msg.channel.send(content=data_msg['Message'], embeds=embeds)

                # Remove from database
                client['DenylistMessageQueue'].delete_one({
                    '_id': data_msg['_id']
                })

                # If delete is set, delete after interval
                if data_msg['DeleteAfter'] > 0:
                    await sent_message.delete(delay=data_msg['DeleteAfter'])
        except Exception as e:
            sentry_sdk.capture_exception(e)
