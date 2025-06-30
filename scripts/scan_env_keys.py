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

import os
import re


def get_files(path: str) -> list[str]:
    # Get list of .py files, recursively in directories

    file_names = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if filename.endswith('.py'):
                file_names.append(os.path.join(root, filename))

    return file_names


if __name__ == '__main__':

    files = get_files("../")

    for i in files:
        with open(i) as f:
            script = f.read()

        for j in re.findall(r"get_key\(['\"]([a-zA-Z_]+)['\"](, ['\"]true['\"])?\)", script):
            print(j[0].upper())
