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
import os

akabot_logger = logging.getLogger("akabot")

def get_key(key: str, default: str = "", required: bool = True):
    key = key.upper()
    value = os.getenv(key)
    if not value:
        akabot_logger.info("Using default %s for %s", default, key)

        if len(default.strip()) == 0 and required:
            raise ValueError("The default for the value %s is by default None. This value is required" % key)

        return default

    return value
