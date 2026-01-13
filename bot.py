# bot_instance.py
import discord
from discord.ext import commands

# ✅ Create the bot instance globally
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
bot.remove_command("help")

# ✅ Store join_times and voice_activity_tracker inside bot BEFORE registering events
bot.join_times = {}
bot.streaming_sessions = {}
bot.voice_activity_tracker = {}
bot.processed_in_leaderboard = set()
bot.invites_cache = {}

# ✅ Function to get the bot instance anywhere
def get_bot():
    return bot