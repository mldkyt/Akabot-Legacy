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
import datetime
import logging
import re

import discord
import sentry_sdk
from discord import Interaction, Embed, Color
from discord.ext import commands
from discord.ui import View, Modal, InputText

from database import client
from utils.languages import get_translation_for_key_localized as trl
from utils.module_toggling import is_module_enabled
from utils.settings import get_setting, set_setting


class V2NameChangeModal(Modal):
    def __init__(self, ch_id: int):
        super().__init__(timeout=120, title='Change Channel Name')
        self.ch_id = ch_id

        self.new_name_field = InputText(label='New Name', placeholder='New Name', min_length=2, max_length=16)
        self.add_item(self.new_name_field)

    async def callback(self, interaction: Interaction):
        try:
            if not get_setting(interaction.guild.id, "module_temporary_vc_enabled", True):
                await interaction.respond("The module temporary_vc is disabled", ephemeral=True)
                return

            new_name = self.new_name_field.value

            if not re.match(r"[a-zA-Z0-9-_]{1,16}", new_name):
                await interaction.respond("Name is invalid!", ephemeral=True)
                return 

            ch = interaction.guild.get_channel(self.ch_id)
            await ch.edit(name=new_name)
            await interaction.response.send_message('Name updated', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('An error occurred', ephemeral=True)
            sentry_sdk.capture_exception(e)


class V2MaxUsersChangeModal(Modal):
    def __init__(self, ch_id: int):
        super().__init__(timeout=120, title='Change Max Users')
        self.ch_id = ch_id

        self.new_max_users_field = InputText(label='New Max Users', placeholder='New Max Users', min_length=1,
                                             max_length=2)
        self.add_item(self.new_max_users_field)

    async def callback(self, interaction: Interaction):
        try:
            if not get_setting(interaction.guild.id, "module_temporary_vc_enabled", True):
                await interaction.respond("The module temporary_vc is disabled", ephemeral=True)
                return

            if not self.new_max_users_field.value.isdigit():
                await interaction.response.send_message('Max users must be a number', ephemeral=True)
                return

            if int(self.new_max_users_field.value) < 2:
                await interaction.response.send_message('Max users must be at least 2', ephemeral=True)
                return

            if int(self.new_max_users_field.value) > 99:
                await interaction.response.send_message('Max users must be at most 99', ephemeral=True)
                return

            new_max_users = int(self.new_max_users_field.value)
            ch = interaction.guild.get_channel(self.ch_id)
            await ch.edit(user_limit=new_max_users)
            await interaction.response.send_message('Max users updated', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('An error occurred', ephemeral=True)
            sentry_sdk.capture_exception(e)


class V2BitrateChangeModal(Modal):
    def __init__(self, ch_id: int):
        super().__init__(timeout=120, title='Change Bitrate')
        self.ch_id = ch_id

        self.new_bitrate_field = InputText(label='New Bitrate', placeholder='New Bitrate', min_length=1,
                                           max_length=2)
        self.add_item(self.new_bitrate_field)

    async def callback(self, interaction: Interaction):
        try:
            if not get_setting(interaction.guild.id, "module_temporary_vc_enabled", True):
                await interaction.respond("The module temporary_vc is disabled", ephemeral=True)
                return

            if not self.new_bitrate_field.value.isdigit():
                await interaction.response.send_message('Bitrate must be a number', ephemeral=True)
                return

            if int(self.new_bitrate_field.value) < 8:
                await interaction.response.send_message('Bitrate must be at least 8', ephemeral=True)
                return

            if int(self.new_bitrate_field.value) > 96:
                await interaction.response.send_message('Bitrate must be at most 96', ephemeral=True)
                return

            new_bitrate = int(self.new_bitrate_field.value) * 1000
            ch = interaction.guild.get_channel(self.ch_id)
            await ch.edit(bitrate=new_bitrate)
            await interaction.response.send_message('Bitrate updated', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('An error occurred', ephemeral=True)
            sentry_sdk.capture_exception(e)


class V2TemporaryVCMenu(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.last_vc_name_change = None

    @discord.ui.button(label='Change Name', style=discord.ButtonStyle.primary)
    async def change_name(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if not get_setting(interaction.guild.id, "module_temporary_vc_enabled", True):
                await interaction.respond("The module temporary_vc is disabled", ephemeral=True)
                return

            if self.last_vc_name_change is not None and (datetime.datetime.now(datetime.timezone.utc) - self.last_vc_name_change).total_seconds() < 30:
                await interaction.respond("Please slow down with renaming the voice channel", ephemeral=True)
                return

            self.last_vc_name_change = datetime.datetime.now(datetime.timezone.utc)

            data = client['TemporaryVC'].find_one(
                {'ChannelID': str(interaction.channel.id), 'GuildID': str(interaction.guild.id)})
            if not data:
                await interaction.response.send_message('This is not a temporary channel', ephemeral=True)
                return

            if data['CreatorID'] != str(interaction.user.id):
                await interaction.response.send_message('You are not the creator of this channel', ephemeral=True)
                return

            mod = V2NameChangeModal(interaction.channel.id)
            await interaction.response.send_modal(mod)
        except Exception as e:
            await interaction.response.send_message('An error occurred', ephemeral=True)
            sentry_sdk.capture_exception(e)

    @discord.ui.button(label='Change Max Users', style=discord.ButtonStyle.primary)
    async def change_max_users(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if not get_setting(interaction.guild.id, "module_temporary_vc_enabled", True):
                await interaction.respond("The module temporary_vc is disabled", ephemeral=True)
                return

            data = client['TemporaryVC'].find_one(
                {'ChannelID': str(interaction.channel.id), 'GuildID': str(interaction.guild.id)})
            if not data:
                await interaction.response.send_message('This is not a temporary channel', ephemeral=True)
                return

            if data['CreatorID'] != str(interaction.user.id):
                await interaction.response.send_message('You are not the creator of this channel', ephemeral=True)
                return

            mod = V2MaxUsersChangeModal(interaction.channel.id)
            await interaction.response.send_modal(mod)
        except Exception as e:
            await interaction.response.send_message('An error occurred', ephemeral=True)
            sentry_sdk.capture_exception(e)

    @discord.ui.button(label='Change Bitrate', style=discord.ButtonStyle.primary)
    async def change_bitrate(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if not get_setting(interaction.guild.id, "module_temporary_vc_enabled", True):
                await interaction.respond("The module temporary_vc is disabled", ephemeral=True)
                return

            data = client['TemporaryVC'].find_one(
                {'ChannelID': str(interaction.channel.id), 'GuildID': str(interaction.guild.id)})
            if not data:
                await interaction.response.send_message('This is not a temporary channel', ephemeral=True)
                return

            if data['CreatorID'] != str(interaction.user.id):
                await interaction.response.send_message('You are not the creator of this channel', ephemeral=True)
                return

            mod = V2BitrateChangeModal(interaction.channel.id)
            await interaction.response.send_modal(mod)
        except Exception as e:
            await interaction.response.send_message('An error occurred', ephemeral=True)
            sentry_sdk.capture_exception(e)


async def new_temporary_channel(from_ch: discord.VoiceChannel,
                                for_user: discord.Member) -> discord.VoiceChannel:
    category = from_ch.category

    new_ch_name = get_setting(for_user.guild.id, 'temporary_vc_name', '{name}\'s channel')

    new_ch_name = new_ch_name.replace('{name}', for_user.display_name)
    new_ch_name = new_ch_name.replace('{username}', for_user.name)
    new_ch_name = new_ch_name.replace('{guild}', for_user.guild.name)

    if not category:
        new_ch = await from_ch.guild.create_voice_channel(name=new_ch_name, reason=trl(0, for_user.guild.id,
                                                                                       'temporary_vc_mod_reason'),
                                                          bitrate=from_ch.bitrate, user_limit=from_ch.user_limit)
    else:
        new_ch = await category.create_voice_channel(name=new_ch_name,
                                                     reason=trl(0, for_user.guild.id, 'temporary_vc_mod_reason'),
                                                     bitrate=from_ch.bitrate, user_limit=from_ch.user_limit)

    res = client['TemporaryVC'].insert_one(
        {'ChannelID': str(new_ch.id), 'GuildID': str(new_ch.guild.id), 'CreatorID': str(for_user.id)})

    if '{id}' in new_ch_name:
        id = str(res.inserted_id)
        new_ch_name = new_ch_name.replace('{id}', str(id))
        await new_ch.edit(name=new_ch_name)

    # V2 Menu
    try:
        emb = Embed(
            title='Voice Channel Settings',
            description='This is a temporary voice channel. Here you can change some settings.',
            colour=Color.blue()
        )
        msg_2 = await new_ch.send(content=for_user.mention, embed=emb, view=V2TemporaryVCMenu())
        client['TemporaryVC'].update_one({'_id': res.inserted_id}, {'$set': {'ManagementMenuMsgID': str(msg_2.id)}})
    except Exception as e:
        sentry_sdk.capture_exception(e)

    return new_ch


async def h_leave_channel(member: discord.Member, state: discord.VoiceState):
    data = client['TemporaryVC'].find_one(
        {'ChannelID': str(state.channel.id), 'GuildID': str(state.channel.guild.id)})
    if not data:
        return

    client['TemporaryVC'].update_one(
        {'ChannelID': str(state.channel.id), 'GuildID': str(state.channel.guild.id)},
        {'$pull': {'Users': str(member.id)}})

    # Check if there are still users
    if len(state.channel.voice_states) > 0:
        # Check if the creator left
        if str(member.id) == data['CreatorID']:
            # Promote a new channel "creator", allowing the members still in the channel to manage it
            new_c = data['Users'][0]
            if new_c == str(member.id):
                new_c = data['Users'][1]
            client['TemporaryVC'].update_one(
                {'ChannelID': str(state.channel.id), 'GuildID': str(state.channel.guild.id)},
                {'$set': {'CreatorID': new_c}}
            )

        return

    # Delete the channel if there are no users left
    await state.channel.delete(reason=trl(0, member.guild.id, 'temporary_vc_mod_reason'))
    client['TemporaryVC'].delete_one({'ChannelID': str(state.channel.id), 'GuildID': str(state.channel.guild.id)})


async def h_join_channel(member: discord.Member, state: discord.VoiceState):
    client['TemporaryVC'].update_one(
        {'ChannelID': str(state.channel.id), 'GuildID': str(state.channel.guild.id)},
        {'$push': {'Users': str(member.id)}})

    if client['TemporaryVCCreators'].count_documents(
            {'ChannelID': str(state.channel.id), 'GuildID': str(state.channel.guild.id)}) > 0:
        vc = await new_temporary_channel(state.channel, member)
        await member.move_to(vc, reason=trl(0, member.guild.id, 'temporary_vc_mod_reason'))


class TemporaryVC(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    temporary_vc_commands = discord.SlashCommandGroup(name='temporary_voice_channels',
                                                      description='Temporary VC channels commands')

    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        try:
            # check if the module is enabled
            if not get_setting(member.guild.id, "module_temporary_vc_enabled", True):
                return

            # First let's check joining for temporary voice channel creation
            if after.channel and not before.channel:
                await h_join_channel(member, after)

            # Now let's check leaving for temporary voice channel deletion
            if before.channel and not after.channel:
                await h_leave_channel(member, before)

            # Handle moving between channels, it's pretty much leaving the previous and joining the new one
            if before.channel and after.channel and before.channel != after.channel:
                await h_leave_channel(member, before)
                await h_join_channel(member, after)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @temporary_vc_commands.command(name='add_creator_channel',
                                   description='Add a channel to create temporary voice channels')
    @is_module_enabled("temporary_vc")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def add_creator_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        try:
            client['TemporaryVCCreators'].insert_one({'ChannelID': str(channel.id), 'GuildID': str(channel.guild.id)})
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, 'temporary_vc_creator_channel_add').format(channel=channel.mention),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @temporary_vc_commands.command(name='remove_creator_channel',
                                   description='Remove a channel to create temporary voice channels')
    @is_module_enabled("temporary_vc")
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def remove_creator_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        try:
            if client['TemporaryVCCreators'].delete_one(
                    {'ChannelID': str(channel.id), 'GuildID': str(channel.guild.id)}).deleted_count > 0:
                await ctx.respond(
                    trl(ctx.user.id, ctx.guild.id, 'temporary_vc_creator_channel_remove').format(
                        channel=channel.mention),
                    ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'temporary_vc_error_channel_not_in_creator').format(
                    channel=channel.mention), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @temporary_vc_commands.command(name='change_default_name',
                                   description='Default name syntax. {name}, {username}, {guild}, {id} are available')
    @is_module_enabled("temporary_vc")
    async def change_default_name(self, ctx: discord.ApplicationContext, name: str):
        try:
            set_setting(ctx.guild.id, 'temporary_vc_name', name)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'temporary_vc_name_format_change').format(name=name),
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
