# main.py
import discord
import asyncio
import logging
from datetime import datetime
from configs.config_general import BOT_TOKEN, BOT_GUILD_ID
from bot import get_bot

# ✅ Get the global bot instance
bot = get_bot()

# --- One-time slash command sync via setup_hook (recommended) ---
bot._did_tree_sync = False  # for visibility/debugging

async def _setup_hook():
    """
    Runs once before the bot connects to Discord's gateway.
    Safe place to sync app commands without being overridden by on_ready handlers.
    """
    if bot._did_tree_sync:
        return
    try:
        # Per-guild sync → appears immediately for that guild
        await bot.tree.sync(guild=discord.Object(BOT_GUILD_ID))
        print(f"✅ Slash commands synced for guild {BOT_GUILD_ID}")
        bot._did_tree_sync = True
    except Exception as e:
        print(f"❌ Failed to sync app commands: {e}")

# Bind setup_hook onto the bot instance
bot.setup_hook = _setup_hook

@bot.check
async def restrict_to_english_cafe(ctx):
    if ctx.guild and ctx.guild.id != BOT_GUILD_ID:
        await ctx.send("This bot is exclusive to **Infinity Café Server** 🎉\nJoin us to use the commands: 🔗 https://discord.gg/BqvjRT6W")
        return False
    return True

# Save the bot's startup time for retroactive tracking of VC activity.
bot.start_time = datetime.utcnow()

# Ensure these dictionaries exist on the bot instance.
if not hasattr(bot, "join_times"):
    bot.join_times = {}
if not hasattr(bot, "voice_activity_tracker"):
    bot.voice_activity_tracker = {}

async def shutdown_handler():
    """Ensure voice activity is logged before the bot shuts down."""
    print("🔻 Bot is shutting down. Saving voice activity...")

    guild = bot.get_guild(BOT_GUILD_ID)
    if not guild:
        print("⚠️ Unable to retrieve guild. Skipping voice activity update.")
        return

    # Make sure our tracking dicts exist and use str(user_id) keys
    if not hasattr(bot, "join_times"):
        bot.join_times = {}
    if not hasattr(bot, "voice_activity_tracker"):
        bot.voice_activity_tracker = {}

    # Build a dict of active non-bot users from all voice channels.
    active_voice_members: dict[str, datetime] = {}
    for channel in guild.voice_channels:
        # Skip AFK channel entirely
        if guild.afk_channel and channel.id == guild.afk_channel.id:
            continue

        non_bot_members = [m for m in channel.members if not m.bot]
        if non_bot_members:
            print(f"📢 Found {len(non_bot_members)} non-bot member(s) in voice channel: {channel.name}")

        for member in non_bot_members:
            uid = str(member.id)
            # If a member isn't already tracked, assume they've been in VC since bot startup.
            if uid not in bot.join_times:
                bot.join_times[uid] = bot.start_time  # retroactive to startup time
                print(f"🕒 Retroactively setting join time for {member.display_name} to {bot.start_time.isoformat()}")

            # Use the stored join time once per user.
            active_voice_members[uid] = bot.join_times[uid]

    if not active_voice_members:
        print("⚠️ No active users in VC. Nothing to update.")
    else:
        active_names = [
            (guild.get_member(int(uid)).display_name if guild.get_member(int(uid)) else uid)
            for uid in active_voice_members
        ]
        print(f"🔍 Active users at shutdown: {active_names}")

    now = datetime.utcnow()

    # Process each tracked active user only once.
    for user_id_str, join_time in active_voice_members.items():
        duration = int((now - join_time).total_seconds())
        if duration <= 0:
            continue

        # Optional: bucket for diagnostics/metrics
        bot.voice_activity_tracker[user_id_str] = bot.voice_activity_tracker.get(user_id_str, 0) + duration

        print(f"⏱️ Processing user {user_id_str}: joined at {join_time.isoformat()}, duration = {duration} seconds.")

        # Use the same XP pipeline as voice_state updates (category 'vc')
        # try:
        #     amount = update_vc_xp(user_id_str, duration, "vc")
        #     print(f"✅ User {user_id_str} earned {amount} XP for {duration} seconds of VC activity.")
        # except Exception as e:
        #     print(f"❌ Failed to update XP for user {user_id_str}: {e}")

        # Remove processed user to prevent duplicate processing
        if user_id_str in bot.join_times:
            del bot.join_times[user_id_str]

    # Cancel any pending post-join tasks to avoid logs firing late
    if hasattr(bot, "voice_join_tasks"):
        for t in list(bot.voice_join_tasks.values()):
            if t and not t.done():
                t.cancel()
        bot.voice_join_tasks.clear()

