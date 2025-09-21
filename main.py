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

class CreateTicketButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="📩 Create Ticket",
            custom_id="ticket_create_v2"  # Changed for uniqueness
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Check bot permissions
            if not interaction.guild.me.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ I need `Manage Channels` permissions!",
                    ephemeral=True
                )
                return

            # Prevent duplicate tickets
            if interaction.user.id in open_tickets:
                await interaction.response.send_message(
                    "You already have an open ticket!",
                    ephemeral=True
                )
                return

            # Create ticket channel
            category = discord.utils.get(interaction.guild.categories, name=TICKET_CATEGORY_NAME)
            if not category:
                category = await interaction.guild.create_category(TICKET_CATEGORY_NAME)

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            
            mod_role = discord.utils.get(interaction.guild.roles, name=MOD_ROLE_NAME)
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                overwrites=overwrites,
                category=category
            )
            open_tickets[interaction.user.id] = channel.id

            # Send ticket message
            embed = discord.Embed(title="Support Ticket", description=f"Hello {interaction.user.mention}, a staff member will assist you shortly.")
            await channel.send(
                content=f"{interaction.user.mention} {mod_role.mention if mod_role else ''}",
                embed=embed,
                view=ManageTicketView()
            )
            
            await interaction.response.send_message(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            print(f"TICKET ERROR: {e}")
            await interaction.response.send_message(
                "❌ Failed to create ticket. Please contact an admin.",
                ephemeral=True
            )

# Update the view to use the new button
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CreateTicketButton())

class ManageTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())
        self.add_item(DeleteTicketButton())

class CloseTicketButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Close Ticket",
            emoji="🔒",
            custom_id="close_ticket_v2"  # Updated custom_id
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Check MOD permissions
            mod_role = discord.utils.get(interaction.guild.roles, name=MOD_ROLE_NAME)
            if mod_role not in interaction.user.roles:
                await interaction.response.send_message(
                    "❌ You need MOD role to close tickets.",
                    ephemeral=True
                )
                return

            # Get the ticket opener's username
            opener = None
            for uid, cid in list(open_tickets.items()):
                if cid == interaction.channel.id:
                    opener = interaction.guild.get_member(uid)
                    break

            # Rename channel to "closed-username"
            if opener:
                new_name = f"closed-{opener.name}"[:32]  # Discord channel names max 32 chars
                try:
                    await interaction.channel.edit(name=new_name)
                except:
                    new_name = f"closed-{opener.id}"  # Fallback to ID if name fails
                    await interaction.channel.edit(name=new_name[:32])

            # Lock the channel
            await interaction.channel.set_permissions(
                interaction.guild.default_role,
                view_channel=False
            )

            # Update open_tickets dict
            if opener and opener.id in open_tickets:
                del open_tickets[opener.id]

            await interaction.response.send_message(
                f"🔒 Ticket closed by {interaction.user.mention}. "
                f"Renamed to `{new_name}`.",
                ephemeral=False
            )

        except Exception as e:
            print(f"CLOSE TICKET ERROR: {e}")
            await interaction.response.send_message(
                "❌ Failed to close ticket. Please try again.",
                ephemeral=True
            )

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
    
    if ctx.channel.name != "〘✍〙⪼registration":
        await ctx.send("❌ You can only use this command in <#1386727438293139638>")
        return
        
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
    
    if ctx.channel.name != "〘✍〙⪼registration":
        await ctx.send("❌ You can only use this command in <#1386727438293139638>")
        return

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
async def setslots(ctx, number: int):
    global MAX_SLOTS, registered_users, list_message_id

    if number < 1 or number > 100:
        await ctx.send("❌ Please choose a number between 1 and 100.")
        return

    MAX_SLOTS = number

    # Reset current list when slots change
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

    await ctx.send(f"✅ Registration slots updated to **{MAX_SLOTS}**. A new list has been created.")
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
