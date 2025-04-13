import asyncio
from aiohttp.hdrs import SERVER
import discord
import re
import mcrcon
VERIFIED_USERS_FILE_PATH = ('verified_users.json')

def load_verified_users():
    """Load verified users from a JSON file."""
    if VERIFIED_USERS_FILE_PATH.exists():
        with open(VERIFIED_USERS_FILE_PATH, 'r') as f:
            return json.load(f)
    return {}




# Set up intents
intents = discord.Intents.default()
intents.members = True  # Enable member intent

GUILD_ID = 1107774033107361904  # Your actual guild ID
USER_ID = 0000000000   # The test user's ID
amount = 25

# Load verification data
def load_verification_data():
    # Load both verified users and pending verifications into separate dictionaries
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    pending_verifications = load_json_file(PENDING_VERIFICATIONS_FILE)

    return verified_users, pending_verifications

from LotteryImports import *
from LotteryImports import load_json_file, save_json_file, SERVER_ID, get_session_value
import os, discord
from discord.ext import tasks

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def generate_invoice_id():
    random_number = random.randint(100000000000000000, 999999999999999999)
    invoice_id = f"invoice-#1-"
    return invoice_id

@tasks.loop(hours=24)
async def send_monthly_invoice():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    current_day = now.day
    month_name = now.strftime("%B")

    # Helper to get ordinal suffix
    def get_day_suffix(day):
        if 11 <= day <= 13:
            return "th"
        match day % 10:
            case 1: return "st"
            case 2: return "nd"
            case 3: return "rd"
            case _: return "th"

    day_suffix = get_day_suffix(current_day)

    # Check if today is the 7th
    if current_day != 8:
        print(f"[Invoice Task] Skipping - today is {month_name} {current_day}{day_suffix}, not the 7th.")
        return

    # Predefined PayPal invoice link
    invoice_link = "https://www.paypal.com/invoice/p/#42MYDDLBJCREQAM2"
    invoice_id = generate_invoice_id()
    amount = 25

    try:
        user = await client.fetch_user(USER_ID)
        print(f"[Invoice Task] Found user: {user.display_name}")

        message = (
            f"Hi {user.display_name}! This is a quick reminder that your hosting invoice is now due.\n"
            f"> Invoice ID: `invoice-#1-9306782`\n"
            f"> Issued: Sunday, April 7, 2025\n"
            f"> Due By: Monday, April 8, 2025\n"
            f"- **You may find your Invoice link in the previous message.**"
        )

        await user.send(message)
        print("[Invoice Task] Invoice link sent successfully.")
    except discord.errors.NotFound:
        print(f"[Invoice Task] Could not find user with ID {USER_ID}")

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged into Lottery Client as {client.user}")

    # Start the task loop
    print("[Startup] Invoice task started. Will only send on the 8th of each month.")

    # Try to fetch the user and confirm
    await send_monthly_invoice()
    try:
        user = await client.fetch_user(USER_ID)
    except discord.errors.NotFound:
        print(f"[Startup] Could not find user with ID {USER_ID}")



def execute_rcon_command(command):
    try:
        print(f"[DEBUG] Attempting to execute RCON command: {command}")
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
            response = mcr.command(command)  # Get response
            print(f"[DEBUG] Executed command: {command}, Response: {response}")
            return response  # <-- THIS IS CRUCIAL
    except Exception as e:
        print(f"[DEBUG] Failed to execute RCON command: {e}")
        return None  # Explicitly return None on failure

@tree.command(name="bankdeposit", description="Deposit your in-game marks into your bank account.")
@discord.app_commands.describe(amount="Amount of marks you want to deposit.")
async def bankdeposit(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=False)

    user_id = str(interaction.user.id)
    bank_data = load_json_file(BANK_FILE)
    verified_users = load_json_file(VERIFIED_USERS_FILE)

    if user_id not in verified_users:
        await interaction.followup.send("❌ You must verify your account using `/link` before using the bank.", ephemeral=False)
        return

    ign = verified_users[user_id]

    # Get current in-game marks
    response = execute_rcon_command(f"playerinfo {ign}")
    if not response or "Marks:" not in response:
        await interaction.followup.send("❌ Failed to retrieve your marks. Make sure you're online in-game.", ephemeral=False)
        return

    try:
        match = re.search(r"Marks:\s*(\d+)", response)
        if not match:
            raise ValueError("Marks not found")
        current_marks = int(match.group(1))
    except (IndexError, ValueError):
        await interaction.followup.send("❌ Could not parse your current marks from the server response.",
                                        ephemeral=False)
        return

    new_marks = current_marks - amount
    execute_rcon_command(f"setmarks {ign} {new_marks}")

    # Update bank balance
    bank_data.setdefault(user_id, 0)
    bank_data[user_id] += amount
    save_data(BANK_FILE, bank_data)

    await interaction.followup.send(f"✅ Successfully deposited **{amount:,}** marks into your bank account.\n💰 Remaining in-game marks: **{new_marks:,}**", ephemeral=False)


