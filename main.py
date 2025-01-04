from __future__ import annotations
from typing import List, Optional
from pathlib import Path
import time
import contextlib
import asyncio
import math

from aiohttp import ClientSession, TCPConnector
from datetime import datetime
from logging import DEBUG, getLogger

from colorama import Fore, Style

from discord import (
    AllowedMentions,
    Intents,
    ClientUser,
    Interaction,
    HTTPException,
    Embed,
)
from discord.message import Message
from discord.ext.commands import Bot, when_mentioned_or
from discord.utils import utcnow
from discord.ext import commands
from tools.client import init_logging, Context
from config import config, Color

from motor.motor_asyncio import AsyncIOMotorClient

log = getLogger("Thrive/bot")


async def get_prefix(bot: "Thrive", message: Message) -> List[str]:
    prefix = [config.client.prefix]
    return when_mentioned_or(*prefix)(bot, message)


class Thrive(Bot):
    user: ClientUser
    session: ClientSession
    uptime: datetime

    mongo_client = AsyncIOMotorClient(config.database.uri)

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            intents=Intents(
                guilds=True,
                members=True,
                messages=True,
                reactions=True,
                moderation=True,
                message_content=True,
                emojis_and_stickers=True,
            ),
            allowed_mentions=AllowedMentions(
                everyone=False, roles=False, users=True, replied_user=True
            ),
            command_prefix=get_prefix,
            case_insensitive=True,
            owner_ids=config.client.owners,
        )
        self.db = self.mongo_client[config.database.database]
        self.buckets: dict = dict(
            guild_commands=dict(
                lock=asyncio.Lock(),
                cooldown=commands.CooldownMapping.from_cooldown(
                    12,
                    2.5,
                    commands.BucketType.guild,
                ),
                blocked=set(),
            )
        )

    @property
    def owners(self) -> List[int]:
        return config.client.owners

    async def setup_hook(self) -> None:
        self.session = ClientSession(connector=TCPConnector(ssl=False))

    async def on_ready(self) -> None:
        if hasattr(self, "uptime"):
            return

        log.info(
            f"Connected as {Fore.LIGHTCYAN_EX}{Style.BRIGHT}{self.user}{Fore.RESET} "
            f"({Fore.LIGHTRED_EX}{self.user.id}{Fore.RESET})."
        )
        self.uptime = utcnow()

        await self.load_extensions()

    async def load_extensions(self) -> None:
        await bot.load_extension("jishaku")

        for feature in Path("cogs").iterdir():
            if not feature.is_dir():
                continue

            elif not (feature / "__init__.py").is_file():
                continue

            try:
                await self.load_extension(".".join(feature.parts))
            except Exception as exc:
                log.exception(
                    "Failed to load extension %s.", feature.name, exc_info=exc
                )

    async def on_message(self, message: Message):
        if not self.is_ready() or not message.guild or message.author.bot:
            return

        if message.content == f"<@{self.user.id}>":
            with contextlib.suppress(HTTPException):
                await message.reply(f"Hi my prefix is `;`")

        ctx = await self.get_context(message)

        if not ctx.command:
            return
        await self.process_commands(message)

    async def on_message_edit(self, before: Message, after: Message):
        if not self.is_ready() or not before.guild or before.author.bot:
            return

        if before.content == after.content or not after.content:
            return

        self.dispatch("user_activity", after.channel, after.author)
        await self.process_commands(after)

    def check_message(self, message: Message) -> bool:
        if not self.is_ready() or message.author.bot or not message.guild:
            return False

        return True

    @staticmethod
    async def command_cooldown(ctx: Context):
        if ctx.author.id == ctx.guild.owner_id:
            return True

        blocked = ctx.bot.buckets["guild_commands"]["blocked"]
        if not ctx.bot.get_guild(ctx.guild.id) or ctx.guild.id in blocked:
            return False

        bucket = ctx.bot.buckets["guild_commands"]["cooldown"].get_bucket(ctx.message)
        if retry_after := bucket.update_rate_limit():
            return False

        return True

    async def on_command_error(self, ctx: Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            cooldown_time = int(math.ceil(error.retry_after))

            human_readable = self._format_cooldown_time(cooldown_time)

            embed = Embed(
                color=Color.invisible_color,
                description=f"You are on cooldown for **{human_readable}**",
            )
            return await ctx.send(embed=embed, delete_after=10)

    def _format_cooldown_time(self, total_seconds: int) -> str:
        if total_seconds >= 86400:
            days = total_seconds // 86400
            return f"{days} day{'s' if days > 1 else ''}"

        hours = total_seconds // 3600
        remaining = total_seconds % 3600
        minutes = remaining // 60
        seconds = remaining % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if seconds > 0 and hours == 0 or minutes == 0 or seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return ", ".join(parts)

    async def get_context(
        self, origin: Message | Interaction, /, *, cls=Context
    ) -> Context:
        context = await super().get_context(origin, cls=cls)
        return context

    def run(self) -> None:
        log.info("Starting the bot...")
        super().run(config.discord.token, reconnect=True, log_handler=None)


if __name__ == "__main__":
    bot = Thrive()
    init_logging(DEBUG)
    bot.run()
