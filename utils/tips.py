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

import json
import random
import re


def get_tips_from_lang_file(guild_id: int, user_id: int, lang: str) -> list[str]:
    """Get the tips from the language file

    Args:
        guild_id (int): Guild ID
        user_id (int): User ID
        lang (str): Language to get tips in (returns empty array when no tips are available for this language)

    Returns:
        list: List of tips
    """
    with open(f"lang/{lang}.json", encoding='utf8') as f:
        file = json.load(f)

    tips = []
    for key in file:
        if re.match(r"^tip_\d+$", key):
            tips.append(file[key])

    return tips


def append_tip_to_message(guild_id: int, user_id: int, msg: str, lang: str) -> str:
    """Append a random tip to a message

    Args:
        guild_id (int): Guild ID
        user_id (int): User ID
        msg (str): Message
        lang (str): Language to get tips in (Will NOT append tip if no tips are available for this language)

    Returns:
        str: Message with tip
    """
    tips = get_tips_from_lang_file(guild_id, user_id, lang)
    if len(tips) == 0:
        return msg  # No tips available for this language

    tip = tips[random.randint(0, len(tips) - 1)]
    return f"{msg}\n\n-# **Tip:** {tip}" + "\n-# Akabot is getting replaced with [Nekona](https://top.gg/bot/1426903542601613444) and will be shut down on June 30th, 2026."
