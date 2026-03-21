import discord
from discord.ext.pages import Paginator

from database import client


class AlreadyPinnedView(discord.ui.View):
    def __init__(self, user: discord.User, msg: discord.Message):
        super().__init__(timeout=120, disable_on_timeout=True)

        self.user = user
        self.msg = msg

    @discord.ui.button(label="Remove from pinned")
    async def remove_from_pinned(self, button: discord.Button, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.respond("Not your interaction", ephemeral=True)
            return

        client['UserPins'].delete_one({
            "User": str(self.user.id),
            "Message": str(self.msg.id)
        })

        self.stop()
        self.disable_all_items()
        await interaction.edit(view=self)


class MessagePinnedView(discord.ui.View):
    def __init__(self, msg: discord.Message):
        super().__init__(timeout=300, disable_on_timeout=True)

        self.msg = msg

    @discord.ui.button(label="Pin it for me too!", style=discord.ButtonStyle.primary)
    async def pin_for_me_too(self, button: discord.Button, interaction: discord.Interaction):
        a = client['UserPins'].find_one({
            "User": str(interaction.user.id),
            "Message": str(self.msg.id)
        })

        if a is not None:
            await interaction.respond("This message is already pinned for you, do you want to remove it instead?",
                view=AlreadyPinnedView(interaction.user, self.msg), ephemeral=True)
            return

        # Size check
        if client['UserPins'].count_documents({"User": str(interaction.user.id)}) > 1000:
            await interaction.respond("You have reached the pinned limit. (1000)", ephemeral=True)
            return

        client['UserPins'].insert_one({
            "User": str(interaction.user.id),
            "Message": str(self.msg.id),
            "Link": self.msg.jump_url
        })

        await interaction.respond(
            "Message was pinned for you. Add the bot to view your pinned messages, pin any message and more.",
           view=AddTheBot(), ephemeral=True)

class AddTheBot(discord.ui.View):
    def __init__(self):
        super().__init__(
            discord.ui.Button(label="Add the bot!", url="https://discord.com/discovery/applications/1172922944033411243"),
            timeout=None
        )


class UserPins(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        super().__init__()

        self.bot = bot

    @discord.message_command(name="Pin This", integration_types=[discord.IntegrationType.user_install])
    async def manage_user_pin(self, ctx: discord.ApplicationContext, message: discord.Message):
        a = client['UserPins'].find_one({
            "User": str(ctx.user.id),
            "Message": str(message.id)
        })

        if a is not None:
            await ctx.respond("This message is already pinned for you, do you want to remove it instead?",
                view=AlreadyPinnedView(ctx.user, message), ephemeral=True)
            return

        # Size check
        if client['UserPins'].count_documents({"User": str(ctx.user.id)}) > 1000:
            await ctx.respond("You have reached the pinned limit. (1000)", ephemeral=True)
            return

        client['UserPins'].insert_one({
            "User": str(ctx.user.id),
            "Message": str(message.id),
            "Link": message.jump_url
        })

        await ctx.respond("Message was pinned for you.", view=MessagePinnedView(message))

    pins_group = discord.SlashCommandGroup(name="pins", integration_types=[discord.IntegrationType.user_install])

    @pins_group.command(name="list", integration_types=[discord.IntegrationType.user_install])
    async def view_pins(self, ctx: discord.ApplicationContext):
        pins = client['UserPins'].find({
            "User": str(ctx.user.id)
        }).to_list()

        if len(pins) == 0:
            await ctx.respond("You do not have any pins", ephemeral=True)
            return

        pages = []
        page = ""
        a = 0

        for i in pins:
            page += f"{a + 1}. {i['Link']}\n"
            a += 1

            if a == 10:
                pages.append(page)
                page = ""

        if a > 0:
            pages.append(page)

        pagination = Paginator(pages)
        await pagination.respond(ctx.interaction, ephemeral=True)

    @pins_group.command(name="unpin", integration_types=[discord.IntegrationType.user_install])
    async def unpin(self, ctx: discord.ApplicationContext, num: int):
        pins = client['UserPins'].find({
            "User": str(ctx.user.id)
        }).to_list()

        if num < 1:
            await ctx.respond("Invalid number", ephemeral=True)
            return

        if num > len(pins):
            await ctx.respond("Invalid number", ephemeral=True)
            return

        pin_id = pins[num - 1]
        client['UserPins'].delete_one({'_id': pin_id['_id']})
        await ctx.respond(f"Unpinned post {pin_id['Link']}", ephemeral=True)
