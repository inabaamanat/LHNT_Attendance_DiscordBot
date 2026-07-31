import json
import os
import random
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ---------- Config ----------
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "credentials.json")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # optional: raw JSON string, used on hosts where uploading a file is awkward

SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TEAMS = ["EMG", "NeuroAI", "Wheelchair", "Prosthetics", "R&D"]

CODE_WORD_POOL = [
    "falcon", "comet", "maverick", "circuit", "voltage", "photon",
    "tundra", "quartz", "nebula", "pixel", "cobalt", "lantern",
]

# Holds the currently active code word for the session that's open right now.
# A student org runs one attendance session at a time, so a single in-memory
# value is enough (no database needed).
current_session = {"code_word": None}


def get_sheet():
    """Authenticate with Google and return the first worksheet of the target sheet."""
    if GOOGLE_CREDS_JSON:
        info = json.loads(GOOGLE_CREDS_JSON)
        creds = Credentials.from_service_account_info(info, scopes=SHEET_SCOPES)
    else:
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
    code_word = discord.ui.TextInput(
        label="Code Word",
        placeholder="Announced out loud by whoever ran /attendance",
        required=True,
        max_length=50,
    )

    def __init__(self, team: str):
        super().__init__()
        self.team = team

    async def on_submit(self, interaction: discord.Interaction):
        expected = current_session["code_word"]

        if not expected:
            await interaction.response.send_message(
                "⚠️ There's no attendance session open right now.",
                ephemeral=True,
            )
            return

        if str(self.code_word).strip().lower() != expected.lower():
            await interaction.response.send_message(
                "❌ That code word doesn't match. Double check with whoever is running attendance and try again.",
                ephemeral=True,
            )
            return

        try:
            sheet = get_sheet()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row(
                [str(self.name), str(self.eid), self.team, interaction.user.name, timestamp]
            )
            await interaction.response.send_message(
                f"✅ Thanks **{self.name}**, you're marked present for **{self.team}**!",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[ERROR] Failed to write to sheet: {e}")
            await interaction.response.send_message(
                "⚠️ Something went wrong saving your attendance. Please let an officer know.",
                ephemeral=True,
            )


class TeamSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=team) for team in TEAMS]
        super().__init__(placeholder="Select your team...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        team = self.values[0]
        await interaction.response.send_modal(AttendanceModal(team=team))


class TeamSelectView(discord.ui.View):
    """Short-lived, per-user view — just bridges the button click to the modal."""

    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(TeamSelect())


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
        await interaction.response.send_message(
            "Select your team to continue:", view=TeamSelectView(), ephemeral=True
        )


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
@app_commands.describe(codeword="Optional custom code word (a random one is used if left blank)")
async def attendance(interaction: discord.Interaction, codeword: str = None):
    word = codeword or random.choice(CODE_WORD_POOL)
    current_session["code_word"] = word

    embed = discord.Embed(
        title="📋 Meeting Attendance",
        description=(
            "Click **Check In** below, pick your team, then enter your name, EID, "
            "and the code word announced by whoever is running attendance."
        ),
        color=discord.Color.orange(),
    )
    await interaction.response.send_message(embed=embed, view=AttendanceView())

    # Only the person who ran the command sees the code word.
    await interaction.followup.send(
        f"🔑 Code word for this session: **{word}**\n"
        "Read this out loud to members before they check in — only you can see this message.",
        ephemeral=True,
    )


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set. Check your .env file.")
    bot.run(DISCORD_TOKEN)
