import discord
from discord.ext import commands
from discord.ui import View, Button
import os
from flask import Flask
from threading import Thread
import asyncio

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_web)
    thread.start()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

MOD_ROLE_NAME = "MOD"
TICKET_CATEGORY_NAME = "【support】"
ROLE_NAME = "REGISTERED"
CHANNEL_NAME = "〘📝〙⪼registered"
REGISTRATION_CHANNEL_NAME = "〘✍〙⪼registration"
registered_users = {}  # Dictionary to store slot positions
open_tickets = {}  # Dictionary to track open tickets
list_message_id = None
MAX_SLOTS = 10  # Maximum number of registration slots

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CreateTicketButton())

class CreateTicketButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="📩 Create ticket", custom_id="create_ticket")

    async def callback(self, interaction: discord.Interaction):
        try:
            user = interaction.user
            guild = interaction.guild

            if user.id in open_tickets:
                await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
                return

            mod_role = discord.utils.get(guild.roles, name=MOD_ROLE_NAME)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
            if not category:
                category = await guild.create_category(TICKET_CATEGORY_NAME)

            channel = await guild.create_text_channel(f"ticket-{user.name}", overwrites=overwrites, category=category)
            open_tickets[user.id] = channel.id

            embed = discord.Embed(
                title="📅 Support Ticket",
                description=f"Hello {user.mention}, a staff member will be with you shortly.\nUse the buttons below to manage the ticket.",
                color=0x3498db
            )
            await channel.send(content=user.mention, embed=embed, view=ManageTicketView())
            await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        except Exception as e:
            print(f"Error creating ticket: {e}")
            await interaction.response.send_message("An error occurred while creating the ticket.", ephemeral=True)

class ManageTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())
        self.add_item(DeleteTicketButton())

class CloseTicketButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Close Ticket", emoji="🔒", custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        try:
            mod_role = discord.utils.get(interaction.guild.roles, name=MOD_ROLE_NAME)
            if mod_role not in interaction.user.roles:
                await interaction.response.send_message("You don't have permission to close this ticket.", ephemeral=True)
                return

            await interaction.channel.set_permissions(interaction.channel.guild.default_role, view_channel=False)
            await interaction.response.send_message("🔒 Ticket closed. Only MODs can access now.", ephemeral=False)
        except Exception as e:
            print(f"Error closing ticket: {e}")
            await interaction.response.send_message("An error occurred while closing the ticket.", ephemeral=True)

class DeleteTicketButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Delete Ticket", emoji="❌", custom_id="delete_ticket")

    async def callback(self, interaction: discord.Interaction):
        try:
            mod_role = discord.utils.get(interaction.guild.roles, name=MOD_ROLE_NAME)
            if mod_role not in interaction.user.roles:
                await interaction.response.send_message("You don't have permission to delete this ticket.", ephemeral=True)
                return

            for uid, cid in list(open_tickets.items()):
                if cid == interaction.channel.id:
                    del open_tickets[uid]
                    break

            await interaction.response.send_message("Ticket will be deleted in 3 seconds...", ephemeral=True)
            await asyncio.sleep(3)
            await interaction.channel.delete()
        except Exception as e:
            print(f"Error deleting ticket: {e}")
            await interaction.response.send_message("An error occurred while deleting the ticket.", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(ManageTicketView())
    print(f"🟢 Bot is online as {bot.user}")

@bot.command()
async def register(ctx):
    global list_message_id

    guild = ctx.guild
    member = ctx.author

    await ctx.message.add_reaction("<:VerifiedBabyPink:1361409947195412745>")

    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not role:
        print("❌ Role not found.")
        return
    if role in member.roles:
        await ctx.send(f"{member.mention}, you are already registered.")
        return
    await member.add_roles(role)

    if member.id in registered_users.values():
        return

    slot = None
    for i in range(1, MAX_SLOTS + 1):
        if i not in registered_users:
            slot = i
            break

    if slot is None:
        await ctx.send(f"{member.mention}, all registration slots are full!")
        return

    registered_users[slot] = member.id

    content = "**Registered Users:**\n"
    for i in range(1, MAX_SLOTS + 1):
        if i in registered_users:
            content += f"{i}. <@{registered_users[i]}>\n"
        else:
            content += f"{i}.\n"

    channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
    if not channel:
        print("❌ Channel not found.")
        return

    if list_message_id:
        try:
            msg = await channel.fetch_message(list_message_id)
            await msg.edit(content=content)
        except:
            sent = await channel.send(content)
            list_message_id = sent.id
    else:
        sent = await channel.send(content)
        list_message_id = sent.id

@bot.command()
async def unregister(ctx, member: discord.Member = None):
    global list_message_id

    guild = ctx.guild

    if member is None:
        member = ctx.author
    else:
        if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_roles):
            await ctx.send(f"{ctx.author.mention}, you don't have permission to unregister other members.")
            return

    await ctx.message.add_reaction("<:VerifiedBabyPink:1361409947195412745>")

    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not role:
        print("❌ Role not found.")
        return

    if role not in member.roles:
        await ctx.send(f"{member.mention} is not registered.")
        return

    await member.remove_roles(role)

    slot_to_remove = None
    for slot, user_id in registered_users.items():
        if user_id == member.id:
            slot_to_remove = slot
            break

    if slot_to_remove:
        del registered_users[slot_to_remove]

    content = "**Registered Users:**\n"
    for i in range(1, MAX_SLOTS + 1):
        if i in registered_users:
            content += f"{i}. <@{registered_users[i]}>\n"
        else:
            content += f"{i}.\n"

    channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
    if not channel:
        print("❌ Channel not found.")
        return

    if list_message_id:
        try:
            msg = await channel.fetch_message(list_message_id)
            await msg.edit(content=content)
        except:
            sent = await channel.send(content)
            list_message_id = sent.id
    else:
        sent = await channel.send(content)
        list_message_id = sent.id

    await ctx.send(f"{member.mention} has been unregistered.")

