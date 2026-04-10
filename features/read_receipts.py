from discord import Cog, Bot, Message, slash_command, Interaction, ApplicationContext, ButtonStyle, Button, \
    IntegrationType
from discord.ui import View, button

from database import client


async def update_message(message: Message | Interaction):
    msg_id = 0
    if isinstance(message, Message):
        msg_id = message.id
    elif isinstance(message, Interaction):
        msg_id = message.message.id
    else:
        raise ValueError("Invalid type passed to update_message")

    data = client["ReadReceipts"].find({"MessageID": str(msg_id)}).to_list()
    data.reverse()

    if len(data) == 0:
        output = "So far no one has marked this as read..."
    elif len(data) == 1:
        output = f"Marked as read by <@{data[0]['UserID']}>"
    elif 1 < len(data) < 4:
        output = "Marked as read by " + ", ".join(
            [f"<@{i['UserID']}>" for i in data[:-1]]) + " and " + f"<@{data[-1]['UserID']}>."
    else:
        output = "Marked as read by " + ", ".join([f"<@{i['UserID']}>" for i in data[:3]]) + " and " + str(
            len(data) - 3) + " others."

    if isinstance(message, Message):
        await message.edit(content=output)
    elif isinstance(message, Interaction):
        await message.edit(content=output)


class ReadReceiptView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Mark as Read", style=ButtonStyle.primary, custom_id="read_receipt")
    async def mark_as_read(self, button: Button, interaction: Interaction):
        if client["ReadReceipts"].find_one(
                {"UserID": str(interaction.user.id), "MessageID": str(interaction.message.id)}) is not None:
            await interaction.respond("Already marked this one as read!", ephemeral=True)
            return

        client["ReadReceipts"].insert_one({
            "UserID": str(interaction.user.id),
            "MessageID": str(interaction.message.id)
        })

        await update_message(interaction)


class ReadReceipts(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ReadReceiptView())

    @slash_command(integration_types=[IntegrationType.guild_install, IntegrationType.user_install])
    async def read_receipt(self, ctx: ApplicationContext):
        await ctx.respond("So far no one read this.", view=ReadReceiptView())
