from __future__ import annotations
from typing import Callable
from pathlib import Path
import random
import json
from bson import Int64

from discord import User, Embed
from discord.ext import commands
from discord.ext.commands import Cog, hybrid_command

from main import Thrive
from tools.client.context import Context
from config import Color
from logging import getLogger

log = getLogger("Thrive/bot")

def ensure_user_in_db() -> Callable:
    async def predicate(ctx: Context) -> bool:
        user = await ctx.bot.db.users.find_one({"_id": ctx.author.id}, {"_id": 1})
        if not user:
            await ctx.bot.db.users.insert_one(
                {
                    "_id": ctx.author.id,
                    "username": ctx.author.name,
                    "wallet": Int64(0),
                    "xp": Int64(0),
                    "level": 1,
                    "commands_ran": {},
                }
            )
            try:
                await ctx.author.send("Hi")
            except Exception:
                pass
        return True

    return commands.check(predicate)

def calculate_level(xp: int) -> int:
    """Calculate the user's level based on XP."""
    return max(1, int((xp / 100) ** 0.5))

class Economy(Cog):
    def __init__(self, bot: Thrive):
        self.bot = bot
        self.beg_messages = self._load_messages("beg_messages.json")
        self.explore_messages = self._load_messages("explore_messages.json")

    def _load_messages(self, filename: str) -> dict:
        """Loads and returns the specified JSON data."""
        json_path = Path(f"tools/assets/{filename}")
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def update_user_stats(self, user_id: int, command_name: str) -> None:
        """Update the user's stats for XP, levels, and command tracking."""
        xp_gain = 2
        user_data = await self.bot.db.users.find_one(
            {"_id": user_id}, {"xp": 1, "level": 1, "commands_ran": 1}
        )

        if user_data is None:
            return

        new_xp = user_data.get("xp", 0) + xp_gain
        new_level = calculate_level(new_xp)

        if new_level > user_data.get("level", 1):
            new_xp = 0

        commands_ran = user_data.get("commands_ran", {})
        commands_ran[command_name] = commands_ran.get(command_name, 0) + 1

        update_fields = {
            "$set": {"xp": new_xp, "level": new_level, "commands_ran": commands_ran}
        }

        await self.bot.db.users.update_one({"_id": user_id}, update_fields)

    @hybrid_command(name="beg")
    @ensure_user_in_db()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def beg(self, ctx: Context) -> None:
        """Beg for a quick lump of cash"""
        target = ctx.author
        outcome_type = random.choice(
            ["success_messages", "fail_messages", "loss_messages"]
        )
        selected_message = random.choice(self.beg_messages[outcome_type])
        payout = random.randint(1, 100)

        update = {
            "$inc": {
                "wallet": payout if outcome_type == "success_messages" else -payout
            }
        }
        await self.bot.db.users.update_one({"_id": target.id}, update)

        final_message = selected_message.replace("${money}", f"**${payout}**")
        embed = Embed(description=f"{final_message}", color=Color.invisible_color)
        await ctx.send(embed=embed)

        await self.update_user_stats(target.id, "beg")

    @hybrid_command(name="explore")
    @ensure_user_in_db()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def explore(self, ctx: Context) -> None:
        """Explore the surroundings for random rewards."""
        target = ctx.author
        outcome_type = random.choice(
            ["success_messages", "fail_messages", "loss_messages"]
        )
        selected_message = random.choice(self.explore_messages[outcome_type])
        payout = random.randint(50, 250) if outcome_type == "success_messages" else random.randint(1, 100)
    
        update = {
            "$inc": {
                "wallet": payout if outcome_type == "success_messages" else -payout
            }
        }
        await self.bot.db.users.update_one({"_id": target.id}, update)
    
        final_message = selected_message.replace("${money}", f"**${payout}**")
        embed = Embed(description=f"{final_message}", color=Color.invisible_color)
        await ctx.send(embed=embed)
    
        await self.update_user_stats(target.id, "explore")

    @hybrid_command(name="balance", aliases=["bal"])
    @ensure_user_in_db()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def balance(self, ctx: Context, member: User = None) -> None:
        """Check your own or another user's balance."""
        target = member or ctx.author
        user_data = await self.bot.db.users.find_one(
            {"_id": target.id}, {"wallet": 1, "level": 1}
        )

        wallet_amount = user_data.get("wallet", 0)

        embed = Embed(
            color=Color.invisible_color,
            title=f"{target}'s balance",
            url="https://www.youtube.com/watch?v=yvHYWD29ZNY"
        )
        embed.add_field(name="Wallet", value=f"${wallet_amount:,}")
        await ctx.send(embed=embed)

        if member is None:
            await self.update_user_stats(target.id, "balance")
