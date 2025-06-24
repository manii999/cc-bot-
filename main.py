import discord
from discord.ext import commands
import os

from flask import Flask
from threading import Thread

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

ROLE_NAME = "REGISTERED"
CHANNEL_NAME = "〘📝〙⪼registered"
registered_users = {}  # Dictionary to store slot positions
list_message_id = None
MAX_SLOTS = 10  # Maximum number of registration slots

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.idle)  # Set the bot status to idle
    print(f"🟡Bot is idle as {bot.user}")

@bot.command()
async def register(ctx):
    global list_message_id

    guild = ctx.guild
    member = ctx.author

    # React to message
    await ctx.message.add_reaction("<:VerifiedBabyPink:1361409947195412745>")

    # Give role
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not role:
        print("❌ Role not found.")
        return
    if role in member.roles:
        await ctx.send(f"{member.mention}, you are already registered.")
        return
    await member.add_roles(role)

    # Add user to list if not already added
    if member.id in registered_users.values():
        return

    # Find the first empty slot
    slot = None
    for i in range(1, MAX_SLOTS + 1):
        if i not in registered_users:
            slot = i
            break

    if slot is None:
        await ctx.send(f"{member.mention}, all registration slots are full!")
        return

    registered_users[slot] = member.id

    # Format the list with all slots
    content = "**Registered Users:**\n"
    for i in range(1, MAX_SLOTS + 1):
        if i in registered_users:
            content += f"{i}. <@{registered_users[i]}>\n"
        else:
            content += f"{i}.\n"

    # Find channel
    channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
    if not channel:
        print("❌ Channel not found.")
        return

    # Edit or send list
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

    # If no member specified, unregister the command author
    if member is None:
        member = ctx.author
    else:
        # Check if user has permission to unregister others (admin or manage roles)
        if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_roles):
            await ctx.send(f"{ctx.author.mention}, you don't have permission to unregister other members.")
            return

    # React to message
    await ctx.message.add_reaction("<:VerifiedBabyPink:1361409947195412745>")

    # Remove role
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if not role:
        print("❌ Role not found.")
        return

    if role not in member.roles:
        await ctx.send(f"{member.mention} is not registered.")
        return

    await member.remove_roles(role)

    # Remove user from registered list
    slot_to_remove = None
    for slot, user_id in registered_users.items():
        if user_id == member.id:
            slot_to_remove = slot
            break

    if slot_to_remove:
        del registered_users[slot_to_remove]

    # Update the list
    content = "**Registered Users:**\n"
    for i in range(1, MAX_SLOTS + 1):
        if i in registered_users:
            content += f"{i}. <@{registered_users[i]}>\n"
        else:
            content += f"{i}.\n"

    # Find channel
    channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
    if not channel:
        print("❌ Channel not found.")
        return

    # Edit or send list
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
@commands.has_role("MOD")  # Restrict the command to users with the "MOD" role
async def send(ctx, *, message: str):
    # This command lets the bot send a message in the same channel where it was invoked
    await ctx.send(message)
    await ctx.message.delete()  # Delete the command message sent by the user

@bot.command()
@commands.has_role("MOD")  # Restrict the command to users with the "MOD" role
async def lock(ctx):
    """Lock the registration channel for members with the PRIVATE role."""
    guild = ctx.guild
    channel = discord.utils.get(guild.text_channels, name="〘✍〙⪼registration")
    private_role = discord.utils.get(guild.roles, name="PRIVATE")

    if channel and private_role:
        try:
            # Set the permissions so the PRIVATE role can view, but not send messages
            await channel.set_permissions(private_role, read_messages=True, send_messages=False)
            await ctx.send("# Registration is closed.")
            await ctx.message.delete()  # Delete the command message sent by the user
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to change the channel permissions.")
    else:
        await ctx.send("Channel or role not found.")

@bot.command()
@commands.has_role("MOD")  # Restrict the command to users with the "MOD" role
async def unlock(ctx):
    """Unlock the registration channel for members with the PRIVATE role."""
    guild = ctx.guild
    channel = discord.utils.get(guild.text_channels, name="〘✍〙⪼registration")
    private_role = discord.utils.get(guild.roles, name="PRIVATE")

    if channel and private_role:
        try:
            # Set permissions to allow sending messages
            await channel.set_permissions(private_role, read_messages=True, send_messages=True)
            await ctx.send("# Registration is open.")
            await ctx.message.delete()  # Delete the command message sent by the user
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to change the channel permissions.")
    else:
        await ctx.send("Channel or role not found.")

keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
