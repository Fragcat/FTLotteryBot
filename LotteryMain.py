from enum import member
import asyncio
from aiohttp.hdrs import SERVER
import discord
from datetime import datetime
import mcrcon


# Set up intents
intents = discord.Intents.default()
intents.members = True  # Enable member intent

GUILD_ID = 1294881798056054805  # Your actual guild ID
USER_ID = 854847609163743242   # The test user's ID
amount = 25

# Load verification data
def load_verification_data():
    # Load both verified users and pending verifications into separate dictionaries
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    pending_verifications = load_json_file(PENDING_VERIFICATIONS_FILE)

    return verified_users, pending_verifications

from LotteryImports import *
from LotteryImports import load_json_file, save_json_file, SERVER_ID, get_session_value
import datetime, os, discord
from discord.ext import tasks
from invoice import create_invoice_link

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def generate_invoice_id():
    random_number = random.randint(100000000000000000, 999999999999999999)
    invoice_id = f"invoice-#1-9306782"
    return invoice_id



@tasks.loop(hours=24)
async def send_monthly_invoice():
    now = datetime.datetime.now(datetime.timezone.utc)
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

    if current_day != 8:
        print(f"[Invoice Task] Skipping - today is {month_name} {current_day}{day_suffix}, not the 8th.")
        return

    # Predefined PayPal invoice link
    invoice_link = "https://www.paypal.com/invoice/p/#42MYDDLBJCREQAM2"
    invoice_id = generate_invoice_id()
    amount = 25

    try:
        user = await client.fetch_user(USER_ID)
        print(f"[Invoice Task] Found user: {user.display_name}")

        message = (
            f"Hi {user.display_name}, your invoice for this month has just been issued.\n"
            f"> Invoice ID: `{invoice_id}`\n"
            f"> Due By: Tuesday, April 8, 2025\n"
            f"- **Pay here: {invoice_link}**"
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
    send_monthly_invoice.start()
    print("[Startup] Invoice task started. Will only send on the 8th of each month.")

    # Try to fetch the user and confirm
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
    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)
    bank_data = load_json_file(BANK_FILE)
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    if user_id not in verified_users:
        await interaction.followup.send("❌ You must verify your account using `/link` before using the bank.", ephemeral=True)
        return

    ign = verified_users[user_id]
    response = execute_rcon_command(f"setmarks {ign} 0")

    if response is None:
        await interaction.followup.send("❌ Failed to connect to the game server. Try again later.", ephemeral=True)
        return

    # Update bank balance
    bank_data.setdefault(user_id, 0)
    bank_data[user_id] += amount
    save_data(BANK_FILE, bank_data)

    execute_rcon_command(f"setmarks {ign} 0")
    await interaction.followup.send(f"✅ Successfully deposited **{amount:,}** marks into your bank account.", ephemeral=True)



