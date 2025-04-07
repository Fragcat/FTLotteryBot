import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone
import discord
import random
from discord.ext import commands
from discord import app_commands
from discord.app_commands import MissingPermissions
from discord import Interaction
from typing import Literal
from LotteryImports import load_data, save_data, update_pool_channel, DISCORD_TOKEN, SERVER_ID
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
data = load_data()


@client.event
async def on_ready():
    await tree.sync()
    print(f"Lottery Client logged in as {client.user}")

@tree.command(name="lottery_donate", description="Donate currency to a lottery pool")
@app_commands.describe(amount="The amount to donate.")
@app_commands.describe(pool="Choose either the short or long lottery pool to join.")
async def donate(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    user = interaction.user

    if amount <= 0:
        await interaction.response.send_message("🚫 Amount must be greater than zero.", ephemeral=false)
        return

    # Add to the correct pool
    data["pools"][pool]["amount"] += amount
    await update_pool_channel(pool, data["pools"][pool]["amount"], data)

    # Log it
    log_entry = {
        "type": "donation",
        "user": user.name,
        "amount": amount,
        "pool": pool,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    data["logs"].append(log_entry)
    save_data(data)

    # Update channel announcement
    update_channel_id = data.get("update_channel_id")
    if update_channel_id:
        channel = interaction.client.get_channel(update_channel_id)
        if channel:
            embed = discord.Embed(
                title="💸 New Lottery Donation!",
                description=f"**{user.name}** donated **{amount}** currency to the **{pool}** pool.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Total in {pool} pool: {data['pools'][pool]}")
            await channel.send(embed=embed)

    await interaction.response.send_message(f"✅ Thanks! You donated {amount} to the {pool} lottery.")
    await update_pool_channel(pool, data["pools"][pool]["amount"], data)


@tree.command(name="lottery_setupdatechannel", description="Set the channel for donation updates")
async def set_update_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    user = interaction.user

    # Allow if user is "fragcat."
    if user.name != "fragcat." and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=false)
        return

    data["update_channel_id"] = channel.id
    save_data(data)
    await interaction.response.send_message(f"✅ Updates will now be posted in {channel.mention}")


async def update_pool_channel(pool: str, amount: int, data: dict):
    if "update_channels" not in data or pool not in data["update_channels"]:
        return

    channel_id = data["update_channels"][pool]
    formatted_amount = f"{amount:,}"

    guild = client.get_guild(SERVER_ID)  # Use your actual server ID here
    if not guild:
        print("[DEBUG] Guild not found.")
        return

    channel = discord.utils.get(guild.channels, id=channel_id)
    if not channel:
        print(f"[DEBUG] Channel ID {channel_id} not found.")
        return

    new_name = f"💰{pool}-pool: {formatted_amount}"
    print(f"Updating channel ID {channel_id} ({channel.name}) to: 💰{pool}-pool: {formatted_amount}")


    try:
        await channel.edit(name=new_name)
    except discord.Forbidden:
        print(f"[WARNING] Missing permissions to rename channel {channel_id}")
    except discord.HTTPException as e:
        print(f"[ERROR] Failed to rename channel: {e}")


import discord
from discord import app_commands
from typing import Literal

import discord
from discord import app_commands
from typing import Literal


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
    # 1) Load your data
    data = load_data()

    # 2) Ensure the update_channels dict exists
    data.setdefault("update_channels", {})

    # 3) Save the channel ID
    data["update_channels"][pool] = channel.id
    save_data(data)

    # 4) Confirm to the user
    await interaction.response.send_message(
        f"✅ Update channel for **{pool}** pool set to {channel.mention}"
    )




# Maximum tickets per user per pool (Ticket cap)
MAX_TICKETS = 100

# Simulated wallet balance (we'll change this later to use the actual game wallet system)
USER_WALLET = 1000  # Example: Player has 1000 currency for testing

@tree.command(name="lottery_tickets", description="Buy lottery tickets for a pool.")
@app_commands.describe(pool="Choose a lottery pool", amount="Number of tickets to buy")
async def buy_tickets(interaction: discord.Interaction, pool: Literal["short", "long"], amount: int):
    user = interaction.user

    # Load the current lottery data
    data = load_data()

    if amount <= 0:
        await interaction.response.send_message("🚫 Amount must be greater than zero.", ephemeral=false)
        return

    # Get the price per ticket
    price_per_ticket = data["ticket_price"].get(pool, 10)  # Default to 10 if not found
    total_cost = amount * price_per_ticket

    # Check if the user has enough currency (for this example, assume 1000 currency is available)
    user_currency = 1000  # This would be retrieved from the user's actual balance
    if user_currency < total_cost:
        await interaction.response.send_message(f"🚫 You don't have enough currency. You need {total_cost} but only have {user_currency}.", ephemeral=false)
        return

    # Update pool amount and user tickets
    data["pools"][pool]["amount"] += total_cost
    user_tickets = data["pools"][pool]["tickets"].get(str(user.id), 0)
    data["pools"][pool]["tickets"][str(user.id)] = user_tickets + amount

    # Save updated data to the JSON file
    save_data(data)

    # Optionally, update the pool channel amount
    await update_pool_channel(pool, data["pools"][pool]["amount"], data)


    await interaction.response.send_message(f"✅ You bought **{amount}** ticket(s) for the **{pool}** pool. Total cost: {total_cost} currency.")


@tree.command(name="join", description="Join a lottery pool.")
@app_commands.describe(pool="Choose either the short or long lottery pool to join.")
@app_commands.choices(pool=[
    app_commands.Choice(name="short", value="short"),
    app_commands.Choice(name="long", value="long")
])
async def lottery_join(interaction: discord.Interaction, pool: app_commands.Choice[str]):
    data = load_data()
    pool_key = pool.value  # "short" or "long"
    pool_data = data["pools"][pool_key]

    user_id = str(interaction.user.id)

    if user_id in pool_data["tickets"]:
        cnt = pool_data["tickets"][user_id]
        await interaction.response.send_message(
            f"🚫 You’re already in the {pool_key} pool with {cnt} ticket(s).", ephemeral=false
        )
        return

    # Give them 1 ticket
    pool_data["tickets"][user_id] = 1
    save_data(data)

    await interaction.response.send_message(
        f"✅ You’ve joined the **{pool_key}** pool with **1** ticket! Good luck!"
    )



@tree.command(name="lottery_draw", description="Draw a winner from a lottery pool.")
@app_commands.describe(pool="Which pool to draw from")
async def draw_winner(interaction: discord.Interaction, pool: Literal["short", "long"]):
    # 1) Load
    data = load_data()

    # 2) Validate pool
    if pool not in data["pools"]:
        await interaction.response.send_message(f"🚫 Pool `{pool}` does not exist.", ephemeral=false)
        return

    pool_data   = data["pools"][pool]
    pool_tickets = pool_data.get("tickets", {})

    # 3) No entries?
    if not pool_tickets:
        await interaction.response.send_message(f"🚫 No entries in the {pool} pool.", ephemeral=false)
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
    save_data(data)

    # 10) Update channel name
    await update_pool_channel(pool, data["pools"][pool]["amount"], data)

    # 11) Announce in the update channel (if set)
    #    Here we assume you have data["update_channels"] = {"short": id, "long": id}
    update_channels = data.get("update_channels", {})
    ch_id = update_channels.get(pool)
    if ch_id:
        ch = interaction.client.get_channel(ch_id)
        if ch:
            embed = discord.Embed(
                title=f"🎉 {pool.capitalize()} Lottery Winner!",
                description=f"**{winner.mention}** won **{prize:,}** coins!",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"Drawn by {interaction.user.name}")
            await ch.send(embed=embed)

    # 12) Reply to the command
    await interaction.response.send_message(
        f"🎉 Winner drawn for **{pool}** pool: {winner.mention} won **{prize:,}** coins!"
    )



client.run(DISCORD_TOKEN)