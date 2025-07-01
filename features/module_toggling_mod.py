import discord
import sentry_sdk

from utils.per_server_settings import set_setting
from utils.languages import get_translation_for_key_localized as trl

VALID_MODULE_NAMES = ["antiraid", "birthday_announcements", "chat_streaks", "economy", "leveling", "schedule",
                      "time_capsule", "temporary_vc", "voice_channel_alerts", "word_scramble"]


class ModuleToggling(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    module_toggling = discord.SlashCommandGroup(name="module_toggling", description="Module toggling commands")

    @module_toggling.command(name="enable", description="Enable a module")
    @discord.option(name="module_name", choices=VALID_MODULE_NAMES)
    async def enable_module(self, ctx: discord.ApplicationContext, module_name: str):
        try:
            set_setting(ctx.guild.id,f"module_{module_name}_enabled", True)

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "module_enabled").format(module_name=module_name))
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"))

    @module_toggling.command(name="disable", description="Disable a module")
    @discord.option(name="module_name", choices=VALID_MODULE_NAMES)
    async def enable_module(self, ctx: discord.ApplicationContext, module_name: str):
        try:
            set_setting(ctx.guild.id,f"module_{module_name}_enabled", False)

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "module_disabled").format(module_name=module_name))
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"))
