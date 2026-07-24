# LHNT_Attendance_DiscordBot


A Discord bot for tracking attendance in a server. It adds a slash command, `/attendance`, that posts a check-in button for members to use. When someone clicks the button and submits their name and EID, the bot records the attendance in a Google Sheet.

## Features

- `/attendance` slash command
- Interactive check-in button
- Collects a member’s name and EID
- Stores attendance data in Google Sheets
- Runs in a Discord server once the bot is online

## How it connects to Google Sheets

The bot uses a Google service account with a `credentials.json` file to access a Google Sheet. The sheet must be shared with the service account email, and the bot uses the sheet ID from the environment settings to write new attendance entries.

## How it starts in Discord

After the bot is running, users can type `/attendance` in any channel the bot can see. The bot will send an attendance message with a button, and members can submit their check-in information from there.

## Setup notes

- Create a `.env` file with your Discord token and Google Sheet ID.
- Place your `credentials.json` file locally in the project folder so the bot can access Google Sheets.
- `credentials.json` is not included in the repository because it contains sensitive Google service account information and should stay private.

## Run locally

```bash
python bot.py
```


