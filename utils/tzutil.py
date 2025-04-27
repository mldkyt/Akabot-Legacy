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

import datetime

from utils.settings import get_setting


def get_server_midnight_time(server_id: int) -> datetime.datetime:
    """Get the time at midnight for the server's timezone

    Args:
        server_id (int): Server ID

    Returns:
        datetime: Time at midnight
    """
    tz_offset = get_setting(server_id, "timezone_offset", "0")
    stamp1 = datetime.datetime.now(datetime.timezone.utc).timestamp() // 86400 * 86400 + (86400 * 3) + float(tz_offset) * 3600
    return datetime.datetime.fromtimestamp(stamp1)


def adjust_time_for_server(time: datetime.datetime, server_id: int) -> datetime.datetime:
    """Adjust time for the server's timezone

    Args:
        time (datetime): Time
        server_id (int): Server ID

    Returns:
        datetime: Adjusted time
    """
    tz_offset = get_setting(server_id, "timezone_offset", "0")
    return time + datetime.timedelta(hours=float(tz_offset))


def get_now_for_server(server_id: int) -> datetime.datetime:
    """Get the current time for the server's timezone

    Args:
        server_id (int): Server ID

    Returns:
        datetime: Current time
    """
    return adjust_time_for_server(datetime.datetime.now(), server_id)
