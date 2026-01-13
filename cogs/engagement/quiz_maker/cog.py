# cogs/engagement/quiz_maker/cog.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

from configs.config_general import BOT_GUILD_ID, OPENAI_API_KEY

from .file_loader import extract_text_from_file
from .quiz_session import QuizSession
from .stats import QuizStatsStore
from .ui import QuizView, QuizSummaryView, QuizSetupView
from .runtime_start import (
    start_quiz_from_setup as start_quiz_from_setup_logic,
    restart_quiz_from_summary as restart_quiz_from_summary_logic,
)
from .runtime_actions import (
    handle_answer as handle_answer_logic,
    handle_skip_question as handle_skip_question_logic,
    handle_end_quiz as handle_end_quiz_logic,
)
from .runtime_questions import (
    handle_question_timeout as handle_question_timeout_logic,
    send_summary as send_summary_logic,
    send_review_dm as send_review_dm_logic,
)

log = logging.getLogger(__name__)

SessionKey = Tuple[int, int]

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".log",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".htm",
    ".css",
    ".csv",
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xlsm",
    ".xltx",
    ".xltm",
}


class QuizMakerCog(commands.Cog):
    """Interactive quiz generator based on uploaded files, via slash command."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.sessions: Dict[SessionKey, QuizSession] = {}
        self.last_completed_sessions: Dict[Tuple[Optional[int], int], QuizSession] = {}
        self.stats_store = QuizStatsStore()

    @app_commands.command(
        name="quiz_maker",
        description="Generate a multiple choice quiz from an uploaded file.",
    )
    @app_commands.describe(
        file="File to build the quiz from (any readable document or text-like file).",
    )
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def quiz_maker(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
    ) -> None:
        if interaction.user.bot:
            await interaction.response.send_message(
                "🤖 Robots do not need pop quizzes.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        channel = interaction.channel
        if channel is None:
            await interaction.followup.send(
                "❌ No channel found to send questions in."
            )
            return

        key: SessionKey = (channel.id, interaction.user.id)
        if key in self.sessions:
            await interaction.followup.send(
                "⚠️ You already have an active quiz in this channel. "
                "Finish or cancel it before starting another one."
            )
            return

        filename = file.filename or "file"
        suffix = Path(filename).suffix.lower()

        if file.size and file.size > MAX_FILE_BYTES:
            await interaction.followup.send(
                f"❌ That file is too large ({file.size} bytes). "
                "Please use a file under 5 MB."
            )
            return

        if suffix and suffix not in ALLOWED_EXTENSIONS:
            await interaction.followup.send(
                "❌ That file type is not supported for quizzes.\n"
                f"Supported extensions: `{', '.join(sorted(ALLOWED_EXTENSIONS))}`"
            )
            return

        try:
            raw_bytes = await file.read()
            text = extract_text_from_file(filename, raw_bytes)
        except Exception as exc:
            log.error("Error reading attachment: %s", exc, exc_info=True)
            message = str(exc).strip() or "Could not read that file."
            await interaction.followup.send(f"❌ {message}")
            return

        setup_view = QuizSetupView(
            cog=self,
            user_id=interaction.user.id,
            source_text=text,
            filename=filename,
        )
        msg = await interaction.followup.send(
            content=(
                f"🧠 Loaded `{filename}` for a new quiz.\n"
                "Use the menus below to choose difficulty, question count, "
                "and whether the quiz is timed, then press **Start quiz**."
            ),
            view=setup_view,
        )
        setup_view.message = msg

    async def start_quiz_from_setup(
        self,
        interaction: discord.Interaction,
        setup_view: QuizSetupView,
    ) -> None:
        await start_quiz_from_setup_logic(self, interaction, setup_view)

    async def handle_answer(
        self,
        interaction: discord.Interaction,
        session_key: SessionKey,
        choice_index: int,
        question_index: int,
        view: discord.ui.View | None = None,
    ) -> None:
        await handle_answer_logic(
            self,
            interaction,
            session_key,
            choice_index,
            question_index,
            view=view,
        )

    async def handle_skip_question(
        self,
        interaction: discord.Interaction,
        session_key: SessionKey,
        question_index: int,
        view: discord.ui.View | None = None,
    ) -> None:
        await handle_skip_question_logic(
            self,
            interaction,
            session_key,
            question_index,
            view=view,
        )

    async def handle_question_timeout(
        self,
        session_key: SessionKey,
        question_index: int,
        view: QuizView,
    ) -> None:
        await handle_question_timeout_logic(self, session_key, question_index, view)

    async def handle_end_quiz(
        self,
        interaction: discord.Interaction,
        session_key: SessionKey,
        question_index: int,
        view: discord.ui.View | None = None,
    ) -> None:
        await handle_end_quiz_logic(
            self,
            interaction,
            session_key,
            question_index,
            view=view,
        )

    async def restart_quiz_from_summary(
        self,
        interaction: discord.Interaction,
        previous_session: QuizSession,
    ) -> None:
        await restart_quiz_from_summary_logic(self, interaction, previous_session)

    async def _send_review_dm(
        self,
        user: discord.abc.User,
        session: QuizSession,
    ) -> bool:
        return await send_review_dm_logic(self, user, session)

    async def _send_summary(
        self,
        channel: discord.abc.Messageable,
        session: QuizSession,
    ) -> None:
        await send_summary_logic(self, channel, session)

    @app_commands.command(
        name="quiz_stats",
        description="Show your quiz performance stats.",
    )
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def quiz_stats(self, interaction: discord.Interaction) -> None:
        if interaction.user.bot:
            await interaction.response.send_message(
                "🤖 Robots do not get bragging rights.", ephemeral=True
            )
            return

        guild_id = interaction.guild_id
        stats = self.stats_store.get_user_stats(guild_id, interaction.user.id)
        if stats is None:
            await interaction.response.send_message(
                "📊 You have not completed any quizzes yet.",
                ephemeral=True,
            )
            return

        from .embeds import build_quiz_stats_embed

        embed = build_quiz_stats_embed(interaction.user, stats)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="quiz_leaderboard",
        description="Show the quiz leaderboard for this server.",
    )
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def quiz_leaderboard(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Leaderboard is only available inside a server.",
                ephemeral=True,
            )
            return

        board = self.stats_store.get_leaderboard(guild.id)
        if not board:
            await interaction.response.send_message(
                "📉 No quiz results for this server yet.",
                ephemeral=True,
            )
            return

        from .embeds import build_leaderboard_embed

        embed = build_leaderboard_embed(guild, board)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="quiz_review",
        description="DMs you a review of your most recent quiz.",
    )
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def quiz_review(self, interaction: discord.Interaction) -> None:
        if interaction.user.bot:
            await interaction.response.send_message(
                "🤖 Robots do not need review sessions.",
                ephemeral=True,
            )
            return

        key = (interaction.guild_id, interaction.user.id)
        session = self.last_completed_sessions.get(key)
        if session is None:
            await interaction.response.send_message(
                "🗒️ I do not have a recent quiz to review for you.",
                ephemeral=True,
            )
            return

        success = await self._send_review_dm(interaction.user, session)
        if not success:
            await interaction.response.send_message(
                "❌ I could not send you a DM. Check your privacy settings.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "📬 I sent you a DM with your quiz review.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(QuizMakerCog(bot))
