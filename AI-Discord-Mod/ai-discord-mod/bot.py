import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
from ai_discord_functions import image_is_safe, message_is_safe
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
import json

load_dotenv()

# Create a lock for each file
servers_lock = asyncio.Lock()
warnings_lock = asyncio.Lock()
sensitivity_lock = asyncio.Lock()

# Save servers settings to file
async def save_servers():
    async with servers_lock:
        try:
            with open("servers.json", "w") as file:
                json.dump(servers, file)
        except IOError as e:
            print(f"Error saving servers: {e}")

# Save warnings to file
async def save_warnings():
    async with warnings_lock:
        try:
            with open("warnings.json", "w") as file:
                json.dump(warning_list, file)
        except IOError as e:
            print(f"Error saving warnings: {e}")


# Load servers settings from file
try:
    with open("servers.json", "r") as file:
        servers = json.load(file)
except FileNotFoundError:
    servers = {}

try:
    with open("warnings.json", "r") as file:
        warning_list = json.load(file)
except FileNotFoundError:
    warning_list = {}

async def save_sensitivity():
    async with sensitivity_lock:
        try:
            with open("sensitivity.json", "w") as file:
                json.dump(sensitivity, file)
        except IOError as e:
            print(f"Error saving sensitivity: {e}")

# Load sensitivity settings from file
try:
    with open("sensitivity.json", "r") as file:
        sensitivity = json.load(file)
except FileNotFoundError:
    sensitivity = {}


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.tree.command(name="help", description="Shows commands and information for the Sven AI bot.")
async def aihelp(interaction: discord.Interaction):
    await interaction.response.send_message(
        """
**Help:**
```
help: Shows this information.
set_warnings <warnings>: Sets the number of warnings a user can have before muting them.
set_mute_time <time>: Sets the amount of time a user is muted for after having too many warnings. Example: 1d, 3m, 5s, 6h
use_warnings <boolean>: Whether to use warnings and mute the user, or just only delete the message.
set_sensitivity <float from 0-1>: The image moderation sensitivity. As sensitivity increases, image moderation becomes more strict, and as sensitivity decreases, image moderation becomes less strict.
set_logs_channel <channel id>: The logs channel id that Sven will log logs to. Note that Sven must have permission to view and send messages to this channel.
```

Note the default presets:
```
set_warnings: 3
set_mute_time: 10m
use_warnings: False
set_sensitivity: 0.5
set_logs_channel: None (will not log any deletions)
```

Also note that the Sven role should be **ABOVE** all other members, in order to create and enforce the muted role.
""", ephemeral = True)

