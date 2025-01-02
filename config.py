from dataclasses import dataclass, field

@dataclass
class Color:
    invisible_color: int = 0x2B2D31

@dataclass
class Emoji:
    thrive_wallet: str = "<:thrive_wallet:1324357593430491226>"

@dataclass
class Discord:
    token: str

@dataclass
class Client:
    prefix: str = ";"
    owners: list = field(default_factory=list)
    support: str = "https://discord.gg/UqmgHnHeGT"

@dataclass
class Database:
    uri: str = "mongodb://localhost:27017"
    database: str = "thrive"

@dataclass
class Config:
    discord: Discord
    client: Client
    database: Database

config: Config = Config(
    discord=Discord(
        token="MTMxMTg5MjExNjMzMDM4NTU0MA.GxbPpO.LNjTUQ5Hyr3fNLTlGSNglkwjC6khXDK_HV_1F0",
    ),
    client=Client(owners=[261855568073850890]),
    database=Database(),
)