@bot.command()
@commands.has_role("MOD")
async def send(ctx, *, message: str):
    await ctx.send(message)
    await ctx.message.delete()

@bot.command()
@commands.has_role("MOD")
async def lock(ctx):
    guild = ctx.guild
    channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL_NAME)
    private_role = discord.utils.get(guild.roles, name="PRIVATE")

    if channel and private_role:
        try:
            await channel.set_permissions(private_role, read_messages=True, send_messages=False)
            await ctx.send("# Registration is closed.")
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to change the channel permissions.")
    else:
        await ctx.send("Channel or role not found.")

@bot.command()
@commands.has_role("MOD")
async def unlock(ctx):
    guild = ctx.guild
    channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL_NAME)
    private_role = discord.utils.get(guild.roles, name="PRIVATE")

    if channel and private_role:
        try:
            await channel.set_permissions(private_role, read_messages=True, send_messages=True)
            await ctx.send("# Registration is open.")
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to change the channel permissions.")
    else:
        await ctx.send("Channel or role not found.")

@bot.command()
@commands.has_role("MOD")
async def newlist(ctx):
    global registered_users, list_message_id

    if ctx.channel.name != REGISTRATION_CHANNEL_NAME:
        await ctx.send("❌ You can only use this command in the registration channel.")
        return

    registered_users = {}
    content = "**Registered Users:**\n"
    for i in range(1, MAX_SLOTS + 1):
        content += f"{i}.\n"

    channel = discord.utils.get(ctx.guild.text_channels, name=CHANNEL_NAME)
    if not channel:
        await ctx.send("❌ Channel not found.")
        return

    sent = await channel.send(content)
    list_message_id = sent.id
    await ctx.send("✅ New registration list created.")
    await ctx.message.delete()

@bot.command()
@commands.has_role("MOD")
async def registeruser(ctx, member: discord.Member):
    global list_message_id

    if ctx.channel.name != REGISTRATION_CHANNEL_NAME:
        await ctx.send("❌ You can only use this command in the registration channel.")
        return

    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not role:
        await ctx.send("❌ REGISTERED role not found.")
        return

    if role in member.roles:
        await ctx.send(f"{member.mention} is already registered.")
        return

    await member.add_roles(role)

    if member.id in registered_users.values():
        await ctx.send("User is already on the list.")
        return

    slot = None
    for i in range(1, MAX_SLOTS + 1):
        if i not in registered_users:
            slot = i
            break

    if slot is None:
        await ctx.send("All slots are full!")
        return

    registered_users[slot] = member.id

    content = "**Registered Users:**\n"
    for i in range(1, MAX_SLOTS + 1):
        if i in registered_users:
            content += f"{i}. <@{registered_users[i]}>\n"
        else:
            content += f"{i}.\n"

    channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
    if not channel:
        await ctx.send("❌ Channel not found.")
        return

    if list_message_id:
        try:
            msg = await channel.fetch_message(list_message_id)
            await msg.edit(content=content)
        except:
            sent = await channel.send(content)
            list_message_id = sent.id
    else:
        sent = await channel.send(content)
        list_message_id = sent.id

    await ctx.send(f"{member.mention} has been registered manually.")
    await ctx.message.delete()

@bot.command()
@commands.has_role(MOD_ROLE_NAME)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="Support Ticket",
        description="Click below to create a support ticket 📩",
        color=0x2ecc71
    )
    await ctx.send(embed=embed, view=TicketView())

keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
