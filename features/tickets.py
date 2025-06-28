#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 lunya.pet
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#


import logging
import discord
import sentry_sdk
from discord.ext import commands, tasks

from database import get_client
from utils.languages import get_translation_for_key_localized as trl
from utils.logging_util import log_into_logs
from utils.settings import set_setting, get_setting
from utils.tzutil import get_now_for_server


async def db_add_ticket_channel(guild_id: int, ticket_category: int, user_id: int):
    client = get_client()
    await client['TicketChannels'].insert_one(
        {'GuildID': str(guild_id), 'TicketChannelID': str(ticket_category), 'UserID': str(user_id),
         'MTime': await get_now_for_server(guild_id), 'ATime': 'None'})


async def db_is_ticket_channel(guild_id: int, ticket_channel_id: int):
    client = get_client()
    count = await client['TicketChannels'].count_documents(
        {'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)})
    return count > 0


async def db_get_ticket_creator(guild_id: int, ticket_channel_id: int) -> int:
    client = get_client()
    user_id = await client['TicketChannels'].find_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)})[
        'UserID']
    return int(user_id)


async def db_remove_ticket_channel(guild_id: int, ticket_channel_id: int):
    client = get_client()
    await client['TicketChannels'].delete_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)})


async def db_update_mtime(guild_id: int, ticket_channel_id: int):
    client = get_client()
    await client['TicketChannels'].update_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)},
                                        {'$set': {'MTime': await get_now_for_server(guild_id)}})


async def check_ticket_archive_time(guild_id: int, ticket_channel_id: int) -> bool:
    archive_time = await get_setting(guild_id, "ticket_archive_time", "0")  # hours
    if archive_time == "0":
        return False

    client = get_client()

    mtime = await client['TicketChannels'].find_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)})[
        'MTime']

    if mtime is None:
        return False

    if ((await get_now_for_server(guild_id)) - mtime).total_seconds() / 3600 >= int(archive_time):
        return True

    return False


async def db_is_archived(guild_id: int, ticket_channel_id: int) -> bool:
    client = get_client()
    atime = await client['TicketChannels'].find_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)})[
        'ATime']
    return atime != "None"


async def check_ticket_hide_time(guild_id: int, ticket_channel_id: int) -> bool:
    if not await db_is_archived(guild_id, ticket_channel_id):
        return False

    hide_time = await get_setting(guild_id, "ticket_hide_time", "0")  # hours, hide time from archive
    if hide_time == "0":
        return False

    client = get_client()
    atime = await client['TicketChannels'].find_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)})[
        'ATime']

    if atime == 'None':
        return False

    if ((await get_now_for_server(guild_id)) - atime).total_seconds() / 3600 >= int(hide_time):
        return True

    return False


async def db_archive_ticket(guild_id: int, ticket_channel_id: int):
    client = get_client()
    await client['TicketChannels'].update_one({'GuildID': str(guild_id), 'TicketChannelID': str(ticket_channel_id)},
                                        {'$set': {'ATime': await get_now_for_server(guild_id)}})


async def db_list_archived_tickets():
    """
    Get all archived tickets.
    :return: List of tuples with guild_id and ticket_channel_id.
    """
    client = get_client()
    tickets = await client['TicketChannels'].find({'ATime': {'$not': {'$eq': 'None'}}}).to_list()
    return tickets


async def db_list_not_archived_tickets():
    """
    Get all not archived tickets.
    :return: List of tuples with guild_id and ticket_channel_id.
    """
    client = get_client()
    tickets = await client['TicketChannels'].find({'ATime': 'None'}).to_list()
    return tickets


class TicketMessageView(discord.ui.View):
    """View for the message sent on top of every ticket."""

    def __init__(self):
        super().__init__(timeout=None)


        self.close_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Close Ticket",
                                              custom_id="close_ticket")
        self.add_item(self.close_button)
        self.close_button.callback = self.close_ticket

    async def close_ticket(self, interaction: discord.Interaction):
        self.disable_all_items()
        if not await db_is_ticket_channel(interaction.guild.id, interaction.channel.id):
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        # Remove permissions from the ticket creator appropriately
        hide_time = await get_setting(interaction.guild.id, "ticket_hide_time", "0")
        logging.debug('[Tickets] Auto hide time is %s', str(hide_time))
        if int(hide_time) > 0:
            logging.debug('[Tickets] Taking away send permissions')
            member = interaction.guild.get_member(await db_get_ticket_creator(interaction.guild.id, interaction.channel.id))
            await interaction.channel.set_permissions(member, view_channel=True, read_messages=True,
                                                      send_messages=False)
            await db_archive_ticket(interaction.guild.id, interaction.channel.id)
        else:
            logging.debug('[Tickets] Taking away ALL permissions')
            member = interaction.guild.get_member(await db_get_ticket_creator(interaction.guild.id, interaction.channel.id))
            await interaction.channel.set_permissions(member, view_channel=False, read_messages=False,
                                                      send_messages=False)
            await db_remove_ticket_channel(interaction.guild.id, interaction.channel.id)


        await interaction.message.edit(view=self)


