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

import aiohttp
import discord
import gitlab
from discord import ButtonStyle
from discord.ext import commands as cmds_ext
from discord.ui import View, Button
from discord.ui.input_text import InputText

from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl
from database import client

akabot_logger = logging.getLogger("akabot")

class VoteView(discord.ui.View):
    def __init__(self):
        super().__init__()

        button1 = discord.ui.Button(label="top.gg", url="https://top.gg/bot/1172922944033411243")

        self.add_item(button1)


class PrivacyPolicyView(discord.ui.View):
    def __init__(self):
        super().__init__()

        button1 = discord.ui.Button(label="lunya.pet",
                                    url="https://lunya.pet/project/akabot/privacy/")

        self.add_item(button1)


class BugReportModal(discord.ui.Modal):
    def __init__(self, user_id: int) -> None:
        super().__init__(title="Bug Report", timeout=600)

        self.user_id = user_id
        title = trl(user_id, 0, "title")
        description = trl(user_id, 0, "description")
        self.title_input = InputText(label=title, style=discord.InputTextStyle.short, max_length=100, min_length=8,
                                     required=True)
        self.description_input = InputText(label=description, style=discord.InputTextStyle.long, max_length=1000,
                                           min_length=20, required=True)

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def submit_bug_report_on_github(self, interaction: discord.Interaction):
        issue_body = ("- This bug report was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        git_user = get_key("GitHub_User")
        git_repo = get_key("GitHub_Repo")
        token = get_key("GitHub_Token")
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": "Bug Report: {bug}".format(bug=self.title_input.value),
            "body": issue_body,
            "labels": ["bug", "in-bot"]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"https://api.github.com/repos/{git_user}/{git_repo}/issues", headers=headers,
                                    json=data) as response:
                if response.status != 201:
                    await interaction.response.send_message(f"Failed to submit bug report: {await response.text()}",
                                                            ephemeral=True)
                    return
        await interaction.response.send_message(
            trl(self.user_id, 0, "feedback_bug_report_submitted", append_tip=True), ephemeral=True)

    async def submit_bug_report_on_gitlab(self, interaction: discord.Interaction):
        issue_body = ("- This bug report was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        gitlab_instance = get_key("GitLab_Instance", "https://gitlab.com")
        gitlab_project_id = get_key("GitLab_ProjectID")
        gitlab_token = get_key("GitLab_Token")

        gl = gitlab.Gitlab(url=gitlab_instance, private_token=gitlab_token)
        gl.projects.get(gitlab_project_id).issues.create({
            'title': f'Bug Report: {self.title_input.value}',
            'description': issue_body,
            'labels': ['bug', 'in-bot']
        })

        await interaction.response.send_message(trl(self.user_id, 0, "feedback_feature_submitted", append_tip=True),
                                                ephemeral=True)

    async def submit_bug_report_on_forgejo(self, interaction):
        forgejo_instance = get_key("Forgejo_Instance")
        forgejo_token = get_key('Forgejo_Token')
        forgejo_owner = get_key('Forgejo_Owner')
        forgejo_project = get_key('Forgejo_Project')

        issue_body = ("- This bug report was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://{forgejo_instance}/api/v1/repos/{forgejo_owner}/{forgejo_project}/issues',
                                    json={
                                        'title': self.title_input.value,
                                        'body': issue_body
                                    },
                                    headers={
                                        'Authorization': f'token {forgejo_token}'
                                    }) as r:
                if r.ok:
                    await interaction.response.send_message(
                        trl(self.user_id, 0, "feedback_bug_report_submitted", append_tip=True),
                        ephemeral=True)
                else:
                    await interaction.response.send_message(f"Failed to submit bug report: {await r.text()}",
                                                            ephemeral=True)

    async def callback(self, interaction: discord.Interaction):
        try:
            issue_platform = get_key("Issue_Platform", "github")

            if issue_platform == "github":
                await self.submit_bug_report_on_github(interaction)
            elif issue_platform == "gitlab":
                await self.submit_bug_report_on_gitlab(interaction)
            elif issue_platform == "forgejo":
                await self.submit_bug_report_on_forgejo(interaction)
            else:
                await interaction.respond(
                    "Error: This Akabot instance doesn't have issue reporting configured. Please contact the instance maintainer.",
                    ephemeral=True)

        except Exception as e:
            akabot_logger.exception("An error occured:")
            await interaction.response.send_message(trl(self.user_id, 0, "command_error_generic"), ephemeral=True)


class FeatureModal(discord.ui.Modal):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(title=trl(user_id, 0, "feedback_feature_form_title"), timeout=600)

        title = trl(user_id, 0, "title")
        description = trl(user_id, 0, "description")
        self.title_input = InputText(label=title, style=discord.InputTextStyle.short, max_length=100, min_length=8,
                                     required=True)
        self.description_input = InputText(label=description, style=discord.InputTextStyle.long, max_length=1000,
                                           min_length=20, required=True)

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def submit_feature_on_github(self, interaction: discord.Interaction):
        issue_body = ("- This feature request was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        git_user = get_key("GitHub_User")
        git_repo = get_key("GitHub_Repo")
        token = get_key("GitHub_Token")
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": "Feature request: {title}".format(title=self.title_input.value),
            "body": issue_body,
            "labels": ["enhancement", "in-bot"]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"https://api.github.com/repos/{git_user}/{git_repo}/issues", headers=headers,
                                    json=data) as response:
                if response.status != 201:
                    await interaction.response.send_message(
                        f"Failed to submit feature request: {await response.text()}", ephemeral=True)
                    return
        await interaction.response.send_message(trl(self.user_id, 0, "feedback_feature_submitted", append_tip=True),
                                                ephemeral=True)

    async def submit_feature_on_gitlab(self, interaction: discord.Interaction):
        issue_body = ("- This feature request was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        gitlab_instance = get_key("GitLab_Instance", "https://gitlab.com")
        gitlab_project_id = get_key("GitLab_ProjectID")
        gitlab_token = get_key("GitLab_Token")

        gl = gitlab.Gitlab(url=gitlab_instance, private_token=gitlab_token)
        gl.projects.get(gitlab_project_id).issues.create({
            'title': f'Feature Request: {self.title_input.value}',
            'description': issue_body,
            'labels': ['suggestion', 'in-bot']
        })

        await interaction.response.send_message(trl(self.user_id, 0, "feedback_feature_submitted", append_tip=True),
                                                ephemeral=True)

    async def submit_feature_on_forgejo(self, interaction):
        forgejo_instance = get_key("Forgejo_Instance")
        forgejo_token = get_key('Forgejo_Token')
        forgejo_owner = get_key('Forgejo_Owner')
        forgejo_project = get_key('Forgejo_Project')

        issue_body = ("- This feature request was created by {display} ({user} {id}) on Discord\n\n"
                      "---\n\n"
                      "### The issue was described by the user as follows:\n\n"
                      "{desc}".format(display=interaction.user.display_name,
                                      user=interaction.user.name,
                                      id=interaction.user.id,
                                      desc=self.description_input.value))

        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://{forgejo_instance}/api/v1/repos/{forgejo_owner}/{forgejo_project}/issues',
                                    json={
                                        'title': self.title_input.value,
                                        'body': issue_body
                                    },
                                    headers={
                                        'Authorization': f'token {forgejo_token}'
                                    }) as r:
                if r.ok:
                    await interaction.response.send_message(
                        trl(self.user_id, 0, "feedback_feature_submitted", append_tip=True),
                        ephemeral=True)
                else:
                    await interaction.response.send_message(f"Failed to submit feature request: {await r.text()}",
                                                            ephemeral=True)

    async def callback(self, interaction: discord.Interaction):
        try:
            issue_platform = get_key("Issue_Platform", "github")

            if issue_platform == "github":
                await self.submit_feature_on_github(interaction)
            elif issue_platform == "gitlab":
                await self.submit_feature_on_gitlab(interaction)
            elif issue_platform == "forgejo":
                await self.submit_feature_on_forgejo(interaction)
            else:
                await interaction.respond(
                    "Error: This Akabot instance doesn't have issue reporting configured. Please contact the instance maintainer.",
                    ephemeral=True)

        except Exception as e:
            akabot_logger.exception("An error occured:")
            await interaction.response.send_message(trl(self.user_id, 0, "command_error_generic"), ephemeral=True)


class ConfirmSubmitBugReport(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

        self.agree_button = discord.ui.Button(label=trl(user_id, 0, "feedback_agree"))
        self.agree_button.callback = self.submit
        self.add_item(self.agree_button)

        self.cancel_github = discord.ui.Button(label=trl(user_id, 0, "feedback_prefer_github"),
                                               style=discord.ButtonStyle.secondary)
        self.cancel_github.callback = self.cancel_gh
        self.add_item(self.cancel_github)

    async def submit(self, interaction: discord.Interaction):
        modal = BugReportModal(self.user_id)
        await interaction.response.send_modal(modal)

    async def cancel_gh(self, interaction: discord.Interaction):
        self.disable_all_items()
        await interaction.respond(
            trl(self.user_id, 0, "feedback_bug_report_direct", append_tip=True),
            ephemeral=True)


class ConfirmSubmitFeatureRequest(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

        self.agree_button = discord.ui.Button(label=trl(user_id, 0, "feedback_agree"))
        self.agree_button.callback = self.submit
        self.add_item(self.agree_button)

        self.cancel_github = discord.ui.Button(label=trl(user_id, 0, "feedback_prefer_github"),
                                               style=discord.ButtonStyle.secondary)
        self.cancel_github.callback = self.cancel_gh
        self.add_item(self.cancel_github)

    async def submit(self, interaction: discord.Interaction):
        modal = FeatureModal(self.user_id)
        await interaction.response.send_modal(modal)

    async def cancel_gh(self, interaction: discord.Interaction):
        await interaction.respond(
            trl(self.user_id, 0, "feedback_feature_direct", append_tip=True),
            ephemeral=True)


class DiscordJoinView(View):
    def __init__(self):
        super().__init__(timeout=180)

        join_btn = discord.ui.Button(label="Join the server", style=discord.ButtonStyle.link,
                                     url="https://discord.gg/YFksXpXnn6")
        self.add_item(join_btn)


class MastodonLinkView(View):
    def __init__(self):
        super().__init__(timeout=180)

        mastodon_btn = Button(label='Open in Mastodon @ floss.social', style=ButtonStyle.link,
                              url='https://floss.social/@Akabot')

        self.add_item(mastodon_btn)


class SupportCmd(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(name="website", help="Get the website link")
    @analytics("website")
    @blocklist()
    async def website(self, ctx: discord.ApplicationContext):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "feedback_visit_website", append_tip=True), ephemeral=True)

    @discord.slash_command(name="vote", description="Vote on the bot")
    @analytics("vote")
    @blocklist()
    async def vote(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            trl(ctx.user.id, ctx.guild.id, "feedback_vote", append_tip=True),
            view=VoteView(),
            ephemeral=True
        )

    @discord.slash_command(name="privacy", description="Privacy policy URL")
    @analytics("privacy policy")
    @blocklist()
    async def privacy_policy(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            trl(ctx.user.id, ctx.guild.id, "feedback_privacy_policy", append_tip=True),
            view=PrivacyPolicyView(),
            ephemeral=True
        )

    @discord.slash_command(name="donate", description="Donate to the bot to support it")
    @analytics("donate")
    @blocklist()
    async def donate(self, ctx: discord.ApplicationContext):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "feedback_donate", append_tip=True), ephemeral=True)

    @discord.slash_command(name='support_discord', description='Support Discord server link')
    async def support_discord(self, ctx: discord.ApplicationContext):
        await ctx.respond("""
# Support Discord Server

__You'll need to verify yourself on the server to post an introduction and get access to the rest of the server.__
This is due to recent raids and attacks on the server due to the developer leaving another modding community because of constant harassment.
**It takes maximum 10 minutes to write an introduction about yourself, and you'll get access to the rest of the server.**

### With this noted, click the button below to join the server:
        """, view=DiscordJoinView(), ephemeral=True)

    @discord.slash_command(name='mastodon', description='Link to the Akabot\'s Mastodon profile!')
    @analytics("mastodon")
    @blocklist()
    async def mastodon(self, ctx: discord.ApplicationContext):
        await ctx.respond(
            "The official Mastodon account of Akabot is @akabot@floss.social\nIt's used for:\n- Akabot updates\n- Akabot service annoncements\n- More!",
            ephemeral=True, view=MastodonLinkView())

    @discord.slash_command(name='limits', description='Get server limits, along with usage')
    @analytics("limits")
    @blocklist()
    async def cmd_limits(self, ctx: discord.ApplicationContext):
        chat_summary_usage = client['ChatSummary'].count_documents({
            'GuildID': str(ctx.guild.id), 'Enabled': True
        })
        announcement_channel_usage = client['AnnouncementChannels'].count_documents({
            'GuildID': str(ctx.guild.id)
        })
        roles_on_join_usage = client['RolesOnJoin'].count_documents({'GuildID': str(ctx.guild.id)})
        giveaways_usage = client['Giveaways'].count_documents({'GuildID': str(ctx.guild.id)})
        automod_actions_usage = client['AutomodActions'].count_documents({'GuildID': str(ctx.guild.id)})

        chat_summary_limit = int(get_key("Max_ChatSummary_Channels", "3"))
        announcement_channel_limit = int(get_key('Max_AnnouncementChannels', '10'))
        roles_on_join_limit = int(get_key('Max_RolesOnJoin', '3'))
        giveaways_limit = int(get_key('Max_Giveaways', '3'))
        automod_actions_limit = int(get_key("AutomodActions_MaxActions", "5"))

        await ctx.respond(f'''
# Understanding the limits of this Akabot instance
- **Announcement Channels**: {announcement_channel_usage} out of {announcement_channel_limit} ({round((announcement_channel_usage / announcement_channel_limit) * 100)}%)
- **Chat Summary Channels**: {chat_summary_usage} out of {chat_summary_limit} channels ({round((chat_summary_usage / chat_summary_limit) * 100)}%)
- **Roles on Join**: {roles_on_join_usage} out of {roles_on_join_limit} roles ({round((roles_on_join_usage / roles_on_join_limit) * 100)}%)
- **Giveaways**: {giveaways_usage} out of {giveaways_limit} running giveaways ({round((giveaways_usage / giveaways_limit) * 100)}%)
- **Automod Actions**: {automod_actions_usage} out of {automod_actions_limit} Automod rules ({round((automod_actions_usage / automod_actions_limit) * 100)}%)''', ephemeral=True)


    feedback_subcommand = discord.SlashCommandGroup(name="feedback", description="Give feedback for the bot")

    @feedback_subcommand.command(name="bug", description="Report a bug")
    @cmds_ext.cooldown(1, 300, cmds_ext.BucketType.user)
    @analytics("feedback bug")
    @blocklist()
    async def report_bug(self, ctx: discord.ApplicationContext):
        await ctx.respond(content=trl(ctx.user.id, ctx.guild.id, "feedback_bug_report_disclaimer", append_tip=True),
                          ephemeral=True,
                          view=ConfirmSubmitBugReport(ctx.user.id))

    @feedback_subcommand.command(name="feature", description="Suggest a feature")
    @cmds_ext.cooldown(1, 300, cmds_ext.BucketType.user)
    @analytics("feedback feature")
    @blocklist()
    async def suggest_feature(self, ctx: discord.ApplicationContext):
        await ctx.respond(content=trl(ctx.user.id, ctx.guild.id, "feedback_feature_disclaimer", append_tip=True),
                          ephemeral=True,
                          view=ConfirmSubmitFeatureRequest(ctx.user.id))

    @discord.slash_command(name="about", description="Get information about the bot")
    @analytics("about")
    @blocklist()
    async def about(self, ctx: discord.ApplicationContext):
        await ctx.respond(trl(ctx.user.id, ctx.guild.id, "feedback_about", append_tip=True), ephemeral=True)