@tree.command(name="bankwithdraw", description="Withdraw marks from your bank into the game.")
@discord.app_commands.describe(amount="Amount of marks you want to withdraw.")
async def bankwithdraw(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=False)

    user_id = str(interaction.user.id)
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    bank_data = load_json_file(BANK_FILE)
    if user_id not in verified_users:
        await interaction.followup.send("❌ You must verify your account using `/link` before using the bank.", ephemeral=False)
        return

    ign = verified_users[user_id]

    if user_id not in bank_data or bank_data[user_id] < amount:
        await interaction.followup.send("❌ You don’t have enough funds in your bank account.", ephemeral=False)
        return

    response = execute_rcon_command(f"playerinfo {ign}")
    if not response or "Marks:" not in response:
        await interaction.followup.send("❌ Failed to get player info. Make sure you're online in-game.", ephemeral=False)
        return

    try:
        match = re.search(r"Marks:\s*(\d+)", response)
        if not match:
            raise ValueError("Marks not found")
        current_marks = int(match.group(1))
    except (IndexError, ValueError):
        await interaction.followup.send("❌ Failed to get player info. Make sure you're online in-game.",
                                        ephemeral=False)
        return

    new_total = current_marks + amount
    bank_data = load_json_file(BANK_FILE)
    execute_rcon_command(f"setmarks {ign} {new_total}")
    bank_data[user_id] -= amount
    save_data(BANK_FILE, bank_data)

    await interaction.followup.send(f"✅ Withdrawn **{amount:,}** marks to your in-game account.", ephemeral=False)


@tree.command(name="bankbalance", description="Check your bank marks balance.")
async def bankbalance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    bank_data = load_json_file(BANK_FILE)
    verified_users = load_json_file(VERIFIED_USERS_FILE)

    if user_id not in verified_users:
        await interaction.response.send_message("❌ You must verify your account using `/link` before using the bank.",
                                                ephemeral=False)
        return

    balance = bank_data.get(user_id, 0)

    # Generate a random color
    random_color = discord.Color(random.randint(0, 0xFFFFFF))

    # Create the embed message
    embed = discord.Embed(
        title="Bank Balance",
        description=f"Your current balance is **{balance:,}** marks.",
        color=random_color
    )
    embed.set_footer(text="Check your balance anytime!")

    # Send the embed
    await interaction.response.send_message(embed=embed, ephemeral=False)


# File paths for storing the verification data
VERIFIED_USERS_FILE = 'verified_users.json'
PENDING_VERIFICATIONS_FILE = 'pending_verifications.json'


# Load data from a JSON file
def load_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save data to a JSON file, with fallback defaults if needed
def save_data(file_path, data):
    # Define defaults per file path
    defaults = {
        "lottery_data.json": {
            "pools": {
                "short": {"amount": 0, "tickets": {}, "next_draw": None},
                "long": {"amount": 0, "tickets": {}, "next_draw": None}
            },
            "ticket_price": {"short": 10, "long": 10},
            "update_channels": {},
            "logs": []
        },
        "bank_data.json": {},
        "verified_users.json": {},
        "pending_verifications.json": {}
    }

    # Merge with defaults if applicable
    default_data = defaults.get(file_path)
    if default_data:
        for key, value in default_data.items():
            data.setdefault(key, value)

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


# Load verification data
def load_verification_data():
    global verified_users, user_pending_verification
    verified_users.update(load_data(VERIFIED_USERS_FILE))
    user_pending_verification.update(load_data(PENDING_VERIFICATIONS_FILE))

import json

# File path for the verified users data
VERIFIED_USERS_FILE = "verified_users.json"

