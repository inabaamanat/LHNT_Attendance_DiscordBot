import os
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ---------- Config ----------
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "credentials.json")

SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheet():
    """Authenticate with Google and return the first worksheet of the target sheet."""
    creds = Credentials.from_service_account_file(GOOGLE_CREDS_PATH, scopes=SHEET_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


# ---------- Discord setup ----------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class AttendanceModal(discord.ui.Modal, title="Meeting Attendance"):
    name = discord.ui.TextInput(
        label="Full Name",
        placeholder="e.g. John Doe",
        required=True,
        max_length=100,
    )
    eid = discord.ui.TextInput(
        label="UT EID",
        placeholder="e.g. jd12345",
        required=True,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            sheet = get_sheet()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row(
                [str(self.name), str(self.eid), interaction.user.name, timestamp]
            )
            await interaction.response.send_message(
                f"✅ Thanks **{self.name}**, you're marked present!",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[ERROR] Failed to write to sheet: {e}")
            await interaction.response.send_message(
                "⚠️ Something went wrong saving your attendance. Please let an officer know.",
                ephemeral=True,
            )


class AttendanceView(discord.ui.View):
    """Persistent view so the button keeps working even after the bot restarts."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Check In",
        style=discord.ButtonStyle.green,
        custom_id="attendance_checkin_button",
    )
    async def check_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AttendanceModal())


@bot.event
async def on_ready():
    bot.add_view(AttendanceView())  # re-register persistent view on startup
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"[ERROR] Command sync failed: {e}")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.tree.command(name="attendance", description="Start attendance check-in for this meeting")
async def attendance(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Meeting Attendance",
        description="Click **Check In** below and enter your name and EID.",
        color=discord.Color.orange(),
    )
    await interaction.response.send_message(embed=embed, view=AttendanceView())


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set. Check your .env file.")
    bot.run(DISCORD_TOKEN)
