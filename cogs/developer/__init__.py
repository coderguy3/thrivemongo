from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Thrive


async def setup(bot: "Thrive") -> None:
    from .developer import Developer

    await bot.add_cog(Developer(bot))
