# Infinity Bot

A modular Discord bot that powers community operations (roles, channels, emojis), engagement loops (XP, streaks, quizzes), economy (multi-currency + shop), games, voice utilities, and admin tooling.

---

## What this bot does

### Community + Server Utilities
- Custom `!help` and an FAQ panel for members.  
- Server commands directory + “quick guide” style embeds (roles, channels, perks, etc.).  

### Engagement & Retention
- **Daily streaks** triggered by activity (messages, reactions, and joining/switching voice channels).  
- **Birthdays**, automatic reactions, and DM utilities.  
- **AI personas** that reply when mentioned or replied-to, posting as webhooks for “character” vibes.

### Economy + Progression
- XP and role ladders, profiles, leaderboards.  
- Currency flow (coins → orbs → stars → diamonds) and a shop system (collectibles, custom roles, subscriptions, exchanges, etc.).  
- Utility commands like `!coins`, `!send_coins`, `!diamonds`, plus a BTC price announcer.

### Games & Social Features
- Clans, spin wheel, dice, fortune, topics, betting, nickname helper, word snake, “tree” mini-game, and more.

### Voice
- Voice state tracking utilities.
- **Voice message transcription** (implementation includes a no-op STT fallback so you can swap in a real provider).

### Admin + Moderation Helpers
- Backup category/channels, purge ranges, permission audits, channel rename tools, embed editing, message send/edit, reaction add/remove, host PC status, etc.

---

## Tech stack

- **discord.py** bot (prefix commands + app commands)  
- Python 3.x
- OpenAI integration for:
  - Persona replies (chat completions)
  - Quiz question generation (async client)
- Optional document parsing for quizzes (PDF/DOCX/PPTX/XLSX)

---

## Repository layout

At the root you have:
- `bot.py` – creates the global bot instance (`command_prefix="!"`) and shared runtime state.  
- `main.py` – bootstraps the bot, syncs slash commands to the configured guild, loads extensions (cogs), and starts the bot.  
- `cogs/` – feature modules grouped by domain (server, admin, stats, fun, economy, engagement, networking, voice, onboarding).  

---

## Quickstart (local dev)

### 1) Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure secrets and server IDs
This bot reads `BOT_TOKEN` and `BOT_GUILD_ID` from `configs.config_general` (which typically loads from environment variables).  
You’ll also want `OPENAI_API_KEY` if you enable personas / AI quiz generation.

Create a `.env` (or set env vars in your host) with at least:
```bash
BOT_TOKEN="your_discord_bot_token"
BOT_GUILD_ID="your_server_id"
OPENAI_API_KEY="your_openai_key"  # needed for Persona + Quiz Maker
```

> The repo also includes a `pycord/.env` in the tree; use whichever approach your deployment prefers.

### 3) Run the bot
```bash
python main.py
```

On startup, the bot will:
- sync slash commands **to your configured guild** (fast availability)
- load all configured cogs
- connect to Discord and begin processing events

---

## Configuration notes

### Guild restriction
Commands are blocked outside the configured guild. If you want multi-server support, remove or rework the `restrict_to_english_cafe` check in `main.py`.

### Slash command scope
Several app commands are **guild-scoped** using `@app_commands.guilds(discord.Object(id=BOT_GUILD_ID))`.  
That’s intentional: instant availability during development and avoids global command propagation delays.

### Permissions
Some features require elevated bot permissions, depending on what you enable:
- Manage Roles (role assignment / reward ladders / custom roles)
- Manage Channels (rename, archive/mover tools)
- Manage Emojis & Stickers (emoji tooling)
- Message Content intent (for many prefix-command + listener features)
- Manage Webhooks (for persona/webhook replies)
- Read Message History (stats, backups, some games)

---

## License
MIT. See `LICENSE`.