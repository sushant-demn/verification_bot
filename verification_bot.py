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

# Bot settings and email
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
ORG_DOMAIN = os.getenv("ORG_DOMAIN", "org.edu")

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.dm_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Temporary storage for verification codes
verification_codes = {}

# Function to send email with verification code
def send_email(recipient_email, code):
    subject = "Your Verification Code"
    body = f"Your verification code is: {code}"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    try:
        # Try sending a DM with instructions
        try:
            await member.send(
                f"👋 Welcome to the **I2IT** server!\n\n"
                f"To access the server, please verify your email ending with **@{ORG_DOMAIN}**.\n"
                f"Reply to this message with your email address:"
            )
        except discord.Forbidden:
            # Handle the case when the bot can't DM the user
            print(f"⚠️ Could not DM {member.name}. Their DMs are likely disabled.")
            # You can optionally notify the server
            general_channel = discord.utils.get(member.guild.text_channels, name="general")
            if general_channel:
                await general_channel.send(f"⚠️ {member.mention}, I couldn't send you a DM. Please enable DMs to verify your email.")

            return

        # Wait for the user to send their email
        def check_email(msg):
            return msg.author == member and isinstance(msg.channel, discord.DMChannel)

        email_msg = await bot.wait_for("message", timeout=120.0, check=check_email)
        email = email_msg.content.strip()

        # Validate the email domain
        if not email.lower().endswith(f"@{ORG_DOMAIN}"):
            await member.send("❌ That email is not valid for your organization.")
            return

        # Generate and store a random verification code
        code = str(random.randint(100000, 999999))
        verification_codes[member.id] = code

        # Send the verification code to the user's email
        send_email(email, code)
        await member.send("📧 A verification code has been sent to your email. Please reply with it.")

        # Wait for the user to reply with the verification code
        def check_code(msg):
            return msg.author == member and isinstance(msg.channel, discord.DMChannel)

        code_msg = await bot.wait_for("message", timeout=180.0, check=check_code)

        # Verify the code
        if code_msg.content.strip() == verification_codes[member.id]:
            guild = discord.utils.get(bot.guilds, name="I2IT")
            if guild:
                role = discord.utils.get(guild.roles, name="Verified")
                if role:
                    member_role = guild.get_member(member.id)
                    if member_role:
                        await member_role.add_roles(role)
                        await member.send("✅ You are now verified and have access to the server!")
                    else:
                        await member.send("⚠️ Could not find you in the server.")
                else:
                    await member.send("⚠️ Could not find the 'Verified' role. Contact an admin.")
            else:
                await member.send("❌ Could not find the server.")
        else:
            await member.send("❌ Incorrect code. Please try again by rejoining the server.")
    except discord.Forbidden:
        print(f"⚠️ Could not DM {member}.")
    except Exception as e:
        await member.send(f"❌ An error occurred: {e}")
        print(f"Error verifying {member}: {e}")

bot.run(TOKEN)
