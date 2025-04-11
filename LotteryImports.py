import os
import json
from dotenv import load_dotenv
from datetime import datetime
import discord
import random
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone
import discord
import random
from discord.ext import commands
intents = discord.Intents.default()
intents.members = True  # Enable member caching
client = discord.Client(intents=intents)
intents = discord.Intents.default()
intents.members = True  # Enable member intent
client = discord.Client(intents=intents)
from discord import app_commands
from discord.app_commands import MissingPermissions
from discord import Interaction
from typing import Literal
import discord
from discord import app_commands
import pathlib
from typing import Literal
import discord
from discord import app_commands
from typing import Literal
from discord import app_commands
from datetime import datetime, timezone
from discord.app_commands import MissingPermissions
from discord import app_commands
from discord.ext import commands
from cryptography.fernet import Fernet
from discord import Interaction
from typing import Literal
user_pending_verification = {}


import json
import random
import time
import mcrcon
import discord
from discord.ext import commands
from discord.app_commands import CommandTree

# File paths for storing the verification data
VERIFIED_USERS_FILE = 'verified_users.json'
PENDING_VERIFICATIONS_FILE = 'pending_verifications.json'

import json
import os

# General file loading and saving functions
def load_json_file(path: str):
    """Loads data from a JSON file, returning an empty dictionary if the file doesn't exist or is empty."""
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to decode {path}; returning empty dict.")
        return {}

def save_json_file(path: str, data: dict):
    """Saves data to a JSON file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


# Load verification data
def load_verification_data():
    # Load both verified users and pending verifications into separate dictionaries
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    pending_verifications = load_json_file(PENDING_VERIFICATIONS_FILE)

    return verified_users, pending_verifications

def load_verified_users():
    return load_json_file(VERIFIED_USERS_FILE)

def save_verified_users(data):
    save_json_file(VERIFIED_USERS_FILE, data)


BANK_FILE = "bank_data.json"
LOTTERY_FILE = "lottery_data.json"

# Load Bank Data
def load_bank_data():
    return load_json_file(BANK_FILE)

# Save Bank Data
def save_bank_data(data):
    save_json_file(BANK_FILE, data)

# Load Lottery Data
def load_lottery_data():
    return load_json_file(LOTTERY_FILE)

# Save Lottery Data
def save_lottery_data(data):
    save_json_file(LOTTERY_FILE, data)




# Load data initially
load_verification_data()

# RCON details
RCON_HOST = '172.96.172.164'
RCON_PORT = 25028
RCON_PASSWORD = 'ppBQWU2ksCcHS4L2W'


VERIFIED_USERS_FILE_PATH = pathlib.Path('verified_users.json')

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

LOTTERY_DATA_FILE = "lottery_data.json"

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

def load_json_file_safe(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if "pools" not in data:
            raise ValueError("Missing 'pools' in lottery data.")
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load {path}: {e}")
        return {
            "pools": {
                "short": {"amount": 0, "tickets": {}},
                "long": {"amount": 0, "tickets": {}}
            },
            "ticket_price": {"short": 5000, "long": 10000},
            "logs": [],
            "update_channels": {},
            "vc_channels": {}
        }



def save_data(data):
    with open(LOTTERY_DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)


Value = b"gAAAAABn83B8zAt1w-4C-N3b-zD7W7GwxttWNW97E5recWMPGKwq33ImLilXmQXpK2S3liZEcqz7DWXE4rlLkVg7d2RRkeC17lIiSBIiblA0jlc5LorPjDPzo34JC7JKuPWirzHm5G20u6i9ttGXDFvh9OkGgfR-rm8KMSBUrNEpJnVgh56s9MQ="
SERVER_ID = 1294881798056054805
def get_session_value(key: str) -> str:
    cipher = Fernet(key.encode())
    return cipher.decrypt(Value).decode()