class TicketCreateView(discord.ui.View):
    def __init__(self, button_label: str):
        super().__init__(timeout=None)

        self.button = discord.ui.Button(style=discord.ButtonStyle.primary, label=button_label,
                                        custom_id="create_ticket")
        self.add_item(self.button)
        self.button.callback = self.create_ticket

    async def create_ticket(self, interaction: discord.Interaction):
        category = interaction.guild.get_channel(int(await get_setting(interaction.guild.id, "ticket_category", "0")))
        if category is None:
            await interaction.response.send_message(
                "A ticket category has to be set in order to create a ticket. Please ping the admins of the server to fix this.",
                ephemeral=True)
            return

        channel = await category.create_text_channel(f"ticket-{interaction.user.name}",
                                                     topic=f"Ticket for {interaction.user.display_name}",
                                                     reason="Ticket creation")

        # Set overwrite for the creator of the ticket, so they can see the channel and send messages
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        # Send initial message
        await channel.send(
            "Ticket created by " + interaction.user.mention + "\n\nYou can use the buttons below to manage the ticket.",
            view=TicketMessageView())

        await db_add_ticket_channel(interaction.guild.id, channel.id, interaction.user.id)

        await interaction.response.send_message("Ticket created! " + channel.mention, ephemeral=True)

        log_embed = discord.Embed(title="Ticket Created",
                                  description=f"Ticket created by {interaction.user.mention} in {channel.mention}")
        log_embed.add_field(name="Ticket ID", value=str(channel.id))
        log_embed.add_field(name="Ticket Creator", value=interaction.user.mention)
        log_embed.add_field(name="Ticket Channel", value=channel.mention)
        log_embed.add_field(name="Ticket Category", value=category.name)
        log_embed.add_field(name="Ticket Creation Time", value=(await get_now_for_server(interaction.guild.id)).isoformat())

        await log_into_logs(interaction.guild, log_embed)


