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

from database import client


def db_add_announcement_channel(guild_id: int, channel_id: int):
    data = client['AnnouncementChannels'].find_one(
        {'GuildID': {'$eq': str(guild_id)}, 'ChannelID': {'$eq': str(channel_id)}})
    if not data:
        client['AnnouncementChannels'].insert_one({'GuildID': str(guild_id), 'ChannelID': str(channel_id)})


def db_remove_announcement_channel(guild_id: int, channel_id: int):
    data = client['AnnouncementChannels'].find_one(
        {'GuildID': {'$eq': str(guild_id)}, 'ChannelID': {'$eq': str(channel_id)}})
    if data:
        client['AnnouncementChannels'].delete_one(
            {'GuildID': {'$eq': str(guild_id)}, 'ChannelID': {'$eq': str(channel_id)}})


def db_is_subscribed_to_announcements(guild_id: int, channel_id: int):
    data = client['AnnouncementChannels'].find_one(
        {'GuildID': {'$eq': str(guild_id)}, 'ChannelID': {'$eq': str(channel_id)}})
    return data is not None


def db_get_announcement_channels(guild_id: int):
    data = client['AnnouncementChannels'].find({'GuildID': {'$eq': str(guild_id)}}).to_list()
    return [(i['GuildID'], i['ChannelID']) for i in data]


def db_get_all_announcement_channels():
    data = client['AnnouncementChannels'].find().to_list()
    return [(i['GuildID'], i['ChannelID']) for i in data]

def db_count_announcement_channels(guild_id: int):
    data = client['AnnouncementChannels'].count_documents({
        'GuildID': str(guild_id)
    })
    return data
