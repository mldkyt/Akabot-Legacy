
from discord.ext import commands as commands_ext

from utils.settings import get_setting


class ModuleNotEnabled(commands_ext.CheckFailure):
    def __init__(self, module: str):
        super().__init__(message=f"Module {module} is not enabled!")
        self.message=f"Module {module} is not enabled!"

    def __str__(self):
        return self.message

def is_module_enabled(module_name: str):
    def predicate(ctx: commands_ext.Context):
        if not get_setting(ctx.guild.id, f"module_{module_name}_enabled", True):
            raise ModuleNotEnabled(module_name)

        return True

    return commands_ext.check(predicate)
