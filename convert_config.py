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

print("Akabot Config Converter from 3.1 -> 3.2")
print("This script will convert your config.json to config.conf format.")

with open("config.json", "r") as f:
    data = json.load(f)

with open("config.conf", "w") as f:
    f.write("""
Admin_AdminGuildID={admin_guild}
Admin_OwnerID={owner_id}
Bot_Version=3.2
Sentry_Enabled={sentry_enabled}
Sentry_DSN={sentry_dsn}
Heartbeat_Enabled={heartbeat_enabled}
Bot_Token={token}
GitHub_User={github_user}
GitHub_Repo={github_repo}
GitHub_Token={github_token}
""".format(
        admin_guild=data.get_files("admin_guild", "0"),
        owner_id=data.get_files("owner_id", "0"),
        sentry_enabled=data.get_files("sentry", {}).get_files("enabled", "false"),
        sentry_dsn=data.get_files("sentry", {}).get_files("dsn", ""),
        heartbeat_enabled=data.get_files("heartbeat", {}).get_files("enabled", "false"),
        token=data.get_files("token", ""),
        github_user=data.get_files("github", {}).get_files("git_user", ""),
        github_repo=data.get_files("github", {}).get_files("git_repo", ""),
        github_token=data.get_files("github", {}).get_files("token", "")
    ))

print("Conversion complete. Written to config.conf.")
