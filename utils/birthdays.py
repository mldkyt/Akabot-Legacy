from database import get_client

async def is_broadcast(user_id: int, guild_id: int):
    """
    Parameters
    ----------
    user_id: int ID of member to check for
    guild_id: int ID of guild to check for

    Returns
    -------
    If member should be broadcast in a server or not. Also use 'AllowedServers' in data type
    """
    client = get_client()
    data = await client['UserBirthday'].find_one({
        'UserID': str(user_id)
    })
    await client.client.close()

    if data is None:
        return False

    if 'AllowedServers' not in data:
        return False

    return str(guild_id) in data['AllowedServers']

async def remove_broadcast(user_id: int, guild_id: int):
    client = get_client()
    await client['UserBirthday'].update_one({
        'UserID': str(user_id)
    }, {
        '$pull': {
            'AllowedServers': str(guild_id)
        }
    })
    await client.client.close()


async def add_broadcast(user_id: int, guild_id: int):
    client = get_client()
    await client['UserBirthday'].update_one({
        'UserID': str(user_id)
    }, {
        '$push': {
            'AllowedServers': str(guild_id)
        }
    })
    await client.client.close()


async def set_broadcast(user_id: int, guild_id: int, state: bool):
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
    is_broadcasting = await is_broadcast(user_id, guild_id)

    if not state and is_broadcasting:
        await remove_broadcast(user_id, guild_id)
        return True
    elif state and not is_broadcasting:
        await add_broadcast(user_id, guild_id)
        return True
    else:
        return False
