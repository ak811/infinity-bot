# cogs/embeds/quick_guide.py
from __future__ import annotations
import discord
from configs.config_channels import (
    CHITTY_CHAT_CHANNEL_ID,
    SERIOUS_CHAT_CHANNEL_ID,
    COMMANDS_CHANNEL_ID,
    CHANNELS_CHANNEL_ID,
)

# Target message
QUICK_GUIDE_CHANNEL_ID = 1194473065514545202
QUICK_GUIDE_MESSAGE_ID = 1328588980123336768

def _quick_guide_text() -> str:
    return (
        "Welcome, traveler 👋 Grab your seat — here’s how to thrive in the Café:\n\n"
        "## 🏆 Level Up\n"
        "* Chat, VC, add or receive reactions → earn **XP**.\n"
        "* Milestones: **Skilled → Proficient → Specialist → Expert → Elite → "
        "Mastermind → Grandmaster → Champion → Legend** ⚡\n"
        "* Every level = shiny rewards.\n\n"
        "## 💎 Currency Flow\n"
        "**Coins → Orbs → Stars → Diamonds**\n"
        "Earn by chatting, VC time, events & streaks.\n"
        "Spend diamonds in the 🏪 Shop for perks, subs & flex.\n\n"
        "## ⚔️ Clans\n"
        "* `!clan join <name>` to rep your squad.\n"
        "* Your activity powers your clan.\n"
        "* Weekly leaderboards = glory + rewards.\n\n"
        "## 🎯 Things To Do\n"
        f"* **Chat:** <#{CHITTY_CHAT_CHANNEL_ID}> / <#{SERIOUS_CHAT_CHANNEL_ID}>\n"
        "* **VCs:** Study, jam, party 🎶\n"
        f"* **Games, Events & Channels:** <#{CHANNELS_CHANNEL_ID}>\n\n"
        "## ⚡ Quick Commands\n"
        "* `!profile` — your stats\n"
        "* `!shop` — spend your coins\n"
        f"_(More in <#{COMMANDS_CHANNEL_ID}> )_\n\n"
        "🚀 That’s it: **Chat → Level → Flex → Clan → Glory.**"
    )

def _split_into_chunks(text: str, limit: int = 4096) -> list[str]:
    if len(text) <= limit:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []

    def flush():
        if current:
            chunks.append("\n\n".join(current))

    for p in paragraphs:
        candidate = ("\n\n".join(current + [p])) if current else p
        if len(candidate) <= limit:
            current.append(p)
        else:
            flush()
            if len(p) <= limit:
                current = [p]
            else:
                # hard wrap
                start = 0
                while start < len(p):
                    end = min(start + limit, len(p))
                    chunks.append(p[start:end])
                    start = end
                current = []
    flush()
    return chunks

def build_quick_guide_embeds() -> list[discord.Embed]:
    full_text = _quick_guide_text()
    chunks = _split_into_chunks(full_text, limit=4096)
    embeds: list[discord.Embed] = []

    for i, chunk in enumerate(chunks):
        title = "🌟 Infinity Café — Quick Guide" if i == 0 else "🌟 Infinity Café — Quick Guide (cont.)"
        embed = discord.Embed(
            title=title,
            description=chunk,
            color=discord.Color.gold(),
        )
        embeds.append(embed)

    return embeds