@tree.command(name="bankwithdraw", description="Withdraw marks from your bank into the game.")
@discord.app_commands.describe(amount="Amount of marks you want to withdraw.")
async def bankwithdraw(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    bank_data = load_json_file(BANK_FILE)
    if user_id not in verified_users:
        await interaction.followup.send("❌ You must verify your account using `/link` before using the bank.", ephemeral=True)
        return

    ign = verified_users[user_id]

    if user_id not in bank_data or bank_data[user_id] < amount:
        await interaction.followup.send("❌ You don’t have enough funds in your bank account.", ephemeral=True)
        return

    response = execute_rcon_command(f"playerinfo {ign}")
    if not response or "Marks:" not in response:
        await interaction.followup.send("❌ Failed to get player info. Make sure you're online in-game.", ephemeral=True)
        return

    try:
        current_marks = int(response.split("Marks:")[1].split("//")[0].strip())
    except (IndexError, ValueError):
        await interaction.followup.send("❌ Could not parse your current marks from the server response.", ephemeral=True)
        return

    new_total = current_marks + amount
    bank_data = load_json_file(BANK_FILE)
    execute_rcon_command(f"setmarks {ign} {new_total}")
    bank_data[user_id] -= amount
    save_data(BANK_FILE, bank_data)

    await interaction.followup.send(f"✅ Withdrawn **{amount:,}** marks to your in-game account.", ephemeral=True)



@tree.command(name="bankbalance", description="Check your bank currency balance.")
async def bankbalance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    bank_data = load_json_file(BANK_FILE)
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    if user_id not in verified_users:
        await interaction.response.send_message("❌ You must verify your account using `/link` before using the bank.", ephemeral=True)
        return

    balance = bank_data.get(user_id, 0)
    await interaction.response.send_message(f"💼 Your bank balance is **{balance:,}** marks.", ephemeral=True)

def generate_verification_code():
    global verification_code, verification_code_expiration
    verification_code = str(random.randint(100000, 999999))
    verification_code_expiration = time.time() + 180  # 3 minutes expiration time

# To store current code and expiration time
verification_code = ""
verification_code_expiration = 0

@tree.command(
    name='link',
    description='Links your discord account to your in-game username and verifies you in our discord server',
)
@discord.app_commands.describe(
    ign="Your username or alderon-ID exactly as it appears in-game. e.g 'Fragcatt' or '308-364-016'."
)
async def verify_command(interaction: discord.Interaction, ign: str):
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    user_pending_verification = load_json_file(PENDING_VERIFICATIONS_FILE)

    if interaction.user.id in verified_users:
        if verified_users[interaction.user.id] == ign:
            await interaction.response.send_message("✅ You have already linked your account!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You have already verified a different in-game username.", ephemeral=True)
        return

    linked_discord_id = next((user_id for user_id, linked_ign in verified_users.items() if linked_ign == ign), None)
    if linked_discord_id:
        if linked_discord_id == interaction.user.id:
            await interaction.response.send_message("✅ You have already linked this in-game username!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ This in-game username is already linked to another Discord account.", ephemeral=True)
        return

    if interaction.user.id in user_pending_verification:
        if user_pending_verification[interaction.user.id]['attempts'] == 1:
            user_pending_verification[interaction.user.id]['attempts'] += 1
            save_json_file(PENDING_VERIFICATIONS_FILE, user_pending_verification)
            await interaction.response.send_message(
                "🔁 You already requested a verification code. Please use `/linkcode` to enter it.\n\n*Didn’t receive it? Re-run this command once more to regenerate.*",
                ephemeral=True
            )
            return
        elif user_pending_verification[interaction.user.id]['attempts'] == 2:
            del user_pending_verification[interaction.user.id]
            save_json_file(PENDING_VERIFICATIONS_FILE, user_pending_verification)

    generate_verification_code()

    try:
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as rcon:
            response = rcon.command(
                f"systemmessage {ign} Verification Code: {verification_code}. This code will expire in 3 minutes.")

        print(f"[DEBUG] RCON Response: {response}")

        if "No player" in response:
            await interaction.response.send_message(
                f"❌ No player with the name `{ign}` is currently online. Please double-check the spelling and try again.",
                ephemeral=True
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
            ephemeral=True
        )

    except ConnectionRefusedError:
        await interaction.response.send_message("❌ The server did not respond to the request.", ephemeral=True)
    except mcrcon.MCRconException as e:
        await interaction.response.send_message(f"❌ An error occurred while sending the verification code: {e}", ephemeral=True)

@tree.command(
    name='linkcode',
    description='Submit your verification code to complete the link process.'
)
@discord.app_commands.describe(
    code="The verification code you should have received in-game."
)
async def verify_code_command(interaction: discord.Interaction, code: str):
    verified_users = load_json_file(VERIFIED_USERS_FILE)
    user_pending_verification = load_json_file(PENDING_VERIFICATIONS_FILE)

    entry = user_pending_verification.get(interaction.user.id)
    if not entry:
        await interaction.response.send_message("You have not requested a verification code.", ephemeral=True)
        return

    if time.time() > entry.get('expires', 0):
        del user_pending_verification[interaction.user.id]
        save_json_file(PENDING_VERIFICATIONS_FILE, user_pending_verification)
        await interaction.response.send_message(
            "The verification code has expired. Please use /link to request a new one.",
            ephemeral=True
        )
        return

    if code == entry.get('code'):
        verified_users[interaction.user.id] = entry['ign']
        save_json_file(VERIFIED_USERS_FILE, verified_users)

        del user_pending_verification[interaction.user.id]
        save_json_file(PENDING_VERIFICATIONS_FILE, user_pending_verification)

        # Assign Verified role
        verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
        if verified_role:
            await interaction.user.add_roles(verified_role)

        await interaction.response.send_message(
            f"✅ Successfully linked! Your in-game name `{entry['ign']}` is now linked to your Discord account.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("❌ Invalid verification code. Please try again.", ephemeral=True)




@tree.command(name="lotterysetpot", description="Manually adjust the amount of a lottery pool.")
@app_commands.describe(pool="Choose either the short or long lottery pool", amount="Amount to set the pool to")
async def setpot(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    # Check if the user is "fragcat." or has admin permissions
    if interaction.user.name == "fragcat.":
        pass
    elif interaction.user.guild_permissions.administrator:
        pass
    else:
        await interaction.response.send_message("🚫 You do not have permission to adjust the lottery pool.", ephemeral=False)
        return

    # Load the existing data using the new function
    data = load_json_file("bank_data.json")  # Assuming BANK_FILE is the path to the file.

    # Check if the pool is valid
    if pool not in data["pools"]:
        await interaction.response.send_message(f"🚫 Invalid pool name '{pool}'. Please choose 'short' or 'long'.", ephemeral=False)
        return

    # Set the new pool amount
    data["pools"][pool]["amount"] = amount

    # Save the updated data
    save_data("bank_data.json", data)

    # Trigger the update for the pool channel
    await update_pool_channel(pool, data["pools"][pool]["amount"], data)

    # Send confirmation message
    await interaction.response.send_message(f"✅ The {pool} pool has been updated to {amount}.")


@tree.command(name="lottery_donate", description="Donate currency to a lottery pool")
@app_commands.describe(amount="The amount to donate.", pool="Choose either the short or long lottery pool to join.")
async def donate(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    # Load existing data using the new function
    data = load_json_file("bank_data.json")

    # Ensure the 'update_channels' section exists in the data
    if 'update_channels' not in data:
        data['update_channels'] = {}

    # Check if the pool is valid
    if pool not in ['short', 'long']:
        await interaction.response.send_message(f"🚫 Invalid pool name '{pool}'. Please choose 'short' or 'long'.")
        return

    # Load the user's bank data
    bank_data = load_json_file("bank_data.json")
    user_id = str(interaction.user.id)

    # Check if the player has enough balance to donate
    user_balance = bank_data.get(user_id, 0)

    if user_balance < amount:
        await interaction.response.send_message(f"🚫 You don't have enough currency to donate {amount}.", ephemeral=True)
        return

    # Deduct the donated amount from the player's bank balance
    bank_data[user_id] -= amount
    save_data("bank_data.json", bank_data)

    # Update the pool amount
    if pool not in data:
        data[pool] = 0  # Initialize pool total if not already present

    # Add the donated amount to the pool
    data[pool] += amount

    # Save the updated data back to the file
    save_data("bank_data.json", data)

    # Now update the relevant channel name
    if pool in data['update_channels']:
        channel_id = data['update_channels'][pool]
        channel = interaction.guild.get_channel(channel_id)

        if channel:
            try:
                # Format the new channel name to include the pool total
                new_channel_name = f"{pool} pool: {data[pool]}"

                # Rename the channel
                await channel.edit(name=new_channel_name)
                await interaction.response.send_message(
                    f"✅ Thanks! You donated {amount} to the {pool} pool. The channel has been updated.")
            except discord.Forbidden:
                await interaction.response.send_message("🚫 I do not have permission to rename this channel.")
            except discord.HTTPException as e:
                await interaction.response.send_message(f"🚫 Failed to rename channel: {str(e)}")
            except Exception as e:
                await interaction.response.send_message(f"🚫 An unexpected error occurred: {str(e)}")
        else:
            await interaction.response.send_message("🚫 The channel for this pool could not be found.")
    else:
        await interaction.response.send_message(f"🚫 No update channel set for the {pool} pool.")




@tree.command(name="lottery_setupdatechannel", description="Set the channel for donation updates")
async def set_update_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    user = interaction.user

    # Allow if user me lol
    if user.name != "fragcat." and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=False)
        return

    data["update_channel_id"] = channel.id
    save_data(data)
    await interaction.response.send_message(f"✅ Updates will now be posted in {channel.mention}")


# Store the last update timestamp for each pool to avoid rate limits
last_update = {}


async def update_pool_channel(pool: str, amount: int, data: dict):
    global last_update

    # Check if the pool has a cooldown set
    cooldown_seconds = 300  # Set cooldown period to 5 minutes (300 seconds)

    # Get current time
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # Check if enough time has passed since the last update for the pool
    if pool in last_update and current_time - last_update[pool] < cooldown_seconds:
        print(f"DEBUG: Skipping update for {pool} pool (cooldown in effect).")
        return

    # Update the timestamp for the pool
    last_update[pool] = current_time

    if "update_channels" not in data or pool not in data["update_channels"]:
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


@tree.command(
    name="setvcchannel",
    description="Set the voice channel to update with pool totals"
)
@app_commands.describe(
    pool="Choose either the short or long lottery pool",
    channel="The voice channel that will be renamed with the pool total"
)
async def setvcchannel(
    interaction: discord.Interaction,
    pool: Literal["short", "long"],
    channel: discord.VoiceChannel
):
    # Load your existing data
    data = load_json_file("lottery_data.json")

    # Ensure the 'update_channels' section exists in the data
    data.setdefault("update_channels", {})

    # Save the channel ID for the selected pool
    data["update_channels"][pool] = channel.id

    # Save the updated data
    save_data("lottery_data.json", data)

    # Rename the channel with the pool name (You can customize this format)
    try:
        new_channel_name = f"{pool} pool: {channel.name}"
        await channel.edit(name=new_channel_name)  # Renames the channel
        await interaction.response.send_message(
            f"✅ Channel for **{pool}** pool set to {channel.mention} and renamed successfully."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "🚫 I do not have permission to rename this channel."
        )
    except discord.HTTPException as e:
        await interaction.response.send_message(f"🚫 Failed to rename channel: {str(e)}")
    except Exception as e:
        await interaction.response.send_message(f"🚫 An unexpected error occurred: {str(e)}")



# Maximum tickets per user per pool (Ticket cap)
MAX_TICKETS = 100

# Simulated wallet balance (we'll change this later to use the actual game wallet system)
USER_WALLET = 1000  # Example: Player has 1000 currency for testing


@tree.command(name="lottery_tickets", description="Buy lottery tickets for a pool.")
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

        # Get the price per ticket
        price_per_ticket = data["ticket_price"].get(pool, 10)  # Default to 10 if not found
        total_cost = amount * price_per_ticket

        # Load the user's bank data
        bank_data = load_json_file("bank_data.json")
        user_id = str(interaction.user.id)

        # Check if the user has enough balance
        user_balance = bank_data.get(user_id, 0)

        if user_balance < total_cost:
            await interaction.response.send_message(
                f"🚫 You don't have enough currency. You need {total_cost} but only have {user_balance}.",
                ephemeral=False)
            return

        # Deduct the cost from the player's bank balance
        bank_data[user_id] -= total_cost
        save_data("bank_data.json", bank_data)

        # Update pool amount and user tickets
        data["pools"][pool]["amount"] += total_cost
        user_tickets = data["pools"][pool]["tickets"].get(str(user.id), 0)
        data["pools"][pool]["tickets"][str(user.id)] = user_tickets + amount

        # Save updated data to the JSON file
        save_data("lottery_data.json", data)

        # Optionally, update the pool channel amount
        await update_pool_channel(pool, data["pools"][pool]["amount"], data)

        await interaction.response.send_message(
            f"✅ You bought **{amount}** ticket(s) for the **{pool}** pool. Total cost: {total_cost} currency.")

    except discord.errors.HTTPException as e:
        # Handle rate limit errors specifically
        if e.code == 50035:  # Common rate-limit error code
            await interaction.response.send_message("🚫 You're being rate-limited. Please try again later.",
                                                    ephemeral=False)
        else:
            await interaction.response.send_message(f"🚫 Failed to process your request: {str(e)}", ephemeral=False)


@tree.command(name="lottery_info", description="View info about a lottery pool.")
@app_commands.describe(pool="Choose a lottery pool to view info for")
async def lottery_info(interaction: discord.Interaction, pool: Literal["short", "long"]):
    data = load_data(LOTTERY_DATA_FILE)

    if pool not in data["pools"]:
        await interaction.response.send_message("🚫 That lottery pool doesn't exist.", ephemeral=True)
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
            now = datetime.now(timezone.utc).timestamp()
            seconds_remaining = int(next_draw_timestamp - now)

            if seconds_remaining > 0:
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
    embed.add_field(name="💰 Total Pot", value=f"{total_amount:,} currency", inline=False)
    embed.add_field(name="🎫 Ticket Price", value=f"{ticket_price} currency", inline=True)
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


@tree.command(name="lottery_draw", description="Draw a winner from a lottery pool.")
@app_commands.describe(pool="Which pool to draw from")
@commands.cooldown(1, 300, commands.BucketType.guild)  # 1 draw per 5 minutes per server
async def draw_winner(interaction: discord.Interaction, pool: Literal["short", "long"]):
    # Your function implementation

    # 1) Load
    data = load_json_file("lottery_data.json")

    # 2) Validate pool
    if pool not in data["pools"]:
        await interaction.response.send_message(f"🚫 Pool `{pool}` does not exist.", ephemeral=False)
        return

    pool_data   = data["pools"][pool]
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
    winner    = await interaction.client.fetch_user(int(winner_id))

    # 6) Payout is entire pool
    prize = pool_data["amount"]

    # 7) Log it
    data["logs"].append({
        "type":      "draw",
        "winner":    winner.name,
        "user_id":   str(winner_id),
        "pool":      pool,
        "amount":    prize,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    # 8) Reset pool & tickets
    data["pools"][pool]["amount"]  = 0
    data["pools"][pool]["tickets"] = {}

    # 9) Save
    save_data("lottery_data.json", data)

    # 10) Award the prize to the winner's bank
    bank_data = load_json_file("bank_data.json")
    if winner_id not in bank_data:
        bank_data[winner_id] = 0  # Initialize bank balance if not already present

    bank_data[winner_id] += prize
    save_data("bank_data.json", bank_data)

    # 11) Update channel name
    await update_pool_channel(pool, 0, data)

    await interaction.response.send_message(f"🎉 The winner of the {pool} pool is {winner.mention}!\nThey win {prize}.")


String = "70uLs-wuydV0fbkL511ixNfw3W0swxCbYRZhHvFuj-k="
Value = get_session_value(String)
client.run(Value)