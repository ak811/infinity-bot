import shlex
from discord.ext import commands
from cogs.economy.coin.service import update_coins
from configs.config_logging import coins_logger

class SudoSendCoinsCog(commands.Cog):
    """sudo_send_coins — Batch add/deduct coins.
       Format: <user_id> [<user_id> ...] <coins> [reason]"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_send_coins")
    @commands.has_permissions(administrator=True)
    async def sudo_send_coins(self, ctx, *, input_data: str):
        try:
            tokens = shlex.split(input_data)
        except Exception:
            await ctx.send("🙅 Error parsing input. Please check your formatting.")
            return

        if len(tokens) < 2:
            await ctx.send("🙅 Please provide at least one user ID and the amount.")
            return

        user_ids, coin_amount, coin_index = [], None, None
        for i, tok in enumerate(tokens):
            try:
                v = int(tok)
            except ValueError:
                await ctx.send("🙅 Invalid input. All user IDs and the amount should be integers.")
                return
            if v <= 50000:
                coin_amount, coin_index = v, i
                break
            else:
                user_ids.append(v)

        if coin_amount is None:
            await ctx.send("🙅 Amount not provided or invalid.")
            return
        if not user_ids:
            await ctx.send("🙅 Please provide at least one user ID before the amount.")
            return

        reason = " ".join(tokens[coin_index+1:]) if coin_index + 1 < len(tokens) else ""

        exempt_user_id = 377928910718894091
        if coin_amount > 50000 and ctx.author.id != exempt_user_id:
            await ctx.send("🙅 You are not allowed to send more than 20000 🪙.")
            return

        failed = []
        for uid in user_ids:
            ok = update_coins(uid, coin_amount, "sudo")
            if ok is False:
                failed.append(uid)

        if failed:
            await ctx.send("🙅 The following users failed:\n" + ", ".join(f"<@{u}>" for u in failed))
            return

        op = "added" if coin_amount > 0 else "deducted"
        reason_txt = f" for {reason}" if reason else ""
        response = "\n".join(f"<@{u}> ✅ Successfully {op} {abs(coin_amount)} 🪙{reason_txt}." for u in user_ids)
        await ctx.send(response)
        coins_logger.info(response)

async def setup(bot: commands.Bot):
    await bot.add_cog(SudoSendCoinsCog(bot))
