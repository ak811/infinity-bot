from __future__ import annotations
import discord
from configs.config_roles import LOOT_AND_LEGENDS_PERKS
from configs.config_channels import ANNOUNCEMENTS_CHANNEL_ID
from configs.config_general import COIN_EMOJI, ORB_EMOJI, STAR_EMOJI
from configs.config_logging import logging
from configs.helper import send_as_webhook

async def announce_role_upgrade(member: discord.Member, new_role: discord.Role, rewards: tuple[int, int, int]) -> None:
    perks = LOOT_AND_LEGENDS_PERKS.get(new_role.id, [])
    perk_text = "\n".join(f"- {p}" for p in perks) if perks else "*(No perks listed… yet!)*"

    dollars, orbs, stars = rewards
    rewards_txt = [f"- {COIN_EMOJI} **{dollars}**", f"- {ORB_EMOJI} **{orbs}**"] + ([f"- {STAR_EMOJI} **{stars}**"] if stars else [])

    embed = discord.Embed(
        title=f"🎉 {member.display_name} is now a {new_role.name}! 🎉",
        description=f"🔥 **Unlocked Perks:**\n{perk_text}\n\n🎁 **Level-Up Rewards:**\n" + "\n".join(rewards_txt),
        color=new_role.color
    ).set_footer(text="Keep climbing those XP ranks!")

    content = f"## 🎇 CONGRATULATIONS 🎇\n## 🚀 {member.mention} has leveled up to {new_role.name}! 🚀\n🎯 *Check out your new perks and rewards below!*"
    ch = member.guild.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    if not ch: return
    try:
        msg = await send_as_webhook(ch, "level_up", content=content, embed=embed)
        for emoji in ("🎉", "✨", "🚀"):
            try: await msg.add_reaction(emoji)
            except discord.HTTPException: pass
    except Exception as e:
        logging.info(f"Failed to announce in rewards channel: {e}")
