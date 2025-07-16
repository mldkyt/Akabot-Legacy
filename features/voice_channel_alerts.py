import logging

import discord

from database import client
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

                await ctx.respond("Subscribed to all notifications! :3", ephemeral=True)
                return

            if not subscribed and current_subscribed:
                client['vc_notifs_all'].delete_one({
                    'Member': str(ctx.user.id)
                })

                await ctx.respond("Unsubscribed from ALL notifications! :3", ephemeral=True)
                return

            if subscribed and current_subscribed:
                await ctx.respond("You are already subscribed to all notifications! :3", ephemeral=True)
            else:
                await ctx.respond("You aren't subscribed to any notifications! :3", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Something went wrong! :3", ephemeral=True)

    @command_grp.command(name="sub_user", description="Subscribe to notifications from a specific user")
    @is_module_enabled("voice_channel_alerts")
    async def sub_user(self, ctx: discord.ApplicationContext, user: discord.User):
        try:
            if client['vc_notifs_user'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            }) > 0:
                await ctx.respond(f"You are already subscribed to notifications from {user.mention}! :3", ephemeral=True)
                return

            client['vc_notifs_user'].insert_one({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            })

            await ctx.respond(f"Subscribed to notifications from {user.mention}! :3", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Something went wrong! :3", ephemeral=True)

    @command_grp.command(name="unsub_user", description="Unsubscribe from notifications from a specific user")
    @is_module_enabled("voice_channel_alerts")
    async def unsub_user(self, ctx: discord.ApplicationContext, user: discord.User):
        try:
            if client['vc_notifs_user'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            }) == 0:
                await ctx.respond(f"You are not subscribed to notifications from {user.mention}! :3", ephemeral=True)
                return

            client['vc_notifs_user'].delete_one({
                'Member': str(ctx.user.id),
                'Target': str(user.id)
            })

            await ctx.respond(f"Unsubscribed from {user.mention} notifications! :3", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Something went wrong! :3", ephemeral=True)

    @command_grp.command(name="sub_channel", description="Subscribe to notifications from a specific channel")
    @is_module_enabled("voice_channel_alerts")
    async def sub_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        try:
            if client['vc_notifs_channel'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            }) > 0:
                await ctx.respond(f"You are already subscribed to notifications from {channel.mention}! :3", ephemeral=True)
                return

            client['vc_notifs_channel'].insert_one({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            })

            await ctx.respond(f"Subscribed to notifications from {channel.mention}! :3", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Something went wrong! :3", ephemeral=True)

    @command_grp.command(name="unsub_channel", description="Unsubscribe from notifications from a specific channel")
    @is_module_enabled("voice_channel_alerts")
    async def unsub_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel):
        try:
            if client['vc_notifs_channel'].count_documents({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            }) == 0:
                await ctx.respond(f"You are not subscribed to notifications from {channel.mention}! :3", ephemeral=True)
                return

            client['vc_notifs_channel'].delete_one({
                'Member': str(ctx.user.id),
                'Target': str(channel.id)
            })

            await ctx.respond(f"Unsubscribed from {channel.mention} notifications! :3", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond("Something went wrong! :3", ephemeral=True)

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
                            await dm_target.send("# Haiii :3\n"
                                                 f"{member.mention} has joined {after.channel.mention}\n"
                                                 f"-# You received this DM because you're subscribed to ALL notifications!")
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
                            await dm_target.send("# Haiii :3\n"
                                                 f"{member.mention} has joined {after.channel.mention}\n"
                                                 f"-# You received this DM because you're subscribed to {member.mention}'s VC notifications!")
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
                            await dm_target.send("# Haiii :3\n"
                                                 f"{member.mention} has joined {after.channel.mention}\n"
                                                 f"-# You received this DM because you're subscribed to {after.channel.mention}'s VC notifications!")
                            sent_to.append(i['Member'])
                    except discord.Forbidden:
                        pass


        except Exception as e:
            akabot_logger.exception("An error occured:")
