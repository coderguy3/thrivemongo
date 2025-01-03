from __future__ import annotations
from typing import Callable
from pathlib import Path
import random
import json

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
        self.beg_messages = self._load_beg_messages()

    def _load_beg_messages(self) -> dict:
        """Loads and returns the beg_messages.json data."""
        json_path = Path("tools/assets/beg_messages.json")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    @hybrid_command(name="beg")
    @ensure_user_in_db()
    async def beg(self, ctx: Context, member: User = None) -> None:
        """Beg for a quick lump of cash"""
        target = member or ctx.author
        user_data = await self.bot.db.users.find_one({"_id": target.id})
        outcome_type = random.choice(["success_messages", "fail_messages", "loss_messages"])
        selected_message = random.choice(self.beg_messages[outcome_type])
        payout = random.randint(1, 100)

        if outcome_type == "success_messages":
            await self.bot.db.users.update_one(
                {"_id": target.id},
                {"$inc": {"wallet": payout}}
            )
            final_message = selected_message.replace("${money}", f"**${payout}**")
            embed=Embed(description=f"{final_message}")
            await ctx.send(embed=embed)

        elif outcome_type == "fail_messages":
            embed=Embed(color=Color.invisible_color, description=f"{selected_message}")
            await ctx.send(embed=embed)

        else:
            await self.bot.db.users.update_one(
                {"_id": target.id},
                {"$inc": {"wallet": -payout}}
            )
            final_message = selected_message.replace("${money}", f"**${payout}**")
            embed=Embed(description=f"{final_message}")
            await ctx.send(embed=embed)



    @hybrid_command(name="balance", aliases=["bal"])
    @ensure_user_in_db()
    async def balance(self, ctx: Context, member: User = None) -> None:
        """Check your own or another user's balance"""
        target = member or ctx.author
        user_data = await self.bot.db.users.find_one({"_id": target.id})

        wallet_amount = user_data.get("wallet", 0)

        if not user_data:
            embed=Embed(color=Color.invisible_color, title=f"{ctx.author}'s balance", url="https://www.youtube.com/watch?v=yvHYWD29ZNY")
            embed.add_field(name="Wallet", value=f"{wallet_amount:,}")
            return await ctx.send(embed=embed)

        embed=Embed(color=Color.invisible_color, title=f"{ctx.author}'s balance", url="https://www.youtube.com/watch?v=yvHYWD29ZNY")
        embed.add_field(name="Wallet", value=f"{wallet_amount:,}")
        await ctx.send(embed=embed)
