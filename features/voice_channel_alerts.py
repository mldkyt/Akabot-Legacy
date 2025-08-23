import logging

import discord

from database import client
from utils.languages import get_translation_for_key_localized as trl
from utils.module_toggling import is_module_enabled
from utils.per_server_settings import get_setting

akabot_logger = logging.getLogger("akabot")

class VoiceChannelAlerts(discord.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    command_grp = discord.SlashCommandGroup(name="voice_channel_alerts", description="Subscribe to voice channel alerts")

    @command_grp.command(name="all_notifications", description="Subscribe to ALL voice channel join notifications")
    @is_module_enabled("voice_channel_alerts")
    async def set_all_notifications(self, ctx: discord.ApplicationContext, subscribed: bool):
        try:
            current_subscribed = client['vc_notifs_all'].count_documents({'Member': str(ctx.user.id)}) == 1

            if subscribed and not current_subscribed:
                client['vc_notifs_all'].insert_one({
                    'Member': str(ctx.user.id)
                })

                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "subscribed_all"), ephemeral=True)
                return

            if not subscribed and current_subscribed:
                client['vc_notifs_all'].delete_one({
                    'Member': str(ctx.user.id)
                })

                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "unsubscribed_all"), ephemeral=True)
                return

            if subscribed and current_subscribed:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "already_subscribed_all"), ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "already_unsubscribed_all"), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @command_grp.command(name="sub_user", description="Subscribe to notifications from a specific user")
    @is_module_enabled("voice_channel_alerts")
    async def sub_user(self, ctx: discord.ApplicationContext, user: discord.User):
        try:
            if client['vc_notifs_user'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            }) > 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "already_subscribed_user"), ephemeral=True)
                return

            client['vc_notifs_user'].insert_one({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            })

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "subscribed_user", mention=user.mention), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @command_grp.command(name="unsub_user", description="Unsubscribe from notifications from a specific user")
    @is_module_enabled("voice_channel_alerts")
    async def unsub_user(self, ctx: discord.ApplicationContext, user: discord.User):
        try:
            if client['vc_notifs_user'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            }) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "not_subscribed_user", mention=user.mention),
                                  ephemeral=True)
                return

            client['vc_notifs_user'].delete_one({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            })

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "unsubscribed_user", mention=user.mention), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @command_grp.command(name="sub_channel", description="Subscribe to notifications from a specific channel")
    @is_module_enabled("voice_channel_alerts")
    async def sub_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        try:
            if client['vc_notifs_channel'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            }) > 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "already_subscribed_channel", channel=channel.mention),
                                  ephemeral=True)
                return

            client['vc_notifs_channel'].insert_one({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            })

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "subscribed_channel", channel=channel.mention),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @command_grp.command(name="unsub_channel", description="Unsubscribe from notifications from a specific channel")
    @is_module_enabled("voice_channel_alerts")
    async def unsub_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        try:
            if client['vc_notifs_channel'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            }) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "already_subscribed_channel", channel=channel.mention),
                                  ephemeral=True)
                return

            client['vc_notifs_channel'].delete_one({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            })

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "not_subscribed_channel", channel=channel.mention),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.channel.id, "command_error_generic"), ephemeral=True)

    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        try:
            if before.channel is None and after.channel is not None:
                if get_setting(after.channel.guild.id, "module_voice_channel_alerts_enabled", True):
                    return

                sent_to = []

                # Member joined
                for i in client['vc_notifs_all'].find({}):
                    try:
                        dm_target = member.guild.get_member(int(i['Member']))
                        if dm_target is not None:
                            await dm_target.send(
                                trl(dm_target.id, 0, "channel_notification_dm_all", member=member.mention,
                                    channel=after.channel.mention))
                            sent_to.append(i['Member'])
                    except discord.Forbidden:
                        pass

                for i in client['vc_notifs_user'].find({
                    'Target': str(member.id)
                }):
                    try:
                        if i['Member'] in sent_to:
                            continue

                        dm_target = member.guild.get_member(int(i['Member']))
                        if dm_target is not None:
                            await dm_target.send(
                                trl(dm_target.id, 0, "channel_notification_dm_user", member=member.mention,
                                    channel=after.channel.mention))
                            sent_to.append(i['Member'])
                    except discord.Forbidden:
                        pass

                for i in client['vc_notifs_channel'].find({
                    'Target': str(after.channel.id)
                }):
                    try:
                        if i['Member'] in sent_to:
                            continue

                        dm_target = member.guild.get_member(int(i['Member']))
                        if dm_target is not None:
                            await dm_target.send(
                                trl(dm_target.id, 0, "channel_notification_dm_channel", member=member.mention,
                                    channel=after.channel.mention))
                            sent_to.append(i['Member'])
                    except discord.Forbidden:
                        pass


        except Exception as e:
            akabot_logger.exception("An error occured:")