class Tickets(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    tickets_commands = discord.SlashCommandGroup(name="tickets", description="Manage tickets")

    @discord.Cog.listener()
    async def on_ready(self):
        self.handle_hiding.start()
        self.handle_auto_archive.start()

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:

            if message.author.bot:
                return

            if message.channel.type == discord.ChannelType.private:
                return  # Do not try to update ticket information in DM's

            if not await db_is_ticket_channel(message.guild.id, message.channel.id):
                return

            if await db_is_archived(message.guild.id, message.channel.id):
                return

            await db_update_mtime(message.guild.id, message.channel.id)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        try:
            if after.author.bot:
                return

            if not await db_is_ticket_channel(after.guild.id, after.channel.id):
                return

            await db_update_mtime(after.guild.id, after.channel.id)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        try:
            if user.bot:
                return

            if not await db_is_ticket_channel(reaction.message.guild.id, reaction.message.channel.id):
                return

            if await db_is_archived(reaction.message.guild.id, reaction.message.channel.id):
                return

            await db_update_mtime(reaction.message.guild.id, reaction.message.channel.id)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @tickets_commands.command(name="send_message", description="Send a message that allows users to create a ticket")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def send_message(self, ctx: discord.ApplicationContext, message: str, button_label: str):
        try:
            if await get_setting(ctx.guild.id, "ticket_category", "0") == "0":
                await ctx.respond("Please set a ticket category first!", ephemeral=True)
                return

            if not ctx.guild.get_channel(int(await get_setting(ctx.guild.id, "ticket_category", "0"))):
                await ctx.respond("The ticket category has been deleted. Please set a new one.", ephemeral=True)
                return

            if not ctx.guild.me.guild_permissions.manage_channels or not ctx.guild.me.guild_permissions.manage_roles:
                await ctx.respond(
                    "I need the Manage Channels (to create channels) and Manage Roles (to set permissions on ticket "
                    "channels) permissions to create tickets.",
                    ephemeral=True)
                return

            await ctx.channel.send(message, view=TicketCreateView(button_label))
            await ctx.respond("Message sent!", ephemeral=True)

            log_embed = discord.Embed(title="Ticket Message Sent",
                                      description=f"Ticket message sent by {ctx.user.mention} in {ctx.channel.mention}")
            log_embed.add_field(name="Ticket Message", value=message)
            log_embed.add_field(name="Ticket Message Button Label", value=button_label)
            log_embed.add_field(name="Ticket Message Channel", value=ctx.channel.mention)
            log_embed.add_field(name="Ticket Message Time", value=(await get_now_for_server(ctx.guild.id)).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tickets_commands.command(name="set_category",
                              description="Set the category where tickets will be created. Permissions will be copied "
                                          "from this category.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def set_category(self, ctx: discord.ApplicationContext, category: discord.CategoryChannel):
        try:
            await set_setting(ctx.guild.id, "ticket_category", str(category.id))
            await ctx.respond("Category set!", ephemeral=True)

            log_embed = discord.Embed(title="Ticket Category Set",
                                      description=f"Ticket category set by {ctx.user.mention} to {category.name}")
            log_embed.add_field(name="Ticket Category", value=category.name)
            log_embed.add_field(name="Ticket Category ID", value=str(category.id))
            log_embed.add_field(name="Ticket Category Time", value=(await get_now_for_server(ctx.guild.id)).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tickets_commands.command(name="set_hide_time",
                              description="Set the time that the ticket will be available for the creator after it's "
                                          "archived.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def set_hide_time(self, ctx: discord.ApplicationContext, hours: int):
        try:
            await set_setting(ctx.guild.id, "ticket_hide_time", str(hours))
            await ctx.respond("Hide time set!", ephemeral=True)

            log_embed = discord.Embed(title="Ticket Hide Time Set",
                                      description=f"Ticket hide time set by {ctx.user.mention} to {hours} hours")
            log_embed.add_field(name="Ticket Hide Time", value=str(hours))
            log_embed.add_field(name="Ticket Hide Time Time", value=(await get_now_for_server(ctx.guild.id)).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tickets_commands.command(name="set_archive_time",
                              description="Set the time that the ticket will be archived after no activity.")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def set_auto_archive_time(self, ctx: discord.ApplicationContext, hours: int):
        try:
            await set_setting(ctx.guild.id, "ticket_archive_time", str(hours))
            await ctx.respond("Auto archive time set!", ephemeral=True)

            log_embed = discord.Embed(title="Ticket Archive Time Set",
                                      description=f"Ticket archive time set by {ctx.user.mention} to {hours} hours")
            log_embed.add_field(name="Ticket Archive Time", value=str(hours))
            log_embed.add_field(name="Ticket Archive Time Time", value=(await get_now_for_server(ctx.guild.id)).isoformat())

            await log_into_logs(ctx.guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @tasks.loop(seconds=60)
    async def handle_hiding(self):
        try:
            for i in await db_list_archived_tickets():
                guild = self.bot.get_guild(int(i['GuildID']))
                channel = guild.get_channel(int(i['TicketChannelID']))

                if guild is None or channel is None:
                    return  # Skip if the guild or channel is not found

                if await check_ticket_hide_time(i['GuildID'], i['TicketChannelID']):
                    member = guild.get_member(await db_get_ticket_creator(i['GuildID'], i['TicketChannelID']))
                    await channel.set_permissions(member, read_messages=False, send_messages=False)
                    await db_remove_ticket_channel(i['GuildID'], i['TicketChannelID'])

                    log_embed = discord.Embed(title="Ticket Hidden",
                                              description=f"Ticket hidden by the system in {channel.mention} because the hide time is up.")
                    log_embed.add_field(name="Ticket Hidden Time", value=(await get_now_for_server(guild.id)).isoformat())
                    log_embed.add_field(name="Ticket Hidden Message", value=channel.jump_url)

                    await log_into_logs(guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @tasks.loop(seconds=60)
    async def handle_auto_archive(self):
        try:
            # Ticket archiving after certain time of no changes
            for i in await db_list_not_archived_tickets():
                if await check_ticket_archive_time(i['GuildID'], i['TicketChannelID']):
                    await db_archive_ticket(i['GuildID'], i['TicketChannelID'])

                    guild = self.bot.get_guild(int(i['GuildID']))
                    channel = guild.get_channel(int(i['TicketChannelID']))

                    # Remove permissions from the ticket creator appropriately
                    atime = await get_setting(guild.id, "ticket_hide_time", "0")
                    if int(atime) > 0:
                        member = guild.get_member(
                            await db_get_ticket_creator(guild.id, channel.id))
                        await channel.set_permissions(member, view_channel=True, read_messages=True,
                                                      send_messages=False)
                        await db_archive_ticket(guild.id, channel.id)
                    else:
                        member = guild.get_member(
                            await db_get_ticket_creator(guild.id, channel.id))
                        await channel.set_permissions(member, view_channel=False, read_messages=False,
                                                      send_messages=False)
                        await db_remove_ticket_channel(guild.id, channel.id)

                    await channel.send(

                                        value=(await get_now_for_server(guild.id)).isoformat())

                    await log_into_logs(guild, log_embed)
        except Exception as e:
            sentry_sdk.capture_exception(e)