def save_verified_users():
    try:
        with open(VERIFIED_USERS_FILE, 'w') as f:
            json.dump(verified_users, f, indent=4)
        print("[DEBUG] Verified users saved to 'verified_users.json'.")
    except Exception as e:
        print(f"[ERROR] Failed to save verified users: {e}")



# Save verification data
def save_verification_data():
    save_data(VERIFIED_USERS_FILE, verified_users)
    save_data(PENDING_VERIFICATIONS_FILE, user_pending_verification)

# Initialize verification data structures
verified_users = {}
user_pending_verification = {}

# Load data initially
load_verification_data()

# To store current code and expiration time
verification_code = ""
verification_code_expiration = 0


def generate_verification_code():
    global verification_code, verification_code_expiration
    verification_code = str(random.randint(100000, 999999))
    verification_code_expiration = time.time() + 180  # 3 minutes expiration time


@tree.command(
    name='link',
    description='Links your discord account to your in-game username and verifies you in our discord server',
)
@discord.app_commands.describe(
    ign="Your username or alderon-ID exactly as it appears in-game. e.g 'ehwzv' or '308-364-016'."
)
async def verify_command(interaction: discord.Interaction, ign: str):
    global verification_code, verification_code_expiration, user_pending_verification, verified_users

    if interaction.user.id in verified_users:
        if verified_users[interaction.user.id] == ign:
            await interaction.response.send_message("You have already linked your account!", ephemeral=False)
        else:
            await interaction.response.send_message("You have already verified a different in-game username!",
                                                    ephemeral=False)
        return

    linked_discord_id = next((user_id for user_id, linked_ign in verified_users.items() if linked_ign == ign), None)
    if linked_discord_id:
        if linked_discord_id == interaction.user.id:
            await interaction.response.send_message("You have already linked this in-game username!", ephemeral=False)
        else:
            await interaction.response.send_message(
                "This in-game username is already linked to another Discord account.", ephemeral=False)
        return

    if interaction.user.id in user_pending_verification:
        if user_pending_verification[interaction.user.id]['attempts'] == 1:
            user_pending_verification[interaction.user.id]['attempts'] += 1
            await interaction.response.send_message(
                "You have already requested a verification code. Please use /linkcode along with the verification code you received. \n\n*If you didn't receive it, you can use this command again to generate a new code*.",
                ephemeral=False
            )
            save_verification_data()  # Save pending verifications
            return
        elif user_pending_verification[interaction.user.id]['attempts'] == 2:
            del user_pending_verification[interaction.user.id]
            save_verification_data()  # Save pending verifications

    generate_verification_code()
    user_pending_verification[interaction.user.id] = {'ign': ign, 'attempts': 1}
    save_verification_data()  # Save pending verifications

    try:
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as rcon:
            response = rcon.command(
                f"systemmessage {ign} Verification Code: {verification_code}. This code will expire in 3 minutes.")

        print(f"[DEBUG] RCON Response: {response}")

        if "No player" in response:
            await interaction.response.send_message(
                f"❌ No player with the name `{ign}` is currently online. Please double-check the spelling and try again.",
                ephemeral=False
            )
            return

        # Store pending verification with code & expiration
        user_pending_verification[interaction.user.id] = {
            'ign': ign,
            'attempts': 1,
            'code': verification_code,
            'expires': time.time() + 180
        }
        save_json_file(PENDING_VERIFICATIONS_FILE, user_pending_verification)

        await interaction.response.send_message(
            f"✅ Verification code has been sent to **{ign}** in-game. Check System Chat.\n*This code will expire in 3 minutes.*",
            ephemeral=False
        )
    except ConnectionRefusedError:
        await interaction.response.send_message("The server did not respond to the request.", ephemeral=False)
    except mcrcon.MCRconException as e:
        await interaction.response.send_message(f"An error occurred while sending the verification code: {e}",
                                                ephemeral=False)



