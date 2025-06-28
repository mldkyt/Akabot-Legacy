import asyncio
import datetime
import random

import discord
from discord.ext import commands as commands_ext
from discord.ext import pages

from database import get_client
from utils.languages import get_translation_for_key_localized as trl
from utils.module_toggling import is_module_enabled
from utils.settings import set_setting, get_setting


async def add_akacoins(user_id: int, amount: int, location: str = 'wallet'):
    if location == 'wallet':
        loc = 'Wallet'
    elif location == 'bank':
        loc = 'Bank'
    else:
        return

    client = get_client()

    await client['Economy'].update_one({
        'UserID': str(user_id),
    }, {
        '$inc': {
            loc: amount
        }
    }, upsert=True)



async def rem_akacoins(user_id: int, amount: int, location: str = 'wallet'):
    if location == 'wallet':
        loc = 'Wallet'
    elif location == 'bank':
        loc = 'Bank'
    else:
        return

    client = get_client()

    await client['Economy'].update_one({
        'UserID': str(user_id),
    }, {
        '$inc': {
            loc: -amount
        }
    }, upsert=True)



async def set_akacoins(user_id: int, amount: int, location: str = 'wallet'):
    if location == 'wallet':
        loc = 'Wallet'
    elif location == 'bank':
        loc = 'Bank'
    else:
        return

    client = get_client()

    await client['Economy'].update_one({
        'UserID': str(user_id),
    }, {
        '$set': {
            loc: amount
        }
    }, upsert=True)



async def get_akacoins(user_id: int):
    client = get_client()
    if await client['Economy'].count_documents({'UserID': str(user_id)}) == 0:
        await client['Economy'].insert_one({
            'UserID': str(user_id),
        }, {
            'Wallet': 0,
            'Bank': 0
        })

    data = await client['Economy'].find_one({'UserID': str(user_id)})

    if 'Wallet' not in data:
        data['Wallet'] = 0
    if 'Bank' not in data:
        data['Bank'] = 0

    return data['Wallet'], data['Bank']


async def claim_daily(guild_id: int, user_id: int) -> (bool, int):
    client = get_client()
    data = await client['Economy'].find_one({
        'UserID': str(user_id),
    })
    if not data:
        return False, 0

    if 'LastDailyClaim' not in data:
        data['LastDailyClaim'] = datetime.datetime.now() - datetime.timedelta(days=1, minutes=1)

    if data['LastDailyClaim'] + datetime.timedelta(days=1) > datetime.datetime.now():
        return False, 0

    daily_min = int(await get_setting(guild_id, "economy_daily_min", "50"))
    daily_max = int(await get_setting(guild_id, "economy_daily_max", "500"))

    add_bal = random.randint(daily_min, daily_max)

    await client['Economy'].update_one({
        'UserID': str(user_id),
    }, {
        '$set': {
            'LastDailyClaim': datetime.datetime.now()
        },
        '$inc': {
            'Wallet': add_bal
        }
    })

    return True, add_bal


async def claim_weekly(guild_id: int, user_id: int) -> (bool, int):
    client = get_client()
    data = await client['Economy'].find_one({
        'UserID': str(user_id),
    })
    if not data:
        return False, 0

    if 'LastWeeklyClaim' not in data:
        data['LastWeeklyClaim'] = datetime.datetime.now() - datetime.timedelta(days=1, minutes=1)

    if data['LastWeeklyClaim'] + datetime.timedelta(days=1) > datetime.datetime.now():
        return False, 0

    weekly_min = int(await get_setting(guild_id, "economy_weekly_min", "50"))
    weekly_max = int(await get_setting(guild_id, "economy_weekly_max", "500"))

    add_bal = random.randint(weekly_min, weekly_max)

    await client['Economy'].update_one({
        'UserID': str(user_id),
    }, {
        '$set': {
            'LastWeeklyClaim': datetime.datetime.now()
        },
        '$inc': {
            'Wallet': add_bal
        }
    })

    return True, add_bal


