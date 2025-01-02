from __future__ import annotations
from typing import Callable

from discord import Message, User, Embed
from discord.ext import commands
from discord.ext.commands import Cog, group, command, hybrid_command, hybrid_group

from main import Thrive
from tools.client.context import Context
from config import Color

from logging import DEBUG, getLogger

log = getLogger("Thrive/bot")


def ensure_user_in_db() -> Callable:
    async def predicate(ctx: Context) -> bool:
        user = await ctx.bot.db.users.find_one({"_id": ctx.author.id})
        if user is None:
            await ctx.bot.db.users.insert_one(
                {
                    "_id": ctx.author.id,
                    "username": ctx.author.name,
                    "wallet": 0,
                }
            )
            try:
                await ctx.author.send("Hi")
            except:
                pass
        return True

    return commands.check(predicate)


class Economy(Cog):
    def __init__(self, bot: Thrive):
        self.bot = bot

    @hybrid_command(name="balance", aliases=["bal"])
    @ensure_user_in_db()
    async def balance(self, ctx: Context, member: User = None) -> None:
        """Check your own or another user's balance."""
        target = member or ctx.author
        user_data = await self.bot.db.users.find_one({"_id": target.id})

        if not user_data:
            embed=Embed(color=Color.invisible_color)
            embed.add_field(name="Wallet")
            return await ctx.send(embed=embed)

        wallet_amount = user_data.get("wallet", 0)
        embed=Embed(
            color=Color.invisible_color,
            desciption=f""
        )
        return await ctx.send(embed=embed)