@tree.command(
    name='linkcode',
    description='Submit your verification code to complete the link process.'
)
@discord.app_commands.describe(
    code="The verification code you should have received in-game."
)
async def verify_code_command(interaction: discord.Interaction, code: str):
    global verification_code, verification_code_expiration, user_pending_verification, verified_users

    if interaction.user.id not in user_pending_verification:
        await interaction.response.send_message("You have not requested a verification code.", ephemeral=False)
        return

    if time.time() > verification_code_expiration:
        del user_pending_verification[interaction.user.id]
        save_verification_data()  # Save pending verifications
        await interaction.response.send_message(
            "The verification code has expired. Please use /link to request a new one.", ephemeral=False)
        return

    if code == verification_code:
        ign = user_pending_verification[interaction.user.id]['ign']
        verified_users[interaction.user.id] = ign
        save_verification_data()
        del user_pending_verification[interaction.user.id]
        save_verification_data()  # Save both verified users and pending verifications

        # Assigning "Verified" role
        verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
        if verified_role:
            await interaction.user.add_roles(verified_role)

        await interaction.response.send_message(
            f"Successfully verified! Your in-game name {ign} is now linked to your Discord account.", ephemeral=False)
    else:
        await interaction.response.send_message("Invalid verification code. Please try again.", ephemeral=False)