async def work(guild_id: int, user_id: int) -> (bool, int):
    client = get_client()
    data = await client['Economy'].find_one({
        'UserID': str(user_id),
    })
    if not data:
        return False, 0

    if 'LastWorkTime' not in data:
        data['LastWorkTime'] = datetime.datetime.now() - datetime.timedelta(minutes=6)

    if data['LastWorkTime'] + datetime.timedelta(minutes=5) > datetime.datetime.now():
        return False, 0

    work_min = int(await get_setting(guild_id, "economy_work_min", "150"))
    work_max = int(await get_setting(guild_id, "economy_work_max", "400"))
    bonus_min = int(await get_setting(guild_id, "economy_work_bonus_min", "0"))
    bonus_max = int(await get_setting(guild_id, "economy_work_bonus_max", "100"))
    bonus_chance = int(await get_setting(guild_id, "economy_work_bonus_chance", "80"))
    bonus_chance_lose = int(await get_setting(guild_id, "economy_work_bonus_chance_lose", "10"))

    bonus = random.randint(bonus_min, bonus_max)
    bonus_ch = random.randint(0, 100)
    work_money = random.randint(work_min, work_max)

    if bonus_ch < bonus_chance_lose:
        work_money -= bonus
    if bonus_ch > bonus_chance:
        work_money += bonus

    await client['Economy'].update_one({
        'UserID': str(user_id),
    }, {
        '$set': {
            'LastWorkTime': datetime.datetime.now()
        },
        '$inc': {
            'Wallet': work_money
        }
    })

    return True, work_money


class SendMoneyConfirmation(discord.ui.View):
    def __init__(self, source: int, target: int, amount: int):
        super().__init__()
        self.source = source
        self.target = target
        self.amount = amount

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.danger)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        client = get_client()
        await client['Economy'].update_one({
            'UserID': str(self.source),
        }, {
            '$inc': {
                'Wallet': -self.amount
            }
        })
        await client['Economy'].update_one({
            'UserID': str(self.target),
        }, {
            '$inc': {
                'Wallet': self.amount
            }
        }, upsert=True)

        member = interaction.guild.get_member(self.target)
        if not member:
            member = 'Unknown'
        else:
            member = member.display_name

        await interaction.edit(view=None, content=(await trl(self.source, 0, 'economy_transfer_to_user', append_tip=True))
                               .format(amount=str(self.amount), member=member))

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.success)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.edit(view=None, content=await trl(self.source, 0, 'economy_transfer_cancel', append_tip=True))


class GambleView(discord.ui.View):
    def __init__(self, guild: int, user: int, amount: int):
        super().__init__()
        self.guild = guild
        self.user = user
        self.amount = amount

        self.chance = 80


        asyncio.create_task(self.second_init(guild))

    async def second_init(self, guild: int):
        start_min_percentage = int(await get_setting(guild, "economy_gambling_start_min_chance", "80"))
        start_max_percentage = int(await get_setting(guild, "economy_gambling_start_max_chance", "100"))

        self.chance = random.randint(start_min_percentage, start_max_percentage)

    @discord.ui.button(label='Gamble', style=discord.ButtonStyle.danger)
    async def gamble(self, button: discord.ui.Button, interaction: discord.Interaction):
        chance = random.randint(0, 100)
        if chance > self.chance:
            self.amount = 0
            await interaction.edit(view=None, content=await trl(self.user, 0, 'economy_gamble_fail', append_tip=True))
            return

        amount_increase_min_percentage = int(
            await get_setting(interaction.guild.id, "economy_gambling_amount_increase_min_percentage", "110"))
        amount_increase_max_percentage = int(
            await get_setting(interaction.guild.id, "economy_gambling_amount_increase_max_percentage", "200"))

        self.amount = int(
            self.amount * (random.randint(amount_increase_min_percentage, amount_increase_max_percentage) / 100))
        self.chance /= float(await get_setting(self.guild, "economy_gambling_factor", "1.1"))
        await interaction.edit(view=self, content=(await trl(self.user, 0, 'economy_gamble_process', append_tip=True)).format(
            amount=str(self.amount)))

    @discord.ui.button(label='Withdraw', style=discord.ButtonStyle.success)
    async def withdraw(self, button: discord.ui.Button, interaction: discord.Interaction):
        await add_akacoins(self.user, self.amount)

        self.stop()
        await interaction.edit(view=None, content=(await trl(self.user, 0, 'economy_gamble_withdraw', append_tip=True)).format(
            amount=str(self.amount)))


