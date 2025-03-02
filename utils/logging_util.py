#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 mldchan
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

import discord

from utils.settings import get_setting


async def log_into_logs(server: discord.Guild, message: discord.Embed, view=None):
    log_id = get_setting(server.id, 'logging_channel', '0')
    log_chan = server.get_channel(int(log_id))
    if log_chan is None:
        return

    if not log_chan.can_send():
        return

    await log_chan.send(embed=message, view=view)