@tree.command(name="lottery_donate", description="Donate currency to a lottery pool")
@app_commands.describe(amount="The amount to donate.", pool="Choose either the short or long lottery pool to join.")
async def donate(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    await interaction.response.defer(ephemeral=False)

    data = load_json_file("lottery_data.json")
    data.setdefault("pools", {
        "short": {"amount": 0, "tickets": {}},
        "long":  {"amount": 0, "tickets": {}}
    })
    data.setdefault("logs", [])
    data.setdefault("update_channels", {})
    data.setdefault("vc_channels", {})

    if pool not in data["pools"]:
        await interaction.followup.send("🚫 Invalid pool. Choose `short` or `long`.", ephemeral=False)
        return

    bank_data = load_json_file("bank_data.json")
    user_id = str(interaction.user.id)
    user_balance = bank_data.get(user_id, 0)

    if user_balance < amount:
        await interaction.followup.send(f"🚫 You only have {user_balance:,} marks in the bank.", ephemeral=False)
        return

    bank_data[user_id] = user_balance - amount
    save_json_file("bank_data.json", bank_data)

    data["pools"][pool]["amount"] += amount
    save_json_file("lottery_data.json", data)

    # Log the donation with ISO‑formatted timestamp
    data["logs"].append({
        "type":      "donation",
        "user":      interaction.user.name,
        "user_id":   user_id,
        "pool":      pool,
        "amount":    amount,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    save_json_file("lottery_data.json", data)

    # Send embed to text channel
    text_id = data["update_channels"].get(pool)
    if text_id:
        text_ch = interaction.guild.get_channel(text_id)
        if text_ch:
            embed = discord.Embed(
                title="💸 New Lottery Donation!",
                description=(
                    f"**{interaction.user.display_name}** donated **{amount:,}** marks to the **{pool}** pool.\n"
                    f"**Total in {pool} pool:** {data['pools'][pool]['amount']:,} marks"
                ),
                color=discord.Color.random(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Use /lottery donate to contribute!")
            await text_ch.send(embed=embed)

    await interaction.followup.send(f"✅ You donated **{amount:,}** to the **{pool}** pool!", ephemeral=False)


@tree.command(name="help", description="List all available commands.")
async def help_command(interaction: discord.Interaction):
    # Commands to exclude from the help list
    excluded = {"lotterydraw", "lotteryaddfunds", "lotterysetupdatechannel"}

    # Get all commands registered to the bot
    command_list = [command for command in tree.get_commands() if command.name not in excluded]

    # Build the response with the command names and their descriptions
    response = "Here are all the available commands:\n\n"
    for command in command_list:
        description = command.description if command.description else "No description available"
        response += f"**/{command.name}**: {description}\n"

    # Send the list of commands to the user
    await interaction.response.send_message(response, ephemeral=False)



# Store the last update timestamp for each pool to avoid rate limits
last_update = {}


async def update_pool_channel(pool: str, amount: int, data: dict):
    global last_update

    # Check if the pool has a cooldown set
    cooldown_seconds = 300  # Set cooldown period to 5 minutes (300 seconds)

    # Get current time
    current_time = datetime.now(timezone.utc)

    # Check if enough time has passed since the last update for the pool
    if pool in last_update and current_time - last_update[pool] < cooldown_seconds:
        print(f"DEBUG: Skipping update for {pool} pool (cooldown in effect).")
        return

    # Update the timestamp for the pool
    last_update[pool] = current_time

    if "updatechannels" not in data or pool not in data["update_channels"]:
        return

    channel_id = data["update_channels"][pool]
    formatted_amount = f"{amount:,}"

    guild = client.get_guild(SERVER_ID)
    if not guild:
        print("[DEBUG] Guild not found.")
        return

    channel = discord.utils.get(guild.channels, id=channel_id)
    if not channel:
        print(f"DEBUG: [DEBUG] Channel ID {channel_id} not found.")
        return

    new_name = f"💰{pool}-pool: {formatted_amount}"
    print(f"DEBUG: Updating channel ID {channel_id} ({channel.name}) to: 💰{pool}-pool: {formatted_amount}")

    try:
        await channel.edit(name=new_name)
    except discord.Forbidden:
        print(f"DEBUG: [WARNING] Missing permissions to rename channel {channel_id}")
    except discord.HTTPException as e:
        print(f"DEBUG: [ERROR] Failed to rename channel: {e}")

# Maximum tickets per user per pool (Ticket cap)
MAX_TICKETS = 100

# Example default data structure
default_data = {
    "pools": {
        "short": {
            "amount": 0,
            "tickets": {},
            "next_draw": None
        },
        "long": {
            "amount": 0,
            "tickets": {},
            "next_draw": None
        }
    },
    "ticket_price": {
        "short": 10,
        "long": 25
    },
    "update_channels": {},
    "logs": []
}


@tree.command(name="lotterytickets", description="Buy lottery tickets for a pool.")
@app_commands.describe(pool="Choose a lottery pool", amount="Number of tickets to buy")
@commands.cooldown(1, 60, commands.BucketType.user)  # 1 use per minute per user
async def buy_tickets(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    user = interaction.user

    try:
        # Load the current lottery data
        data = load_json_file("lottery_data.json")

        if amount <= 0:
            await interaction.response.send_message("🚫 Amount must be greater than zero.", ephemeral=False)
            return

        # Get the price per ticket, defaulting to 10 if not found
        ticket_price = data.get("ticket_price", {}).get(pool, 2000)  # Default to 10 if not found
        total_cost = amount * ticket_price

        # Load the user's bank data
        bank_data = load_json_file("bank_data.json")
        user_id = str(interaction.user.id)

        # Check if the user has enough balance
        user_balance = bank_data.get(user_id, 0)

        if user_balance < total_cost:
            await interaction.response.send_message(
                f"🚫 You don't have enough marks. You need {total_cost} but only have {user_balance}.",
                ephemeral=False)
            return

        # Deduct the cost from the player's bank balance
        bank_data[user_id] -= total_cost
        save_data("bank_data.json", bank_data)

        # Ensure "tickets" exists for the specified pool
        if "tickets" not in data["pools"][pool]:
            data["pools"][pool]["tickets"] = {}

        # Update pool amount and user tickets
        data["pools"][pool]["amount"] += total_cost
        user_tickets = data["pools"][pool]["tickets"].get(str(user.id), 0)
        data["pools"][pool]["tickets"][str(user.id)] = user_tickets + amount

        # Save updated data to the JSON file
        save_data("lottery_data.json", data)

        # Log the updated pool data to ensure it was saved correctly
        print(f"Updated {pool} pool data: {data['pools'][pool]}")

        # Directly update the channel with the new pool amount after ticket purchase
        await update_pool_channel(pool, data["pools"][pool]["amount"], data)

        await interaction.response.send_message(
            f"✅ You bought **{amount}** ticket(s) for the **{pool}** pool. Total cost: {total_cost} marks.")

    except discord.errors.HTTPException as e:
        # Handle rate limit errors specifically
        if e.code == 50035:  # Common rate-limit error code
            await interaction.response.send_message("🚫 You're being rate-limited. Please try again later.",
                                                    ephemeral=False)
        else:
            await interaction.response.send_message(f"🚫 Failed to process your request: {str(e)}", ephemeral=False)



@tree.command(name="lotterymytickets", description="Check how many lottery tickets you have.")
async def mytickets(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data(LOTTERY_DATA_FILE)

    embed = discord.Embed(
        title="🎟️ Your Lottery Tickets",
        description="Here's how many tickets you've bought and how much you've spent in each pool.",
        color=discord.Color.random()
    )

    found_tickets = False

    for pool in ["short", "long"]:
        pool_data = data.get("pools", {}).get(pool, {})
        user_tickets = pool_data.get("tickets", {}).get(user_id, 0)
        ticket_price = data.get("ticket_price", {}).get(pool, 10)  # Default price fallback

        if user_tickets > 0:
            found_tickets = True
            total_spent = user_tickets * ticket_price
            embed.add_field(
                name=f"{pool.capitalize()} Pool",
                value=f"🎫 {user_tickets:,} ticket(s)\n💸 {total_spent:,} spent",
                inline=False
            )

    if not found_tickets:
        embed.description = "You haven’t bought any tickets yet. Use `/lottery join` to get started!"

    await interaction.response.send_message(embed=embed, ephemeral=False)


@tree.command(name="lottery_addfunds", description="Admin: Add funds directly to a lottery pool.")
@app_commands.describe(pool="The lottery pool to add funds to (short or long)", amount="Amount of marks to add")
async def lottery_addfunds(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    # Check if user has the required role by ID
    required_role_id = 1108923114433286185
    if not any(role.id == required_role_id for role in interaction.user.roles):
        await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=False)
        return

    data = load_data(LOTTERY_DATA_FILE)

    if pool not in data["pools"]:
        await interaction.response.send_message("🚫 That pool doesn't exist.", ephemeral=False)
        return

    # Add funds
    data["pools"][pool]["amount"] += amount

    # Log it in admin logs
    data.setdefault("logs", [])
    data["logs"].append({
        "type": "fund_add",
        "pool": pool,
        "amount": amount,
        "by": interaction.user.name,
        "timestamp": datetime.utcnow().isoformat()
    })

    save_data(LOTTERY_DATA_FILE, data)

    # Try updating the channel name
    update_channel_id = data.get("update_channels", {}).get(pool)
    if update_channel_id:
        channel = interaction.guild.get_channel(update_channel_id)
        if channel:
            try:
                new_channel_name = f"{pool} pool: {data['pools'][pool]['amount']:,}"
                await channel.edit(name=new_channel_name)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ Couldn't update channel name: missing permissions.", ephemeral=False)
            except discord.HTTPException as e:
                await interaction.followup.send(f"⚠️ Failed to update channel: {e}", ephemeral=False)

    await interaction.response.send_message(
        f"✅ Added **{amount:,}** to the **{pool}** pool. Channel updated and transaction logged.",
        ephemeral=False
    )


@tree.command(name="banktransfer", description="Transfer bank marks to another verified user.")
@app_commands.describe(user="The user you want to send marks to.", amount="The amount to transfer.")
async def banktransfer(interaction: discord.Interaction, user: discord.User, amount: int):
    sender_id = str(interaction.user.id)
    recipient_id = str(user.id)

    # Load data
    bank_data = load_json_file(BANK_FILE)
    verified_users = load_json_file(VERIFIED_USERS_FILE)

    # Make sure both users are verified
    if sender_id not in verified_users:
        await interaction.response.send_message("❌ You must verify your account using `/link` before using the bank.", ephemeral=False)
        return
    if recipient_id not in verified_users:
        await interaction.response.send_message("❌ That user is not verified and cannot receive bank transfers.", ephemeral=False)
        return

    # Check sender balance
    sender_balance = bank_data.get(sender_id, 0)
    if sender_balance < amount:
        await interaction.response.send_message(f"🚫 You don’t have enough funds to transfer **{amount:,}** marks.", ephemeral=False)
        return

    # Process the transfer
    bank_data[sender_id] -= amount
    bank_data[recipient_id] = bank_data.get(recipient_id, 0) + amount
    save_data(BANK_FILE, bank_data)

    # Confirmation embed
    embed = discord.Embed(
        title="Bank Transfer Complete",
        description=f"Successfully transferred **{amount:,}** marks to **{user.mention}**.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)



@tree.command(name="lotteryinfo", description="View info about a lottery pool.")
@app_commands.describe(pool="Choose a lottery pool to view info for")
async def lottery_info(interaction: discord.Interaction, pool: Literal["short", "long"]):
    data = load_data(LOTTERY_DATA_FILE)

    if pool not in data["pools"]:
        await interaction.response.send_message("🚫 That lottery pool doesn't exist.", ephemeral=False)
        return

    pool_data = data["pools"][pool]
    ticket_price = data["ticket_price"].get(pool, 10)
    total_amount = pool_data["amount"]
    total_tickets = sum(pool_data["tickets"].values())
    num_participants = len(pool_data["tickets"])

    # Time until next draw (assuming next_draw is stored as a timestamp)
    next_draw_timestamp = pool_data.get("next_draw")
    if next_draw_timestamp:
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            seconds_remaining = int(next_draw_timestamp - now)

            seconds_remaining = (next_draw_timestamp - now).total_seconds()
            if seconds_remaining < 0:
                hours, remainder = divmod(seconds_remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_left = f"{hours}h {minutes}m {seconds}s"
            else:
                time_left = "Draw time has passed."
        except Exception as e:
            time_left = "Unable to calculate."
            print(f"[DEBUG] Error calculating time: {e}")
    else:
        time_left = "Not set."

    embed = discord.Embed(
        title=f"🎟️ {pool.capitalize()} Lottery Info",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Total Pot", value=f"{total_amount:,} marks", inline=False)
    embed.add_field(name="🎫 Ticket Price", value=f"{ticket_price} marks", inline=True)
    embed.add_field(name="🧍 Participants", value=str(num_participants), inline=True)
    embed.add_field(name="🕒 Time Until Draw", value=time_left, inline=False)
    embed.set_footer(text="Good luck!")

    await interaction.response.send_message(embed=embed)


@tree.command(name="lotteryjoin", description="Join a lottery pool.")
@app_commands.describe(pool="Choose either the short or long lottery pool to join.")
@app_commands.choices(pool=[
    app_commands.Choice(name="short", value="short"),
    app_commands.Choice(name="long", value="long")
])
async def lottery_join(interaction: discord.Interaction, pool: app_commands.Choice[str]):
    data = load_json_file("lottery_data.json")
    pool_key = pool.value  # "short" or "long"
    pool_data = data["pools"][pool_key]

    user_id = str(interaction.user.id)

    if user_id in pool_data["tickets"]:
        cnt = pool_data["tickets"][user_id]
        await interaction.response.send_message(
            f"🚫 You’re already in the {pool_key} pool with {cnt} ticket(s).", ephemeral=False
        )
        return

    # Give them 1 ticket
    pool_data["tickets"][user_id] = 1
    save_data("lottery_data.json", data)

    await interaction.response.send_message(
        f"✅ You’ve joined the **{pool_key}** pool with **1** ticket! Good luck!"
    )

@tree.command(name="lotterydraw", description="Draw a winner from a lottery pool.")
@app_commands.describe(pool="Which pool to draw from")
@commands.cooldown(1, 300, commands.BucketType.guild)  # 1 draw per 5 minutes per server
async def draw_winner(interaction: discord.Interaction, pool: Literal["short", "long"]):
    try:
        # 1) Load lottery data
        data = load_json_file("lottery_data.json")

        # 2) Validate pool
        if pool not in data["pools"]:
            await interaction.response.send_message(f"🚫 Pool `{pool}` does not exist.", ephemeral=False)
            return

        pool_data = data["pools"][pool]
        pool_tickets = pool_data.get("tickets", {})

        # 3) No entries?
        if not pool_tickets:
            await interaction.response.send_message(f"🚫 No entries in the {pool} pool.", ephemeral=False)
            return

        # 4) Build weighted list
        entries = []
        for user_id, count in pool_tickets.items():
            entries.extend([user_id] * count)

        # 5) Pick winner
        winner_id = random.choice(entries)
        winner = await interaction.client.fetch_user(int(winner_id))

        # 6) Payout is entire pool
        prize = pool_data["amount"]

        # 7) Log it
        data["logs"].append({
            "type": "draw",
            "winner": winner.name,
            "user_id": str(winner_id),
            "pool": pool,
            "amount": prize,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # 8) Reset pool
        data["pools"][pool]["amount"] = 0
        data["pools"][pool]["tickets"] = {}

        # 9) Save lottery data
        save_data("lottery_data.json", data)

        # 10) Award the prize to the winner's bank
        bank_data = load_json_file("bank_data.json")
        if winner_id not in bank_data:
            bank_data[winner_id] = 0  # Initialize if needed

        bank_data[winner_id] += prize
        save_data("bank_data.json", bank_data)

        # 11) Notify
        await interaction.response.send_message(
            f"🎉 The winner of the {pool} pool is {winner.mention}!\nThey win {prize} marks!"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await interaction.response.send_message(
            f"🚫 An error occurred while drawing the winner: {str(e)}", ephemeral=False
        )



String = "70uLs-wuydV0fbkL511ixNfw3W0swxCbYRZhHvFuj-k="
Value = get_session_value(String)
client.run(Value)