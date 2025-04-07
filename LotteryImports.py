import os
import json
from dotenv import load_dotenv
from datetime import datetime
import discord
import random
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from discord.app_commands import MissingPermissions
from discord import app_commands
from discord.ext import commands
from discord import Interaction
from typing import Literal

def save_lottery_data(data):
    """Saves the lottery data to the JSON file."""
    with open("lottery_data.json", "w") as f:
        json.dump(data, f, indent=4)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "lottery_data.json"

def load_data():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        # Create a fresh data file if missing or empty
        data = {
            "pools": {
                "short": 0,
                "long": 0
            },
            "tickets": {},
            "logs": [],
            "update_channel_id": None
        }
        save_data(data)
        return data
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Corrupted JSON — reset it
        print("⚠️ lottery_data.json is corrupted. Resetting it.")
        data = {
            "pools": {
                "short": 0,
                "long": 0
            },
            "tickets": {},
            "logs": [],
            "update_channel_id": None
        }
        save_data(data)
        return data


# Save data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Create embed message for donations
def create_donation_embed(user, amount, pool):
    embed = discord.Embed(
        title="🎉 New Lottery Donation!",
        description=f"**{user.display_name}** contributed **{amount}** coins to the **{pool.capitalize()} Lottery**!",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="Lottery System")
    return embed


async def update_pool_channel(pool: str, amount: int, data: dict):
    if "update_channels" not in data or pool not in data["update_channels"]:
        return
    ...



import json
import os

# Path to the lottery data JSON file
LOTTERY_DATA_PATH = "lottery_data.json"


def load_data():
    # 1. Load or initialize
    if not os.path.exists(LOTTERY_DATA_PATH) or os.stat(LOTTERY_DATA_PATH).st_size == 0:
        data = {
            "pools": {"short": 0, "long": 0},
            "logs": [],
            "update_channel_id": None,
            "ticket_price": {"short": 10, "long": 20}
        }
    else:
        try:
            with open(LOTTERY_DATA_PATH, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ lottery_data.json corrupted; resetting.")
            data = {
                "pools": {"short": 0, "long": 0},
                "logs": [],
                "update_channel_id": None,
                "ticket_price": {"short": 10, "long": 20}
            }

    # 2. Migrate pool entries from int → dict
    pools = data.setdefault("pools", {})
    for p in ["short", "long"]:
        val = pools.get(p, 0)
        if isinstance(val, int):
            # convert old format
            pools[p] = {"amount": val, "tickets": {}}
        elif isinstance(val, dict):
            # ensure keys exist
            pools[p].setdefault("amount", 0)
            pools[p].setdefault("tickets", {})
        else:
            # fallback
            pools[p] = {"amount": 0, "tickets": {}}

    # 3. Ensure other top‑level keys
    data.setdefault("logs", [])
    data.setdefault("update_channel_id", None)
    data.setdefault("ticket_price", {"short": 10, "long": 20})

    return data

def save_data(data):
    with open(LOTTERY_DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)


DISCORD_TOKEN='MTM1ODI1ODM5MDc5MDQzOTAwNA.G3idif.2C5Qq-rDNtg5F7098ksx6MRZWs67Wu4i82kNN0'
SERVER_ID='12948817980560548051'