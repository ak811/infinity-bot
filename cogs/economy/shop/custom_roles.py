from __future__ import annotations

import inspect
import discord
from discord.ext import commands
from discord import app_commands

from .helpers import generate_shop_embed
from utils.utils_json import load_json, save_json

from cogs.economy.orb.service import update_orbs, get_total_orbs
from cogs.server.roles.rank import get_highest_loot_legends_role_index  # rank lookup

from configs.config_files import CUSTOM_ROLES_FILE
from configs.config_channels import LOGS_CHANNEL_ID
from configs.config_general import BOT_GUILD_ID

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_BYTES = 256 * 1024

# ──────────────────────────────────────────────────────────────────────────────
# Eligibility gate: Lieutenant (index 3) and above only
# ──────────────────────────────────────────────────────────────────────────────
MIN_RANK_INDEX = 3  # Lieutenant+

def _has_lieutenant_plus(member: discord.Member) -> bool:
    """
    Returns True if the member's highest Loot & Legends rank index is >= 3 (Lieutenant+).
    Falls back to False if rank lookup fails.
    """
    try:
        return get_highest_loot_legends_role_index(member) >= MIN_RANK_INDEX
    except Exception:
        return False

# ──────────────────────────────────────────────────────────────────────────────
# Storage & helpers
# ──────────────────────────────────────────────────────────────────────────────
async def get_or_create_custom_role(member: discord.Member):
    """
    Get or create the member's custom role entry.
    NOTE: Callers must check _has_lieutenant_plus(member) BEFORE calling this.
    """
    custom_roles = load_json(CUSTOM_ROLES_FILE)
    user_id = str(member.id)
    guild = member.guild
    role = None
    if user_id in custom_roles:
        role_id = custom_roles[user_id].get("role_id")
        role = guild.get_role(role_id)
    if role is None:
        try:
            # create a zero-width named role
            role = await guild.create_role(name="\u200c\u200c", colour=discord.Colour.default())
            custom_roles[user_id] = {"role_id": role.id}
            save_json(CUSTOM_ROLES_FILE, custom_roles)
            await member.add_roles(role)

            # Try to position just under "trial_helper_role" if it exists
            trial_helper_role = discord.utils.get(guild.roles, id=1201212028874920017)
            if trial_helper_role:
                await role.edit(position=trial_helper_role.position - 1)
        except Exception as e:
            print(f"Error creating custom role for {member.id}: {e}")
    return role


def role_edit_accepts(*param_names: str) -> str | None:
    """
    Detects the proper kwarg for role icon based on discord.py version:
    typically 'display_icon' or 'icon'. Returns the first supported name or None.
    """
    try:
        params = inspect.signature(discord.Role.edit).parameters
        for name in param_names:
            if name in params:
                return name
    except Exception:
        pass
    return None


async def clear_custom_role(member: discord.Member) -> bool:
    """
    Clear (remove & delete) the user's custom role regardless of eligibility.
    Useful to let users clean up even if they later fall below the gate.
    """
    custom_roles = load_json(CUSTOM_ROLES_FILE)
    user_id = str(member.id)
    guild = member.guild
    if user_id in custom_roles:
        role_id = custom_roles[user_id].get("role_id")
        role = guild.get_role(role_id)
        if role:
            try:
                await member.remove_roles(role)
                await role.delete(reason="Custom role cleared by user")
            except Exception as e:
                print(f"Failed to clear custom role for {member.id}: {e}")
                return False
        custom_roles.pop(user_id, None)
        save_json(CUSTOM_ROLES_FILE, custom_roles)
        return True
    return False