@bot.tree.command(name="set_logs_channel", description="Set a server wide channel id for logging messages.")
@app_commands.describe(logs_channel_id = "Logs Channel ID")
async def set_logs_channel(interaction: discord.Interaction, logs_channel_id: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    try:
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['logs_channel_id'] = logs_channel_id
        await save_servers()
        await interaction.response.send_message(f"**Successfully set logs channel id to: {logs_channel_id}**", ephemeral=True)
    except:
        await interaction.response.send_message("**Failed to parse logs channel id. Logs Channel ID must be an integer.**", ephemeral=True)

    
@bot.tree.command(name="use_warnings", description="Whether to automatically mute users after a certain amount of warnings.")
@app_commands.describe(use_warnings = "Use Warnings")
async def use_warnings(interaction: discord.Interaction, use_warnings: bool):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
    servers[str(interaction.guild.id)]['use_warnings'] = use_warnings
    await save_servers()
    await interaction.response.send_message(f"Successfully set use_warnings to **{use_warnings}**.", ephemeral=True)

@bot.tree.command(name="set_sensitivity", description="Set a server wide image moderation sensitivity.")
@app_commands.describe(sensitivity = "Image Moderation Sensitivity")
async def set_sensitivity(interaction: discord.Interaction, sensitivity: float):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    if sensitivity > 1:
        await interaction.response.send_message("**Failed to parse sensitivity. Sensitivity must be a number from 0-1.**", ephemeral=True)
        return
    try:
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['sensitivity'] = sensitivity
        await save_servers()
        await interaction.response.send_message(f"**Successfully set image moderation sensitivity to: {sensitivity}**", ephemeral=True)
    except:
        await interaction.response.send_message("**Failed to parse sensitivity. Sensitivity must be a number from 0-1.**", ephemeral=True)


@bot.tree.command(name="set_warnings", description="Set a server wide warnings limit before muting a member.")
@app_commands.describe(warning_count = "Warning Count")
async def set_warnings(interaction: discord.Interaction, warning_count: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    try:
        warnings = warning_count
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['warnings'] = warnings
        await save_servers()
        await interaction.response.send_message(f"**Successfully set warnings to: {warnings}**", ephemeral=True)
    except:
        await interaction.response.send_message("**Failed to parse warnings. Warnings must be an integer.**", ephemeral=True)

@bot.tree.command(name="set_mute_time", description="Set a server wide mute time to mute a member for.")
@app_commands.describe(mute_time = "Mute Time")
async def set_mute_time(interaction: discord.Interaction, mute_time: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(f"You do not have permission to use this command.", ephemeral=True)
        return
    try:
        servers[str(interaction.guild.id)] = servers.get(str(interaction.guild.id), {})
        servers[str(interaction.guild.id)]['mute_time'] = mute_time
        await save_servers()
        await interaction.response.send_message(f"**Successfully set mute time to {mute_time}**", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message("**Invalid duration input**", ephemeral=True)


BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_TRIGGERING_WORDS = os.getenv("USE_TRIGGERING_WORDS")

if USE_TRIGGERING_WORDS == "True":
    TRIGGERING_WORDS_FILE = os.getenv("TRIGGERING_WORDS")
    if TRIGGERING_WORDS_FILE:
        with open(TRIGGERING_WORDS_FILE, "r") as file:
            TRIGGERING_WORDS = file.read().split(",")
    else:
        TRIGGERING_WORDS = []
else:
    TRIGGERING_WORDS = []

if not BOT_TOKEN or not OPENAI_API_KEY:
    print("You did not set your .env file correctly.")
    exit()


async def tempmute(ctx, member: discord.Member=None):
    guild = ctx.guild
    warnings = servers[str(guild.id)].get('warnings', 3)
    time = servers[str(guild.id)].get('mute_time', '10m')
    reason = f"sending more than {warnings} inappropriate messages."
    bot_member = guild.get_member(bot.user.id)
    try:
        seconds = int(time[:-1])
        duration = time[-1]
        if duration == "s":
            seconds = seconds * 1
        elif duration == "m":
            seconds = seconds * 60
        elif duration == "h":
            seconds = seconds * 60 * 60
        elif duration == "d":
            seconds = seconds * 86400
        else:
            await ctx.send("Invalid duration input")
            return
    except Exception as e:
        print(e)
        await ctx.send("Invalid duration input")
        return

    Muted = discord.utils.get(guild.roles, name="Muted")
    if not Muted:
        Muted = await guild.create_role(name="Muted")
        all_roles = await guild.fetch_roles()
        for i in range(len(all_roles)):
            if all_roles[i] in [y for y in bot_member.roles]:
                role_of_muted = len(all_roles)-i-1
        try:
            await Muted.edit(reason=None, position=role_of_muted)
        except:
            await ctx.send("**Failed to mute user, ensure that the bot role is above all other roles.**")
            return
        for channel in guild.channels:
            await channel.set_permissions(Muted, speak=False, send_messages=False, read_message_history=True, read_messages=True)

    await member.add_roles(Muted, reason=reason)
    muted_embed = discord.Embed(title="Muted User", description=f"{member.mention} was muted for {reason} Muted for {time}.")
    await ctx.send(embed=muted_embed)
    await asyncio.sleep(seconds)
    await member.remove_roles(Muted)
    unmute_embed = discord.Embed(title="Mute Over!", description=f'{member.mention} is now unmuted.')
    await ctx.send(embed=unmute_embed)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    await bot.wait_until_ready()
    if message.author.id == bot.user.id:
        return
    sent_message = message
    guild = message.guild
    if str(guild.id) not in servers:  # If server is not in servers, add it
        servers[str(guild.id)] = {'use_warnings': False, 'warnings': 3, 'mute_time': '10m'}
        await save_servers()

    use_warnings = servers[str(guild.id)].get('use_warnings', False)
    warnings = servers[str(guild.id)].get('warnings', 3)

    if str(guild.id) not in warning_list:
        warning_list[str(guild.id)] = {}
        await save_warnings()
    

    if USE_TRIGGERING_WORDS == "True":
            if not any(map(message.content.__contains__, TRIGGERING_WORDS)):
                return
            else:
                print("Triggering word found in the filter, sending to OpenAI...")

    if message.attachments:
        attachments = message.attachments
        for attachment in attachments:
            if attachment.content_type.startswith("image"):
                await attachment.save("toModerate.jpeg")
                sensitivity = servers[str(guild.id)].get('sensitivity', 0.5)
                result = await image_is_safe(sensitivity=sensitivity)

                if not result:
                    await sent_message.delete()
                    print("Deleted a message with an inappropriate image. The message was sent from " + str(sent_message.author.id))

                    logs_channel_id = servers[str(guild.id)].get('logs_channel_id', None)
                    if logs_channel_id:
                        logs_channel = bot.get_channel(int(logs_channel_id))
                        await logs_channel.send(f"Deleted an image from {sent_message.author.mention} because it was inappropriate.")

                    if not use_warnings:
                        await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate.")
                        return
                    if message.author.id in warning_list[str(guild.id)]:
                        warning_list[str(guild.id)][message.author.id] += 1
                        await save_warnings()
                        if warning_list[str(guild.id)][message.author.id] >= warnings:
                            await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate.")
                            await tempmute(sent_message.channel, sent_message.author)
                            warning_list[str(guild.id)][message.author.id] = 0
                            await save_warnings()
                        else:
                            await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) -  warning_list[str(guild.id)][message.author.id]) + " warnings left.")
                    else:
                        warning_list[str(guild.id)][message.author.id] = 1
                        await save_warnings()
                        await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s image because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) -  warning_list[str(guild.id)][message.author.id]) + " warnings left.")
                    return
    
    if not message.attachments and not await(message_is_safe(message.content, OPENAI_API_KEY)):
        await sent_message.delete()
        print("Deleted an inappropriate message. The message was sent from " + str(sent_message.author.id))

        logs_channel_id = servers[str(guild.id)].get('logs_channel_id', None)
        if logs_channel_id:
            logs_channel = bot.get_channel(int(logs_channel_id))
            await logs_channel.send(f"Deleted a message from {sent_message.author.mention} because it was inappropriate. The message was: '{sent_message.content}'")

        if not use_warnings:
            await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate.")
            return
        if message.author.id in warning_list[str(guild.id)]:
            warning_list[str(guild.id)][message.author.id] += 1
            await save_warnings()
            if warning_list[str(guild.id)][message.author.id] >= warnings:
                await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate.")
                await tempmute(sent_message.channel, sent_message.author)
                warning_list[str(guild.id)][message.author.id] = 0
                await save_warnings()
            else:
                await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) -  warning_list[str(guild.id)][message.author.id]) + " warnings left.")
        else:
            warning_list[str(guild.id)][message.author.id] = 1
            await save_warnings()
            await sent_message.channel.send("Deleted " + sent_message.author.mention + "'s message because it was inappropriate. " + sent_message.author.mention + " has " + str(int(warnings) - warning_list[str(guild.id)][message.author.id]) + " warnings left.")
    
    await bot.process_commands(message)

    @bot.event
    async def on_message_edit(message_before, message_after):
        await on_message(message_after)
    
bot.run(BOT_TOKEN)
