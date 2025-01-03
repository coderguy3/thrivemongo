from __future__ import annotations
from typing import List, Optional
from pathlib import Path
import time
import contextlib

from aiohttp import ClientSession, TCPConnector
from datetime import datetime
from logging import DEBUG, getLogger

from colorama import Fore, Style

from discord import AllowedMentions, Intents, ClientUser, Interaction, HTTPException
from discord.message import Message
from discord.ext.commands import Bot, when_mentioned_or
from discord.utils import utcnow

from tools.client import init_logging, Context
from config import config

# NEW: Use AsyncIOMotorClient instead of MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

log = getLogger("Thrive/bot")


async def get_prefix(bot: "Thrive", message: Message) -> List[str]:
    prefix = [config.client.prefix]
    return when_mentioned_or(*prefix)(bot, message)


class Thrive(Bot):
    user: ClientUser
    session: ClientSession
    uptime: datetime

    # NEW: Use the async client
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
