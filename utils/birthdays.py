from database import client

def is_broadcast(user_id: int, guild_id: int):
    """
    Parameters
    ----------
    user_id: int ID of member to check for
    guild_id: int ID of guild to check for

    Returns
    -------
    If member should be broadcast in a server or not. Also use 'AllowedServers' in data type
    """
    data = client['UserBirthday'].find_one({
        'UserID': str(user_id)
    })

    if data is None:
        return False

    if 'AllowedServers' not in data:
        return False

    return str(guild_id) in data['AllowedServers']

def remove_broadcast(user_id: int, guild_id: int):
    client['UserBirthday'].update_one({
        'UserID': str(user_id)
    }, {
        '$pull': {
            'AllowedServers': str(guild_id)
        }
    })

def add_broadcast(user_id: int, guild_id: int):
    client['UserBirthday'].update_one({
        'UserID': str(user_id)
    }, {
        '$push': {
            'AllowedServers': str(guild_id)
        }
    })

def set_broadcast(user_id: int, guild_id: int, state: bool):
    """
    Set state of broadcasting
    Parameters
    ----------
    user_id: int ID of member to affect
    guild_id: int ID of guild to set value for
    state: bool State to set this value for

    Returns
    -------
    True if modified, False if not modified
    """
    is_broadcasting = is_broadcast(user_id, guild_id)

    if not state and is_broadcasting:
        remove_broadcast(user_id, guild_id)
        return True
    elif state and not is_broadcasting:
        add_broadcast(user_id, guild_id)
        return True
    else:
        return False