async def main():
    """Main bot execution with proper shutdown handling."""
    try:

        # Server
        await bot.load_extension("cogs.server.help")
        await bot.load_extension("cogs.server.faq")
        await bot.load_extension("cogs.server.commands")
        await bot.load_extension("cogs.server.avatar")
        await bot.load_extension("cogs.server.channels")
        await bot.load_extension("cogs.server.roles")
        await bot.load_extension("cogs.server.emojis")

        # Admin
        await bot.load_extension("cogs.admin.roles.add_role_everyone")
        await bot.load_extension("cogs.admin.roles.remove_role_everyone")
        await bot.load_extension("cogs.admin.roles.add_member_role_everyone_except_vips")

        await bot.load_extension("cogs.admin.backup.messages")
        await bot.load_extension("cogs.admin.backup.category")
        await bot.load_extension("cogs.admin.delete.category_channels")
        await bot.load_extension("cogs.admin.delete.purge")
        await bot.load_extension("cogs.admin.count.messages")
        await bot.load_extension("cogs.admin.count.mentions")
        await bot.load_extension("cogs.admin.embed.remove_buttons")
        await bot.load_extension("cogs.admin.embed.edit")
        await bot.load_extension("cogs.admin.events.create")
        await bot.load_extension("cogs.admin.channels.rename")
        await bot.load_extension("cogs.admin.channels.check_dangerous_perms")
        await bot.load_extension("cogs.admin.channels.list_perms")
        await bot.load_extension("cogs.admin.message.send")
        await bot.load_extension("cogs.admin.message.edit")
        await bot.load_extension("cogs.admin.reaction.add")
        await bot.load_extension("cogs.admin.reaction.remove")
        await bot.load_extension("cogs.admin.misc.pc_status")
        await bot.load_extension("cogs.admin.misc.send_coins")
        
        # Stats
        await bot.load_extension("cogs.stats.main")
        await bot.load_extension("cogs.stats.leaderboard")
        await bot.load_extension("cogs.stats.logging.delete")
        await bot.load_extension("cogs.stats.logging.reactions")
        await bot.load_extension("cogs.stats.logging.roles")
        await bot.load_extension("cogs.stats.message_stats.ping_count")
        await bot.load_extension("cogs.stats.message_stats.message_count")
        await bot.load_extension("cogs.stats.message_stats.word_count")
        await bot.load_extension("cogs.stats.close_circle")

        # Games
        await bot.load_extension("cogs.fun.spin_wheel.cog_spin")
        await bot.load_extension("cogs.fun.clans")
        await bot.load_extension("cogs.fun.nickname")
        await bot.load_extension("cogs.fun.tree")
        await bot.load_extension("cogs.fun.word_snake")
        await bot.load_extension("cogs.fun.compliment")
        await bot.load_extension("cogs.fun.dice")
        await bot.load_extension("cogs.fun.fortune")
        await bot.load_extension("cogs.fun.topic")
        await bot.load_extension("cogs.fun.bet")

        # Economy
        await bot.load_extension("cogs.economy.shop")
        await bot.load_extension("cogs.economy.xp")
        await bot.load_extension("cogs.economy.coin")
        await bot.load_extension("cogs.economy.orb")
        await bot.load_extension("cogs.economy.star")
        await bot.load_extension("cogs.economy.diamond")
        await bot.load_extension("cogs.economy.dollar")
        await bot.load_extension("cogs.economy.confirmation")
        await bot.load_extension("cogs.economy.bank")
        await bot.load_extension("cogs.economy.profile")
        await bot.load_extension("cogs.economy.bitcoin")

        # Networking
        await bot.load_extension("cogs.networking.ping")
        await bot.load_extension("cogs.networking.pings")
        await bot.load_extension("cogs.networking.online")

        # Engagement
        await bot.load_extension("cogs.engagement.reactions")
        await bot.load_extension("cogs.engagement.birthdays")
        await bot.load_extension("cogs.engagement.daily_streaks")
        await bot.load_extension("cogs.engagement.automatic_reactions")
        await bot.load_extension("cogs.engagement.persona")
        await bot.load_extension("cogs.engagement.dm")
        await bot.load_extension("cogs.engagement.quiz_maker")

        # Voice
        await bot.load_extension("cogs.voice.transcription")
        await bot.load_extension("cogs.voice.voice_chat")
        await bot.load_extension("cogs.voice.vc_name_update")
        await bot.load_extension("cogs.voice.voice_state_updates")

        # Onboarding
        await bot.load_extension("cogs.onboarding.new_member_roles")
        await bot.load_extension("cogs.onboarding.invites_handler")
        # await bot.load_extension("cogs.onboarding.welcome")

        # Misc
        await bot.load_extension("cogs.misc.disboard")
        await bot.load_extension("cogs.misc.embeds")

        # Run the bot
        await bot.start(BOT_TOKEN)

    except asyncio.CancelledError:
        print("⚠️ Bot task cancelled, cleaning up...")
    finally:
        print("⚠️ Closing bot...")
        await shutdown_handler()
        await bot.close()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("⚠️ KeyboardInterrupt detected.")
    finally:
        # Cancel any pending tasks.
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        # Shutdown logging to flush and close all logging handlers.
        logging.shutdown()
        print("✅ Cleanup complete. Exiting gracefully.")
        loop.close()
