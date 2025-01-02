from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Thrive


async def setup(bot: "Thrive") -> None:
    from .economy import Economy

    await bot.add_cog(Economy(bot))
