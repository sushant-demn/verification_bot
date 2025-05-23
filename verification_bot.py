import os
import random
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot and Email Configuration
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
EMAIL_ADDRESS = os.getenv("SMTP_USER")
EMAIL_PASSWORD = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.zoho.in")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
ORG_DOMAIN = os.getenv("ORG_DOMAIN", "org.edu")

# Bot Intents
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.dm_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Temporary in-memory verification storage
verification_codes = {}

# ðŸ“§ Send an email with OTP
def send_email(recipient_email, code):
    subject = "Your Verification Code"
    body = f"Your verification code is: {code}"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
            return True
    except Exception as e:
        print(f"âŒ Email sending failed: {e}")
        return False

@bot.event
async def on_ready():
    print(f"âœ… Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    try:
        # Step 1: DM the user asking for their email
        try:
            await member.send(
                f"ðŸ‘‹ Welcome to the **I2IT** server!\n\n"
                f"To access the server, please verify your email ending with **@{ORG_DOMAIN}**.\n"
                f"Reply to this message with your email address:"
            )
        except discord.Forbidden:
            print(f"âš ï¸ Could not DM {member.name}.")
            general_channel = discord.utils.get(member.guild.text_channels, name="general")
            if general_channel:
                await general_channel.send(f"{member.mention}, please enable DMs to verify your email.")
            return

        # Step 2: Wait for user's email
        def check_email(msg):
            return msg.author == member and isinstance(msg.channel, discord.DMChannel)

        email_msg = await bot.wait_for("message", timeout=120.0, check=check_email)
        email = email_msg.content.strip()

        if not email.lower().endswith(f"@{ORG_DOMAIN}"):
            await member.send("âŒ That email is not valid for your organization.")
            return

        # Step 3: Generate and send OTP
        code = str(random.randint(100000, 999999))
        verification_codes[member.id] = code
        sent = send_email(email, code)

        if not sent:
            await member.send("âŒ Failed to send verification email. Please try again later.")
            return

        await member.send("ðŸ“§ A verification code has been sent to your email. Please reply with it.")

        # Step 4: Wait for OTP
        def check_code(msg):
            return msg.author == member and isinstance(msg.channel, discord.DMChannel)

        code_msg = await bot.wait_for("message", timeout=180.0, check=check_code)

        if code_msg.content.strip() == verification_codes.get(member.id):
            guild = discord.utils.get(bot.guilds, name="I2IT")
            if guild:
                role = discord.utils.get(guild.roles, name="Verified")
                if role:
                    await member.add_roles(role)
                    await member.send("âœ… You are now verified and have access to the server!")
                else:
                    await member.send("âš ï¸ 'Verified' role not found. Contact an admin.")
            else:
                await member.send("âŒ Server not found.")
        else:
            await member.send("âŒ Incorrect code. Please try again.")

    except discord.Forbidden:
        print(f"âš ï¸ Could not DM {member}.")
    except Exception as e:
        await member.send(f"âŒ An error occurred: {e}")
        print(f"Error verifying {member}: {e}")

bot.run(TOKEN)
