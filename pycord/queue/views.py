# pycord/queue/views.py

import discord
from configs.config_logging import logging
from configs.helper import send_as_webhook
from .state import queue_state

class QueueView(discord.ui.View):
    def __init__(self, vc_id: int):
        super().__init__(timeout=None)
        self.add_item(JoinButton(vc_id))
        self.add_item(LeaveButton(vc_id))

# ---------- Core update helpers (moved here to avoid circular import) ----------

async def update_queue_embed(guild: discord.Guild, vc_id: int):
    """Edit (or recreate) the queue message for a given VC."""
    state = queue_state.get(vc_id)
    if not state:
        return

    channel = guild.get_channel(state["channel_id"])
    if channel is None:
        logging.warning(f"[Queue] Channel {state['channel_id']} not found for vc {vc_id}")
        return

    members = "\n".join(f"<@{uid}>" for uid in state["user_ids"]) or "_(empty)_"
    new_embed = discord.Embed(
        title="🎮 Current Queue",
        description=members,
        color=discord.Color.green()
    )
    view = QueueView(vc_id)

    hook = state.get("hook")
    try:
        if hook:
            await hook.edit_message(state["message_id"], embed=new_embed, view=view)
        else:
            msg = await channel.fetch_message(state["message_id"])
            await msg.edit(embed=new_embed, view=view)
    except Exception:
        logging.exception("[Queue] Failed to edit existing queue message; sending a fresh one.")
        msg = await send_as_webhook(channel, "queue", embed=new_embed, view=view)
        state["message_id"] = msg.id
        if hasattr(msg, "webhook"):
            state["hook"] = msg.webhook  # cache webhook if available

async def send_queue_status(ctx, vc_id: int):
    """Resend the current queue embed without altering state."""
    state = queue_state.get(vc_id)
    if not state:
        return
    try:
        channel = ctx.bot.get_channel(state["channel_id"])
        if not channel:
            return
        # Reconstruct embed from state instead of fetching old message (safer)
        members = "\n".join(f"<@{uid}>" for uid in state["user_ids"]) or "_(empty)_"
        embed = discord.Embed(
            title="🎮 Current Queue",
            description=members,
            color=discord.Color.green()
        )
        await send_as_webhook(ctx, "queue", embed=embed, view=QueueView(vc_id))
    except Exception:
        logging.warning("[Queue] Failed to resend existing queue embed.")

# ---------- Buttons ----------

class JoinButton(discord.ui.Button):
    def __init__(self, vc_id: int):
        super().__init__(
            label="Join",
            style=discord.ButtonStyle.success,
            custom_id=f"queue:join:{vc_id}"
        )
        self.vc_id = vc_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = queue_state.get(self.vc_id)
        if not state:
            return
        user_id = interaction.user.id
        if user_id in state["user_ids"]:
            return await interaction.followup.send(
                "🙅 You’re already in the queue!",
                ephemeral=True
            )
        state["user_ids"].append(user_id)
        await update_queue_embed(interaction.guild, self.vc_id)

        channel = interaction.guild.get_channel(state["channel_id"])
        if channel:
            await send_as_webhook(
                channel,
                "queue",
                embed=discord.Embed(
                    description=f"✅ **{interaction.user.display_name}** joined the queue.",
                    color=discord.Color.green()
                )
            )

class LeaveButton(discord.ui.Button):
    def __init__(self, vc_id: int):
        super().__init__(
            label="Leave",
            style=discord.ButtonStyle.danger,
            custom_id=f"queue:leave:{vc_id}"
        )
        self.vc_id = vc_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        state = queue_state.get(self.vc_id)
        if not state:
            return
        user_id = interaction.user.id
        if user_id not in state["user_ids"]:
            return await interaction.followup.send(
                "🙅 You’re not in the queue!",
                ephemeral=True
            )
        state["user_ids"].remove(user_id)
        await update_queue_embed(interaction.guild, self.vc_id)

        channel = interaction.guild.get_channel(state["channel_id"])
        if channel:
            await send_as_webhook(
                channel,
                "queue",
                embed=discord.Embed(
                    description=f"🚪 **{interaction.user.display_name}** left the queue.",
                    color=discord.Color.red()
                )
            )