class Economy(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    economics_subcommands = discord.SlashCommandGroup(name='eco', description='Economy commands')

    # Weekly, daily commands
    @economics_subcommands.command(name='daily', description='Claim daily reward')
    @is_module_enabled("economy")
    async def daily(self, ctx: discord.ApplicationContext):
        success, added = claim_daily(ctx.guild.id, ctx.author.id)

        if not success:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_daily_claimed", append_tip=True), ephemeral=True)
            return

        await ctx.respond(
            (await trl(ctx.user.id, ctx.guild.id, "economy_daily_claim", append_tip=True)).format(amount=str(added)),
            ephemeral=True)

    @economics_subcommands.command(name='weekly', description='Claim weekly reward')
    @is_module_enabled("economy")
    async def weekly(self, ctx: discord.ApplicationContext):
        success, added = claim_weekly(ctx.guild.id, ctx.author.id)

        if not success:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'economy_weekly_claimed', append_tip=True), ephemeral=True)
            return

        await ctx.respond(
            (await trl(ctx.user.id, ctx.guild.id, 'economy_weekly_claim', append_tip=True)).format(amount=str(added)),
            ephemeral=True)

    @economics_subcommands.command(name='work', description='Work and earn money')
    @is_module_enabled("economy")
    async def work(self, ctx: discord.ApplicationContext):
        success, added = work(ctx.guild.id, ctx.author.id)

        if not success:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'economy_work_too_frequently', append_tip=True),
                              ephemeral=True)
            return

        await ctx.respond(
            (await trl(ctx.user.id, ctx.guild.id, 'economy_work_worked', append_tip=True)).format(amount=str(added)),
            ephemeral=True)

    @economics_subcommands.command(name='balance', description='View your balance')
    @is_module_enabled("economy")
    async def balance(self, ctx: discord.ApplicationContext):
        wallet, bank = get_akacoins(ctx.author.id)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_balance", append_tip=True)
                          ).format(wallet=str(wallet), bank=str(bank)), ephemeral=True)

    economics_admin_subcommands = economics_subcommands.create_subgroup(name='admin',
                                                                        description='Economy admin commands')

    @economics_subcommands.command(name='pay', description='Send someone money')
    @is_module_enabled("economy")
    async def pay(self, ctx: discord.ApplicationContext, target: discord.User, amount: int):
        if ctx.user.id == target.id:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_pay_self", append_tip=True), ephemeral=True)
            return

        client = get_client()
        source_data = await client['Economy'].find_one({'UserID': str(ctx.user.id)})
        if source_data['Wallet'] < amount:
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_no_money", append_tip=True)
                              ).format(wallet=str(source_data['Wallet']), amount=str(amount)), ephemeral=True)
            return

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_pay_confirmation", append_tip=True)
                          ).format(amount=str(amount), target=target.display_name), ephemeral=True,
                          view=SendMoneyConfirmation(ctx.user.id, target.id, amount))

    @economics_subcommands.command(name='gamble', description='Gamble with money')
    @is_module_enabled("economy")
    @commands_ext.cooldown(1, 60, commands_ext.BucketType.user)
    async def gamble(self, ctx: discord.ApplicationContext, amount: int):
        client = get_client()
        data = await client['Economy'].find_one({'UserID': str(ctx.user.id)})
        if data['Wallet'] < amount:
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_no_money", append_tip=True)
                              ).format(wallet=str(data['Wallet']), amount=str(amount)), ephemeral=True)
            return

        await ctx.respond(
            (await trl(ctx.user.id, ctx.guild.id, "economy_gamble_start", append_tip=True)).format(amount=str(amount)),
            ephemeral=True,
            view=GambleView(ctx.guild.id, ctx.user.id, amount))

    @economics_subcommands.command(name='rob', description='Attempt to rob someone')
    @is_module_enabled("economy")
    @commands_ext.cooldown(1, 60, commands_ext.BucketType.user)
    async def rob(self, ctx: discord.ApplicationContext, target: discord.Member):
        chance = random.randint(0, 100)

        chance_setting = int(await get_setting(ctx.guild.id, "economy_rob_chance", "60"))
        chance_min_money = int(await get_setting(ctx.guild.id, "economy_rob_min_money", "25"))

        client = get_client()
        target_data = await client['Economy'].find_one({'UserID': str(target.id)})
        if not target_data:
            target_data = {
                'Wallet': 0
            }

        if chance > chance_setting and target_data['Wallet'] < chance_min_money:
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_rob_success_no_money", append_tip=True)
                              ).format(target=target.display_name), ephemeral=True)
        elif chance > chance_setting:
            stolen_min_percentage = int(await get_setting(ctx.guild.id, "economy_rob_stolen_percentage_min", "10"))
            stolen_max_percentage = int(await get_setting(ctx.guild.id, "economy_rob_stolen_percentage_max", "25"))

            stolen = int(target_data['Wallet'] * (random.randint(stolen_min_percentage, stolen_max_percentage) / 100))
            await rem_akacoins(target.id, stolen)
            await add_akacoins(ctx.author.id, stolen)
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_rob_success", append_tip=True)
                              ).format(target=target.display_name, stolen=str(stolen)), ephemeral=True)
        elif target_data['Wallet'] < chance_min_money:
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_rob_fail_no_money", append_tip=True)
                              ).format(target=target.display_name), ephemeral=True)
        else:
            fine_min_percentage = int(await get_setting(ctx.guild.id, "economy_rob_fine_percentage_min", "10"))
            fine_max_percentage = int(await get_setting(ctx.guild.id, "economy_rob_fine_percentage_max", "200"))

            fine = int(random.randint(fine_min_percentage, fine_max_percentage) * (target_data['Wallet'] / 100))
            await rem_akacoins(ctx.user.id, fine)
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_rob_fail", append_tip=True)
                              ).format(target=target.display_name, fine=str(fine)), ephemeral=True)

    @economics_subcommands.command(name='leaderboard', description='View the server leaderboard')
    @is_module_enabled("economy")
    async def lb(self, ctx: discord.ApplicationContext):
        cur_page = ""
        p = []

        client = get_client()
        records = await client['Economy'].find().to_list()

        if len(records) == 0:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_lb_empty", append_tip=True), ephemeral=True)
            return

        for i, v in enumerate(records):
            member = ctx.guild.get_member(int(v['UserID']))
            if member is None:
                member = f'user{v["UserID"]}'
            else:
                member = member.display_name

            cur_page += (await trl(ctx.user.id, ctx.guild.id, "economy_lb_row") \
                ).format(index=str(i + 1), name=member, amount=str(v['Wallet'] + v['Bank']))

            if (i + 1) % 10 == 0:
                p.append(cur_page)
                cur_page = ""

        if len(cur_page) > 0:
            p.append(cur_page)

        paginator = pages.Paginator(p)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @economics_subcommands.command(name='shop', description='View items in shop')
    @is_module_enabled("economy")
    async def shop(self, ctx: discord.ApplicationContext):
        cur_page = ""
        p = []

        client = get_client()

        records = await client['Shop'].find({
            'GuildID': str(ctx.guild.id)
        }).to_list()


        if len(records) == 0:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_shop_empty", append_tip=True), ephemeral=True)
            return

        for i, v in enumerate(records):
            cur_page += (await trl(ctx.user.id, ctx.guild.id, "economy_shop_row")).format(index=str(i + 1),
                                                                                  identifier=v['Identifier'],
                                                                                  price=str(v['Price']))

            if (i + 1) % 10 == 0:
                p.append(cur_page)
                cur_page = ""

        if len(cur_page) > 0:
            p.append(cur_page)

        paginator = pages.Paginator(p)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @economics_subcommands.command(name='buy', description='Buy an item')
    @is_module_enabled("economy")
    async def buy(self, ctx: discord.ApplicationContext, identifier: str):
        client = get_client()
        if await client['Inventory'].count_documents({'Identifier': identifier, 'UserID': str(ctx.user.id), 'GuildID': str(ctx.guild.id)}) > 0:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_buy_own", append_tip=True), ephemeral=True)
            return

        shop_item = await client['Shop'].find_one({'Identifier': identifier, 'GuildID': str(ctx.guild.id)})
        if not shop_item:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_buy_not_found", append_tip=True), ephemeral=True)
            return

        if shop_item['Price'] > (await get_akacoins(ctx.user.id))[0]:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_buy_poor", append_tip=True), ephemeral=True)
            return

        await rem_akacoins(ctx.user.id, shop_item['Price'])
        await client['Inventory'].insert_one({
            'GuildID': str(ctx.guild.id),
            'UserID': str(ctx.user.id),
            'Identifier': identifier,
            'Type': shop_item['Type'],
            'Price': shop_item['Price'],
            'AllowSell': shop_item['AllowSell'],
            'AllowTrade': shop_item['AllowTrade']
        })


        if shop_item['Type'] == 'role' and 'RoleID' in shop_item:
            role = ctx.guild.get_role(int(shop_item['RoleID']))
            if role:
                await ctx.user.add_roles(role)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_buy_success", append_tip=True)
                          ).format(identifier=identifier), ephemeral=True)

    @economics_subcommands.command(name='inventory', description='View items in inventory')
    @is_module_enabled("economy")
    async def inventory(self, ctx: discord.ApplicationContext):
        cur_page = ""
        p = []

        client = get_client()
        records = await client['Inventory'].find({
            'UserID': str(ctx.user.id),
            'GuildID': str(ctx.guild.id)
        }).to_list()

        if len(records) == 0:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_inventory_empty", append_tip=True),
                              ephemeral=True)
            return

        for i, v in enumerate(records):
            sell_str = await trl(ctx.user.id, ctx.guild.id, "economy_item_sellable") if v['AllowSell'] \
                else await trl(ctx.user.id, ctx.guild.id, "economy_item_not_sellable")
            trade_str = await trl(ctx.user.id, ctx.guild.id, "economy_item_tradeable") if v['AllowTrade'] \
                else await trl(ctx.user.id, ctx.guild.id, "economy_item_not_tradeable")

            cur_page += (await trl(ctx.user.id, ctx.guild.id, "economy_shop_row")).format(index=str(i + 1),
                                                                                  identifier=v['Identifier'],
                                                                                  price=str(v['Price']),
                                                                                  sell_str=sell_str,
                                                                                  trade_str=trade_str)

            if (i + 1) % 10 == 0:
                p.append(cur_page)
                cur_page = ""

        if len(cur_page) > 0:
            p.append(cur_page)

        paginator = pages.Paginator(p)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @economics_subcommands.command(name='sell', description='Sell an item that is sellable.')
    @is_module_enabled("economy")
    async def sell(self, ctx: discord.ApplicationContext, identifier: str):
        client = get_client()
        inventory = await client['Inventory'].find_one({'Identifier': identifier, 'UserID': str(ctx.user.id), 'GuildID': str(ctx.guild.id)})
        if not inventory:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_sell_not_own", append_tip=True), ephemeral=True)
            return

        if not inventory['AllowSell']:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_sell_not_allowed", append_tip=True),
                              ephemeral=True)
            return

        await add_akacoins(ctx.user.id, inventory['Price'])
        await client['Inventory'].delete_one({'Identifier': identifier, 'UserID': str(ctx.user.id), 'GuildID': str(ctx.guild.id)})

        if inventory['Type'] == 'role':
            shop_item = await client['Shop'].find_one({'Identifier': identifier, 'GuildID': str(ctx.guild.id)})
            role = ctx.guild.get_role(int(shop_item['RoleID']))
            if role:
                await ctx.user.remove_roles(role)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_sell_success", append_tip=True)
                          ).format(identifier=identifier), ephemeral=True)

    @economics_subcommands.command(name='send', description='Send an item to another player.')
    @is_module_enabled("economy")
    async def send(self, ctx: discord.ApplicationContext, to: discord.Member, identifier: str):
        if to.id == ctx.user.id:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_send_self", append_tip=True), ephemeral=True)
            return

        client = get_client()

        inventory = await client['Inventory'].find_one({'Identifier': identifier, 'UserID': str(ctx.user.id), 'GuildID': str(ctx.guild.id)})
        if not inventory:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_sell_not_own", append_tip=True), ephemeral=True)
            return

        if not inventory['AllowTrade']:
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_send_not_allowed", append_tip=True),
                              ephemeral=True)
            return

        await client['Inventory'].delete_one({'Identifier': identifier, 'UserID': str(ctx.user.id), 'GuildID': str(ctx.guild.id)})
        await client['Inventory'].insert_one({
            'GuildID': str(ctx.guild.id),
            'UserID': str(to.id),
            'Identifier': identifier,
            'Type': inventory['Type'],
            'Price': inventory['Price'],
            'AllowSell': inventory['AllowSell'],
            'AllowTrade': inventory['AllowTrade']
        })

        if inventory['Type'] == 'role':
            shop_item = await client['Shop'].find_one({'Identifier': identifier, 'GuildID': str(ctx.guild.id)})
            role = ctx.guild.get_role(int(shop_item['RoleID']))
            if role:
                await ctx.user.remove_roles(role)
                await to.add_roles(role)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_send_success", append_tip=True)
                          ).format(identifier=identifier, target=to.display_name), ephemeral=True)

    @economics_subcommands.command(name='transfer', description='Transfer money between the bank and wallet')
    @is_module_enabled("economy")
    @discord.option(name='into', choices=['bank', 'wallet'])
    async def transfer(self, ctx: discord.ApplicationContext, into: str, amount: int):
        limit = int(await get_setting(ctx.guild.id, 'economy_transfer_limit', "-1"))

        if limit != -1 and amount > limit:
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_transfer_limit", append_tip=True)
                              ).format(limit=str(limit)), ephemeral=True)
            return

        cooldown = datetime.datetime.now() + datetime.timedelta(
            minutes=int(await get_setting(ctx.guild.id, 'economy_cooldown_minutes', "1")),
            hours=int(await get_setting(ctx.guild.id, 'economy_cooldown_hours', "1"))
        )

        client = get_client()

        # bank to wallet
        if into == 'wallet':
            data = await client['Economy'].find_one({'UserID': str(ctx.user.id)})
            if data['Bank'] < amount:
                await ctx.respond(
                    (await trl(ctx.user.id, ctx.guild.id, "economy_transfer_no_money_in_bank", append_tip=True)
                    ).format(bank=str(data['Bank']), amount=str(amount)),
                    ephemeral=True)
                return

            if 'TransferLimit' in data and data['TransferLimit'] > datetime.datetime.now():
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_transfer_cooldown", append_tip=True),
                                  ephemeral=True)
                return

            await client['Economy'].update_one({
                'UserID': str(ctx.user.id)
            }, {
                '$inc': {
                    'Bank': -amount,
                    'Wallet': amount
                },
                '$set': {
                    'TransferLimit': cooldown
                }
            })

            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_transfer_wallet", append_tip=True)
                              ).format(amount=str(amount)), ephemeral=True)
        elif into == 'bank':
            data = await client['Economy'].find_one({'UserID': str(ctx.user.id)})
            if data['Wallet'] < amount:
                await ctx.respond(
                    (await trl(ctx.user.id, ctx.guild.id, "economy_transfer_no_money_in_wallet", append_tip=True)
                    ).format(wallet=str(data['Wallet']), amount=str(amount)),
                    ephemeral=True)
                return

            if 'TransferLimit' in data and data['TransferLimit'] > datetime.datetime.now():
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "economy_transfer_cooldown", append_tip=True),
                                  ephemeral=True)
                return

            await client['Economy'].update_one({
                'UserID': str(ctx.user.id)
            }, {
                '$inc': {
                    'Wallet': -amount,
                    'Bank': amount
                },
                '$set': {
                    'TransferLimit': cooldown
                }
            })

            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_transfer_bank", append_tip=True)
                              ).format(amount=str(amount)), ephemeral=True)


    @economics_admin_subcommands.command(name='add', description='Add AkaCoins to a specific user')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name='location', choices=['wallet', 'bank'])
    async def admin_add(self, ctx: discord.ApplicationContext, user: discord.User, amount: int,
                        location: str = 'wallet'):
        await add_akacoins(user.id, amount, location=location)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_admin_add", append_tip=True)
                          ).format(amount=str(amount), name=user.display_name, location=location), ephemeral=True)

    @economics_admin_subcommands.command(name='remove', description='Remove AkaCoins from a specific user')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name='location', choices=['wallet', 'bank'])
    async def admin_remove(self, ctx: discord.ApplicationContext, user: discord.User, amount: int,
                           location: str = 'wallet'):
        await rem_akacoins(user.id, amount, location=location)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_admin_remove", append_tip=True)
                          ).format(amount=str(amount), name=user.display_name, location=location), ephemeral=True)

    @economics_admin_subcommands.command(name='set', description='Set AkaCoins for a specific user')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name='location', choices=['wallet', 'bank'])
    async def admin_set(self, ctx: discord.ApplicationContext, user: discord.User, amount: int,
                        location: str = 'wallet'):
        await set_akacoins(user.id, amount, location=location)

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_admin_set", append_tip=True)
                          ).format(amount=str(amount), name=user.display_name, location=location), ephemeral=True)

    @economics_admin_subcommands.command(name='balance', description='Get another user\'s balance.')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    async def admin_balance(self, ctx: discord.ApplicationContext, user: discord.User):
        wallet, bank = get_akacoins(user.id)

        await ctx.respond(
            (await trl(ctx.user.id, ctx.guild.id, "economy_admin_balance", append_tip=True)
            ).format(name=user.display_name, wallet=str(wallet), bank=str(bank)),
            ephemeral=True)

    @economics_admin_subcommands.command(name='reset', description='Reset AkaCoins for a specific user')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    @discord.option(name='location', choices=['wallet', 'bank'])
    async def admin_reset(self, ctx: discord.ApplicationContext, user: discord.User):
        await set_akacoins(user.id, 0, 'wallet')
        await set_akacoins(user.id, 0, 'bank')

        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_admin_reset", append_tip=True)
                          ).format(name=user.display_name), ephemeral=True)

    @economics_admin_subcommands.command(name='add_role_on_sale',
                                         description='Put a role on sale, so people can purchase it.')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    async def add_role_to_shop(self, ctx: discord.ApplicationContext, role: discord.Role, identifier: str, price: int,
                               allow_sell: bool = True, allow_trade: bool = True):
        if ctx.me.top_role.position < role.position or not ctx.me.guild_permissions.manage_roles:
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "verification_set_role_no_perms", append_tip=True),
                ephemeral=True)
            return

        client = get_client()

        await client['Shop'].update_one({
            'RoleID': role.id,
        }, {
            '$set': {
                'GuildID': ctx.guild.id,
                'Type': 'role',
                'Identifier': identifier,
                'Price': price,
                'AllowSell': allow_sell,
                'AllowTrade': allow_trade
            }
        }, upsert=True)


        sell_str = await trl(ctx.user.id, ctx.guild.id, "economy_item_sellable") if allow_sell \
            else await trl(ctx.user.id, ctx.guild.id, "economy_item_not_sellable")
        trade_str = await trl(ctx.user.id, ctx.guild.id, "economy_item_tradeable") if allow_trade \
            else await trl(ctx.user.id, ctx.guild.id, "economy_item_not_tradeable")
        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_admin_role_on_sale", append_tip=True)
                          ).format(role=role.mention, price=str(price), sell_str=sell_str, trade_str=trade_str),
                          ephemeral=True)

    @economics_admin_subcommands.command(name='remove_role_from_sale',
                                         description='Remove a role from sale, no one will be able to purchase it.')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    async def remove_role_from_shop(self, ctx: discord.ApplicationContext, role: discord.Role):
        client = get_client()

        await client['Shop'].delete_one({
            'RoleID': role.id,
            'GuildID': ctx.guild.id,
            'Type': 'role'
        })


        await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "economy_admin_role_removed", append_tip=True)
                          ).format(role=role.mention), ephemeral=True)

    @economics_admin_subcommands.command(name='set_transfer_limits',
                                         description='Set transfer (bank <=> wallet) limits.')
    @is_module_enabled("economy")
    @commands_ext.has_permissions(manage_guild=True)
    async def set_transfer_limits(self, ctx: discord.ApplicationContext, amount: int, cooldown_minutes: int,
                                  cooldown_hours: int):
        await set_setting(ctx.guild.id, 'economy_transfer_limit', str(amount))
        await set_setting(ctx.guild.id, 'economy_cooldown_minutes', str(cooldown_minutes))
        await set_setting(ctx.guild.id, 'economy_cooldown_hours', str(cooldown_hours))

        await ctx.respond(
            (await trl(ctx.user.id, ctx.guild.id, "economy_admin_role_set_limits", append_tip=True)
            ).format(amount=str(amount), cooldown_minutes=str(cooldown_minutes), cooldown_hours=str(cooldown_hours)),
            ephemeral=True)

    @economics_admin_subcommands.command(name='set_gambling', description="Set various gambling settings")
    @is_module_enabled("economy")
    @discord.option(name='start_min_chance', description='The minimum chance to have when starting a new gamble. (80%)')
    @discord.option(name='start_max_chance',
                    description='The maximum chance to have when starting a new gamble. (100%)')
    @discord.option(name='factor',
                    description='Factor that if higher will decrease the chance more every gamble. (1.1)')
    @discord.option(name='amount_increase_min_percentage', description='Minimum percentage of increase. (110%)')
    @discord.option(name='amount_increase_max_percentage', description='Maximum percentage of increase. (200%)')
    @commands_ext.has_permissions(manage_guild=True)
    async def set_gambling(self, ctx: discord.ApplicationContext, start_min_chance: int = -1,
                           start_max_chance: int = -1, factor: float = -1, amount_increase_min_percentage: int = -1,
                           amount_increase_max_percentage: int = -1):
        if start_min_chance != -1:
            await set_setting(ctx.guild.id, "economy_gambling_start_min_chance", str(start_min_chance))
        if start_max_chance != -1:
            await set_setting(ctx.guild.id, "economy_gambling_start_max_chance", str(start_max_chance))
        if factor != -1:
            await set_setting(ctx.guild.id, "economy_gambling_factor", str(factor))
        if amount_increase_min_percentage != -1:
            await set_setting(ctx.guild.id, "economy_gambling_amount_increase_min_percentage",
                              str(amount_increase_min_percentage))
        if amount_increase_max_percentage != -1:
            await set_setting(ctx.guild.id, "economy_gambling_amount_increase_max_percentage",
                              str(amount_increase_max_percentage))

        await ctx.respond("Settings were saved.", ephemeral=True)

    @economics_admin_subcommands.command(name='set_daily_weekly', description="Set various daily/weekly settings")
    @is_module_enabled("economy")
    @discord.option(name='daily_min', description='Minimum daily money (50)')
    @discord.option(name='daily_max', description='Maximum daily money (500)')
    @discord.option(name='weekly_min', description='Minimum weekly money (250)')
    @discord.option(name='weekly_max', description='Maximum weekly money (2500)')
    @commands_ext.has_permissions(manage_guild=True)
    async def set_gambling(self, ctx: discord.ApplicationContext, daily_min: int = -1,
                           daily_max: int = -1, weekly_min: int = -1, weekly_max: int = -1):
        if daily_min != -1:
            await set_setting(ctx.guild.id, "economy_daily_min", str(daily_min))
        if daily_max != -1:
            await set_setting(ctx.guild.id, "economy_daily_max", str(daily_max))
        if weekly_min != -1:
            await set_setting(ctx.guild.id, "economy_weekly_min", str(weekly_min))
        if weekly_max != -1:
            await set_setting(ctx.guild.id, "economy_weekly_max", str(weekly_max))

        await ctx.respond("Settings were saved.", ephemeral=True)

    @economics_admin_subcommands.command(name='set_work', description="Set various work settings")
    @is_module_enabled("economy")
    @discord.option(name='work_min', description='Minimum work money (150)')
    @discord.option(name='work_max', description='Maximum work money (400)')
    @discord.option(name='bonus_min', description='Minimum bonus money (0)')
    @discord.option(name='bonus_max', description='Maximum bonus money (100)')
    @discord.option(name='bonus_chance', description='Bonus money chance (80)')
    @discord.option(name='bonus_chance_lose', description='Bonus money lose chance (10)')
    @commands_ext.has_permissions(manage_guild=True)
    async def set_gambling(self, ctx: discord.ApplicationContext, work_min: int = -1,
                           work_max: int = -1, bonus_min: int = -1, bonus_max: int = -1, bonus_chance: int = -1,
                           bonus_chance_lose: int = -1):
        if work_min != -1:
            await set_setting(ctx.guild.id, "economy_work_min", str(work_min))
        if work_max != -1:
            await set_setting(ctx.guild.id, "economy_work_max", str(work_max))
        if bonus_min != -1:
            await set_setting(ctx.guild.id, "economy_work_bonus_min", str(bonus_min))
        if bonus_max != -1:
            await set_setting(ctx.guild.id, "economy_work_bonus_max", str(bonus_max))
        if bonus_chance != -1:
            await set_setting(ctx.guild.id, "economy_work_bonus_chance", str(bonus_chance))
        if bonus_chance_lose != -1:
            await set_setting(ctx.guild.id, "economy_work_bonus_chance_lose", str(bonus_chance_lose))

        await ctx.respond("Settings were saved.", ephemeral=True)

    @economics_admin_subcommands.command(name='set_rob', description="Set various rob settings")
    @is_module_enabled("economy")
    @discord.option(name='chance', description='Rob success chance (60%)')
    @discord.option(name='min_money', description='Minimum money required for robbing (25)')
    @discord.option(name='stolen_percentage_min', description='Minimum percentage of stolen (10%)')
    @discord.option(name='stolen_percentage_max', description='Maximum percentage of stolen (25%)')
    @discord.option(name='fine_percentage_min', description='Minimum percentage of fine (10%)')
    @discord.option(name='fine_percentage_max', description='Maximum percentage of fine (200%)')
    @commands_ext.has_permissions(manage_guild=True)
    async def set_gambling(self, ctx: discord.ApplicationContext, chance: int = -1, min_money: int = -1,
                           stolen_percentage_min: int = -1, stolen_percentage_max: int = -1,
                           fine_percentage_min: int = -1, fine_percentage_max: int = -1):
        if chance != -1:
            await set_setting(ctx.guild.id, "economy_rob_chance", str(chance))
        if min_money != -1:
            await set_setting(ctx.guild.id, "economy_rob_min_money", str(min_money))
        if stolen_percentage_min != -1:
            await set_setting(ctx.guild.id, "economy_rob_stolen_percentage_min", str(stolen_percentage_min))
        if stolen_percentage_max != -1:
            await set_setting(ctx.guild.id, "economy_rob_stolen_percentage_max", str(stolen_percentage_max))
        if fine_percentage_min != -1:
            await set_setting(ctx.guild.id, "economy_rob_fine_percentage_min", str(fine_percentage_min))
        if fine_percentage_max != -1:
            await set_setting(ctx.guild.id, "economy_rob_fine_percentage_max", str(fine_percentage_max))

        await ctx.respond("Settings were saved.", ephemeral=True)