# ──────────────────────────────────────────────────────────────────────────────
# Modals
# ──────────────────────────────────────────────────────────────────────────────
class CustomRoleNameModal(discord.ui.Modal, title="Customize Role Name"):
    role_name = discord.ui.TextInput(
        label="Enter new role name",
        placeholder="My Custom Role",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Eligibility gate
        if not _has_lieutenant_plus(interaction.user):
            return await interaction.response.send_message(
                "❌ Custom roles are available to **Lieutenant** and above.", ephemeral=True
            )

        user_id = str(interaction.user.id)
        cost = 0
        if get_total_orbs(user_id) < cost:
            return await interaction.response.send_message(
                "❌ Not enough 🔮 orbs to customize your role name.", ephemeral=True
            )

        role = await get_or_create_custom_role(interaction.user)
        try:
            await role.edit(name=self.role_name.value)
            await interaction.user.add_roles(role, reason="Custom role update")
            # Nudge role close to top (but below max)
            await interaction.guild.edit_role_positions({role: max(r.position for r in interaction.guild.roles) - 1})
            await interaction.response.send_message(
                f"✅ Your role name has been updated to **{self.role_name.value}**!", ephemeral=True
            )
            update_orbs(user_id, -cost)
            channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
            if channel:
                embed = discord.Embed(title=f"🎉 Role Name Updated <@{user_id}>", color=discord.Color.red())
                embed.add_field(name="User", value=interaction.user.mention, inline=True)
                await channel.send(embed=embed)
        except Exception:
            await interaction.response.send_message("❌ Failed to update role name.", ephemeral=True)


class CustomRoleColorModal(discord.ui.Modal, title="Customize Role Color"):
    role_color = discord.ui.TextInput(
        label="Enter new role color (hex, e.g., #FF0000)",
        placeholder="#FFFFFF",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Eligibility gate
        if not _has_lieutenant_plus(interaction.user):
            return await interaction.response.send_message(
                "❌ Custom roles are available to **Lieutenant** and above.", ephemeral=True
            )

        user_id = str(interaction.user.id)
        cost = 0
        if get_total_orbs(user_id) < cost:
            return await interaction.response.send_message(
                "❌ Not enough 🔮 orbs to customize your role color.", ephemeral=True
            )

        # parse color
        try:
            color_value = int(self.role_color.value.strip("#"), 16)
            color = discord.Colour(color_value)
        except Exception:
            return await interaction.response.send_message(
                "❌ Invalid color format. Use a hex code like #FF0000.", ephemeral=True
            )

        role = await get_or_create_custom_role(interaction.user)
        try:
            await role.edit(colour=color)
            await interaction.user.add_roles(role, reason="Custom role update")
            await interaction.guild.edit_role_positions({role: max(r.position for r in interaction.guild.roles) - 1})
            await interaction.response.send_message("✅ Your role color has been updated!", ephemeral=True)
            update_orbs(user_id, -cost)
            channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
            if channel:
                embed = discord.Embed(title="🎉 Role Color Updated", color=discord.Color.green())
                embed.add_field(name="User", value=interaction.user.mention, inline=True)
                await channel.send(embed=embed)
        except Exception:
            await interaction.response.send_message("❌ Failed to update role color.", ephemeral=True)

# ──────────────────────────────────────────────────────────────────────────────
# View / Shop
# ──────────────────────────────────────────────────────────────────────────────
class CustomRolesShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🏷️ Set or Change Role Name", style=discord.ButtonStyle.primary, custom_id="role_name", row=0)
    async def open_role_name_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Eligibility gate
        if not _has_lieutenant_plus(interaction.user):
            return await interaction.response.send_message(
                "❌ Custom roles are available to **Lieutenant** and above.", ephemeral=True
            )
        await interaction.response.send_modal(CustomRoleNameModal())

    @discord.ui.button(label="🎨 Set or Change Role Color", style=discord.ButtonStyle.primary, custom_id="role_color", row=0)
    async def open_role_color_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Eligibility gate
        if not _has_lieutenant_plus(interaction.user):
            return await interaction.response.send_message(
                "❌ Custom roles are available to **Lieutenant** and above.", ephemeral=True
            )
        await interaction.response.send_modal(CustomRoleColorModal())

    @discord.ui.button(label="🖼️ Set or Change Role Icon", style=discord.ButtonStyle.success, custom_id="role_icon_info", row=1)
    async def show_role_icon_instructions(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = (
            "🖼️ **Role Icon**\n\n"
            "Use `/set_role_icon` command to upload PNG/JPG/WEBP/GIF (≤256KB).\n\n"
            "Note: Custom roles are available to **Lieutenant** and above."
        )
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="❌ Clear Custom Role", style=discord.ButtonStyle.danger, custom_id="clear_custom_role", row=1)
    async def clear_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = await clear_custom_role(interaction.user)
        if success:
            await interaction.response.send_message("✅ Your custom role has been cleared.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You don’t have a custom role to clear.", ephemeral=True)

# ──────────────────────────────────────────────────────────────────────────────
# Cog: slash command for role icon
# ──────────────────────────────────────────────────────────────────────────────
class RoleIcon(commands.Cog):
    """Provides /set_role_icon (image only)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set_role_icon", description="Upload an image to set your custom role icon")
    @app_commands.describe(image="PNG/JPG/WEBP/GIF under 256KB")
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def set_role_icon(self, interaction: discord.Interaction, image: discord.Attachment):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Eligibility gate
        if not _has_lieutenant_plus(interaction.user):
            return await interaction.followup.send(
                "❌ Custom roles are available to **Lieutenant** and above.", ephemeral=True
            )

        guild = interaction.guild
        if guild is None:
            return await interaction.followup.send("❌ Guild context missing.", ephemeral=True)

        me = guild.me
        if not me or not me.guild_permissions.manage_roles:
            return await interaction.followup.send("❌ I need **Manage Roles** permission.", ephemeral=True)

        if "ROLE_ICONS" not in guild.features:
            return await interaction.followup.send("❌ This server doesn’t support role icons.", ephemeral=True)

        # Get or create the user's custom role (eligible by gate above)
        role = await get_or_create_custom_role(interaction.user)
        if role is None:
            return await interaction.followup.send("❌ Couldn’t find your custom role.", ephemeral=True)

        ct = image.content_type or ""
        if (ct not in ALLOWED_MIME) and (not image.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))):
            return await interaction.followup.send("❌ Please upload PNG/JPG/WEBP/GIF.", ephemeral=True)
        if image.size > MAX_BYTES:
            return await interaction.followup.send(f"❌ File too large. Max size is {MAX_BYTES // 1024}KB.", ephemeral=True)

        icon_kw = role_edit_accepts("display_icon", "icon")
        if icon_kw is None:
            lib_ver = getattr(discord, "__version__", "unknown")
            params = ", ".join(inspect.signature(discord.Role.edit).parameters.keys())
            return await interaction.followup.send(
                "❌ This bot’s library doesn’t expose a role icon parameter on `Role.edit()`.\n"
                f"discord.py version: **{lib_ver}**\n"
                f"Current `Role.edit` params: `{params}`\n"
                "Admins: update to discord.py ≥2.x with role icon support.",
                ephemeral=True,
            )

        data = await image.read()
        try:
            kwargs = {icon_kw: data, "reason": f"User {interaction.user} uploaded role icon"}
            await role.edit(**kwargs)
        except discord.Forbidden:
            return await interaction.followup.send("❌ I can’t edit that role (hierarchy).", ephemeral=True)
        except (TypeError, discord.HTTPException) as e:
            return await interaction.followup.send(f"❌ Failed to set icon: `{e}`", ephemeral=True)

        await interaction.followup.send("✅ Role icon updated!", ephemeral=True)

        channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title=f"🖼️ Role Icon Set! <@{interaction.user.id}>", color=discord.Color.blurple())
            embed.add_field(name="User", value=interaction.user.mention, inline=True)
            await channel.send(embed=embed)

# ──────────────────────────────────────────────────────────────────────────────
# Shop builder
# ──────────────────────────────────────────────────────────────────────────────
def build_custom_roles_shop():
    description = (
        "✨ **Customize Your Personal Role!** ✨\n\n"
        "• 🏷️ **Custom Role Name**\n"
        "• 🎨 **Custom Role Color**\n"
        "• 🖼️ **Role Icon**\n\n"
        "🔓 **Requires rank: Lieutenant or higher.**\n"
    )
    embed = generate_shop_embed(
        title="🎨 Custom Roles Shop",
        description=description,
        footer="Stand out with your own custom role! 🌟",
        color=discord.Color.teal(),
    )
    view = CustomRolesShopView()
    return embed, view

# ──────────────────────────────────────────────────────────────────────────────
# Cog setup
# ──────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(RoleIcon(bot))
