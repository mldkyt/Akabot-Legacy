import logging

from discord.ext import commands as commands_ext
from discord.ext.commands import CheckFailure

from database import client
from utils.config import get_key

SFW_ONLY = get_key("SFW_ONLY", "false") == "true"

BLOCKLIST_WORDS = [i.strip() for i in get_key("BLOCKLIST_WORDS", "", required=False).split(";") if len(i.strip()) > 0]
BLOCKLIST_SERVERS = [i.strip() for i in get_key("BLOCKLIST_SERVERS", "", required=False).split(";") if len(i.strip()) > 0]
BLOCKLIST_USERS = [i.strip() for i in get_key("BLOCKLIST_USERS", "", required=False).split(";") if len(i.strip()) > 0]

PERM_BLOCKLIST_WORDS = [i.strip() for i in get_key("PERMANENT_BLOCKLIST_WORDS", "", required=False).split(";") if len(i.strip()) > 0]

akabot_logger = logging.getLogger("akabot")

akabot_logger.debug("BLOCKLIST_WORDS: %s %d", str(BLOCKLIST_WORDS), len(BLOCKLIST_WORDS))
akabot_logger.debug("BLOCKLIST_SERVERS: %s %d", str(BLOCKLIST_SERVERS), len(BLOCKLIST_SERVERS))
akabot_logger.debug("BLOCKLIST_USERS: %s %d", str(BLOCKLIST_USERS), len(BLOCKLIST_USERS))
akabot_logger.debug("PERM_BLOCKLIST_WORDS: %s %d", str(PERM_BLOCKLIST_WORDS), len(PERM_BLOCKLIST_WORDS))

def check_blocklist(text: str) -> tuple[bool, str]:
    for i in BLOCKLIST_WORDS:
        if i.lower() in text.lower():
            akabot_logger.debug("Text %s contains keyword %i", text, i.lower())
            return True, i
        
    for i in PERM_BLOCKLIST_WORDS:
        if i.lower() in text.lower():
            akabot_logger.debug("Text %s contains perm keyword %i", text, i.lower())
            return True, i
        
    return False, ""

def add_guild_to_blocklist(guild_id: str, text: str):
    for i in PERM_BLOCKLIST_WORDS:
        if i.lower() in text.lower():
            akabot_logger.debug("Adding guild %s to blocklist due to %s", str(guild_id), i.lower())
            client["BlocklistedGuilds"].insert_one({"GuildID": guild_id, "Reason": f"Blocklisted: \"{text}\" had permanent blocklisted keyword \"{i}\""})

def add_member_to_blocklist(user_id: str, text: str):
    for i in PERM_BLOCKLIST_WORDS:
        if i.lower() in text.lower():
            akabot_logger.debug("Adding member %s to blocklist due to %s", str(user_id), i.lower())
            client["BlocklistedUsers"].insert_one({"UserID": user_id, "Reason": f"Blocklisted: \"{text}\" had permanent blocklisted keyword \"{i}\""})

def check_guild_blocklist(guild_id: str) -> tuple[bool, str]:
    blocked = client["BlocklistedGuilds"].find_one({"GuildID": guild_id})
    if blocked:
        akabot_logger.debug("Server %s is blocked with reason %s", str(guild_id), blocked["Reason"])
        return True, blocked["Reason"]

    return False, ""

def check_user_blocklist(user_id: str) -> tuple[bool, str]:
    blocked = client["BlocklistedUsers"].find_one({"UserID": user_id})
    if blocked:
        akabot_logger.debug("User %s is blocked with reason %s", str(user_id), blocked["Reason"])
        return True, blocked["Reason"]

    return False, ""

def blocklist():
    def predicate(ctx: commands_ext.Context):
        try:
            if SFW_ONLY and ctx.channel.is_nsfw():
                raise BlocklistError("This instance of Akabot is configured to be only used in SFW spaces.")

            if ctx.guild is not None:
                if str(ctx.guild.id) in BLOCKLIST_SERVERS:
                    raise BlocklistError("This instance of Akabot blocks this server.")

                blocked, reason = check_guild_blocklist(str(ctx.guild.id))
                if blocked:
                    raise BlocklistError(f"Blocklisted in DB: {reason}")

                blocked, keyword = check_blocklist(ctx.guild.name)
                if blocked:
                    add_guild_to_blocklist(str(ctx.guild.id), ctx.guild.name)
                    raise BlocklistError(f"Word {keyword} was blocklisted in guild.name")

                blocked, keyword = check_blocklist(ctx.guild.description or '')
                if blocked:
                    add_guild_to_blocklist(str(ctx.guild.id), ctx.guild.description or '')
                    raise BlocklistError(f"Word {keyword} was blocklisted in guild.description")

            if ctx.author is not None:
                if str(ctx.author.id) in BLOCKLIST_USERS:
                    raise BlocklistError("This instance of Akabot blocks you.")

                blocked, reason = check_user_blocklist(str(ctx.author.id))
                if blocked:
                    raise BlocklistError(f"Blocklisted in DB: {reason}")

                blocked, keyword = check_blocklist(str(ctx.author.display_name))
                if blocked:
                    add_member_to_blocklist(str(ctx.author.display_name), ctx.author.display_name)
                    raise BlocklistError(f"Word {keyword} was blocklisted in author.display_name")

                blocked, keyword = check_blocklist(str(ctx.author.name))
                if blocked:
                    add_member_to_blocklist(str(ctx.author.display_name), ctx.author.name)
                    raise BlocklistError(f"Word {keyword} was blocklisted in author.name")

            return True
        except BlocklistError as e:
            raise e
        except Exception as e:
            return True
    
    return commands_ext.check(predicate)

class BlocklistError(CheckFailure):
    """Custom error for blocklist"""
    
    def __init__(self, message: str):
        self.message = message
    
    def __str__(self):
        return "Blocklisted: " + self.message
