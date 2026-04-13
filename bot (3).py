# bot.py
import discord
from discord.ext import commands
import json
import os
import random
from keepalive import keep_alive

# ─── CONFIG ───────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")
SETTINGS_FILE = "settings.json"
MAX_MESSAGES = 20
PREFIX = "$"
# ──────────────────────────────────────────────────────────

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "vouch_channel_id": None,
        "sender_role_id": None,
        "target_role_id": None,
        "messages": []
    }

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

settings = load_settings()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# ─────────────────────────────────────────────────────────
# HELP COMMAND
# ─────────────────────────────────────────────────────────

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="📖 Vouch Bot — Help",
        description="All commands use the `$` prefix. Admin-only commands require **Administrator** permission.",
        color=0x5865F2
    )
    embed.add_field(
        name="⚙️ Setup Commands (Admin only)",
        value=(
            "`$setchannel #channel` — Set where vouches are posted\n"
            "`$setsenderrole @role` — Role whose members trigger auto-vouch\n"
            "`$settargetrole @role` — Role shown in the vouch embed\n"
            "`$vouchsettings` — View current configuration"
        ),
        inline=False
    )
    embed.add_field(
        name=f"💬 Message Commands (Admin only, max {MAX_MESSAGES})",
        value=(
            "`$addmsg <text>` — Add a preset vouch message\n"
            "`$removemsg <number>` — Remove a message by its number\n"
            "`$listmsgs` — View all preset messages\n"
            "`$clearmsgs` — Remove ALL preset messages"
        ),
        inline=False
    )
    embed.add_field(
        name="✅ How It Works",
        value=(
            "1. Admin sets the channel, sender role, target role & messages\n"
            "2. Any member with the **sender role** sends a message anywhere\n"
            "3. Bot picks a **random preset message** and posts a vouch embed\n"
            "4. No interaction needed — fully automatic!"
        ),
        inline=False
    )
    embed.set_footer(text=f"Max preset messages: {MAX_MESSAGES} | Prefix: {PREFIX}")
    await ctx.send(embed=embed)

# ─────────────────────────────────────────────────────────
# ADMIN SETUP COMMANDS
# ─────────────────────────────────────────────────────────

@bot.command(name="setchannel")
@commands.check(is_admin)
async def set_channel(ctx, channel: discord.TextChannel):
    settings["vouch_channel_id"] = channel.id
    save_settings(settings)
    await ctx.send(f"✅ Vouch channel set to {channel.mention}")


@bot.command(name="setsenderrole")
@commands.check(is_admin)
async def set_sender_role(ctx, role: discord.Role):
    settings["sender_role_id"] = role.id
    save_settings(settings)
    await ctx.send(f"✅ Sender role set to **{role.name}** — members with this role will auto-vouch.")


@bot.command(name="settargetrole")
@commands.check(is_admin)
async def set_target_role(ctx, role: discord.Role):
    settings["target_role_id"] = role.id
    save_settings(settings)
    await ctx.send(f"✅ Target role set to **{role.name}** — this role will appear in vouch embeds.")


@bot.command(name="vouchsettings")
@commands.check(is_admin)
async def vouch_settings(ctx):
    guild = ctx.guild
    channel     = guild.get_channel(settings["vouch_channel_id"]) if settings["vouch_channel_id"] else None
    sender_role = guild.get_role(settings["sender_role_id"])       if settings["sender_role_id"]   else None
    target_role = guild.get_role(settings["target_role_id"])       if settings["target_role_id"]   else None
    msg_count   = len(settings["messages"])

    embed = discord.Embed(title="⚙️ Vouch Bot — Current Settings", color=0x5865F2)
    embed.add_field(name="Vouch Channel",   value=channel.mention      if channel     else "❌ Not set", inline=False)
    embed.add_field(name="Sender Role",     value=sender_role.mention  if sender_role else "❌ Not set", inline=False)
    embed.add_field(name="Target Role",     value=target_role.mention  if target_role else "❌ Not set", inline=False)
    embed.add_field(name="Preset Messages", value=f"{msg_count}/{MAX_MESSAGES}",                         inline=False)

    ready = all([channel, sender_role, target_role, msg_count > 0])
    embed.set_footer(text="✅ Bot is ready and active!" if ready else "⚠️ Setup incomplete — some settings missing.")
    await ctx.send(embed=embed)

