# pycord/bot.py
import os
import inspect
import discord
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

# scheduled events + voice state tracking (guarded for lib/version differences)
if hasattr(intents, "scheduled_events"):
    intents.scheduled_events = True
if hasattr(intents, "voice_states"):
    intents.voice_states = True


class PycordBot(commands.Bot):
    async def setup_hook(self):
        # register event handlers (decorators)
        try:
            from pycord.events import register_events  # noqa: F401
            print("✅ Registered event handlers (pycord.events)")
        except Exception as e:
            print(f"🙅 Failed to register event handlers: {e}")

        # load extensions (sync or async depending on your discord lib)
        try:
            maybe = self.load_extension("pycord.queue")
            if inspect.isawaitable(maybe):
                await maybe
            print("✅ Loaded extension: pycord.queue")
        except Exception as e:
            print(f"🙅 Failed to load pycord.queue extension: {e}")


bot_pycord = PycordBot(command_prefix="!", intents=intents)
bot_pycord.remove_command("help")


def get_bot() -> commands.Bot:
    return bot_pycord


def main():
    load_dotenv()
    token = os.getenv("PYCORD_BOT_TOKEN")
    if not token:
        print("🙅 PYCORD_BOT_TOKEN is missing. Please add it to your .env file.")
        return

    print("🚀 Starting Pycord bot...")
    bot_pycord.run(token)


if __name__ == "__main__":
    main()