# ─────────────────────────────────────────────────────────
# MESSAGE COMMANDS
# ─────────────────────────────────────────────────────────

@bot.command(name="addmsg")
@commands.check(is_admin)
async def add_message(ctx, *, message: str):
    msgs = settings["messages"]
    if len(msgs) >= MAX_MESSAGES:
        await ctx.send(f"❌ You've reached the **{MAX_MESSAGES} message limit**. Remove one with `$removemsg <number>` first.")
        return
    msgs.append(message)
    save_settings(settings)
    await ctx.send(f"✅ Message **#{len(msgs)}** added! (`{len(msgs)}/{MAX_MESSAGES}` slots used)")


@bot.command(name="removemsg")
@commands.check(is_admin)
async def remove_message(ctx, index: int):
    msgs = settings["messages"]
    if index < 1 or index > len(msgs):
        await ctx.send(f"❌ Invalid number. You have **{len(msgs)}** messages. Use `$listmsgs` to see them.")
        return
    removed = msgs.pop(index - 1)
    save_settings(settings)
    await ctx.send(f"✅ Removed message **#{index}**: `{removed}`\n(`{len(msgs)}/{MAX_MESSAGES}` slots used)")


@bot.command(name="listmsgs")
@commands.check(is_admin)
async def list_messages(ctx):
    msgs = settings["messages"]
    if not msgs:
        await ctx.send("❌ No preset messages yet. Use `$addmsg <text>` to add some.")
        return
    formatted = "\n".join(f"`{i+1}.` {m}" for i, m in enumerate(msgs))
    embed = discord.Embed(
        title=f"📋 Preset Vouch Messages ({len(msgs)}/{MAX_MESSAGES})",
        description=formatted,
        color=0x5865F2
    )
    await ctx.send(embed=embed)


@bot.command(name="clearmsgs")
@commands.check(is_admin)
async def clear_messages(ctx):
    settings["messages"] = []
    save_settings(settings)
    await ctx.send("🗑️ All preset messages cleared.")

# ─────────────────────────────────────────────────────────
# AUTO VOUCH TRIGGER
# ─────────────────────────────────────────────────────────

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return

    sender_role_id   = settings.get("sender_role_id")
    vouch_channel_id = settings.get("vouch_channel_id")
    target_role_id   = settings.get("target_role_id")
    msgs             = settings.get("messages", [])

    if not all([sender_role_id, vouch_channel_id, target_role_id, msgs]):
        await bot.process_commands(message)
        return

    sender_role = message.guild.get_role(sender_role_id)
    if sender_role not in message.author.roles:
        await bot.process_commands(message)
        return

    if message.channel.id == vouch_channel_id:
        await bot.process_commands(message)
        return

    vouch_channel = bot.get_channel(vouch_channel_id)
    target_role   = message.guild.get_role(target_role_id)

    if not vouch_channel or not target_role:
        await bot.process_commands(message)
        return

    chosen_msg = random.choice(msgs)

    embed = discord.Embed(
        description=f"**{chosen_msg}**",
        color=0x57F287,
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url
    )
    embed.add_field(name="Vouched by", value=message.author.mention, inline=True)
    embed.add_field(name="Role",       value=target_role.mention,     inline=True)
    embed.set_footer(text="✅ Vouch")

    await vouch_channel.send(embed=embed)
    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online | Prefix: {PREFIX} | Max messages: {MAX_MESSAGES}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You need **Administrator** permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument. Use `$help` to see correct usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument. Make sure you're mentioning a valid role or channel.")


keep_alive()
bot.run(TOKEN)
