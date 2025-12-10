# ===============================
#   STYLISH TELEGRAM TAG BOT - FINAL FULL EDITION (FIXED)
# ===============================

import asyncio
import random
import sqlite3
import datetime
import time
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors import ChatAdminRequiredError, UserNotParticipantError

# -----------------------------
# CONFIG
# -----------------------------
# NOTE: Replace these with your actual values. Use environment variables 
# for production for better security (Recommended).
API_ID = 38066200
API_HASH = "8a2864ab9a3b02341cbe31d0228a6725"
BOT_TOKEN = "8434016246:AAHxYSoUXd6l5A5yFrCxgOVJxBy19nIJgP0"

OWNER_ID = 7384495179       # <-- Your ID (A.K.A. The Owner)

# Multiple Admins Allowed Here
BOT_ADMINS = {
    111111111,   # Admin 1
    222222222,   # Admin 2
    333333333,   # Admin 3
}  # Add unlimited admins here

SUPPORT_CHAT = "Rajnetworkchat"
UPDATES_CHANNEL = "Rajnetworksbot"
START_PHOTO_URL = "https://i.imgur.com/xVwIQfB.jpeg"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot client
bot = TelegramClient("tagbot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

tagging = {}
users_db = set()  # PM broadcast database

# -----------------------------
# DATABASE SETUP (GROUP & LOGS DB)
# -----------------------------
db = sqlite3.connect("groups.db", check_same_thread=False)
cursor = db.cursor()

# Group DB
cursor.execute("""
CREATE TABLE IF NOT EXISTS groups (
    chat_id INTEGER PRIMARY KEY
)
""")

# Welcome Log DB (For 24-hour welcome cooldown)
cursor.execute("""
CREATE TABLE IF NOT EXISTS welcome_log (
    chat_id INTEGER,
    user_id INTEGER,
    last_welcome INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")

# Couple System DB (Ensuring both tables are created)
cursor.execute("""
CREATE TABLE IF NOT EXISTS temp_couple (
    chat_id INTEGER PRIMARY KEY,
    user1 INTEGER,
    user2 INTEGER,
    set_time INTEGER
)
""")

# --- FIX: Permanent Couple table schema added correctly on startup ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS perm_couple (
    chat_id INTEGER PRIMARY KEY,
    user1 INTEGER,
    user2 INTEGER
)
""")

# Greet Log for Couple System (24-hour couple welcome cooldown)
cursor.execute("""
CREATE TABLE IF NOT EXISTS greet_log (
    chat_id INTEGER,
    user_id INTEGER,
    last_greet INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")

db.commit()

# Fix for old welcome_log database (adds missing column if needed)
try:
    cursor.execute("SELECT last_welcome FROM welcome_log LIMIT 1")
except sqlite3.OperationalError:
    try:
        cursor.execute("ALTER TABLE welcome_log ADD COLUMN last_welcome INTEGER DEFAULT 0")
        db.commit()
    except sqlite3.OperationalError:
        pass # Column already exists or another issue

# --- Database Helpers ---
def add_group(chat_id):
    cursor.execute("INSERT OR IGNORE INTO groups (chat_id) VALUES (?)", (chat_id,))
    db.commit()

def remove_group(chat_id):
    cursor.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))
    db.commit()

def set_temp_couple(chat, u1, u2):
    t = int(time.time())
    cursor.execute("INSERT OR REPLACE INTO temp_couple VALUES (?, ?, ?, ?)", (chat, u1, u2, t))
    db.commit()

def delete_temp_couple(chat):
    cursor.execute("DELETE FROM temp_couple WHERE chat_id=?", (chat,))
    db.commit()

def get_temp_couple(chat):
    cursor.execute("SELECT user1, user2, set_time FROM temp_couple WHERE chat_id=?", (chat,))
    return cursor.fetchone()

def set_perm_couple(chat, u1, u2):
    cursor.execute("INSERT OR REPLACE INTO perm_couple VALUES (?, ?, ?)", (chat, u1, u2))
    db.commit()

def delete_perm_couple(chat):
    cursor.execute("DELETE FROM perm_couple WHERE chat_id=?", (chat,))
    db.commit()

def get_perm_couple(chat):
    cursor.execute("SELECT user1, user2 FROM perm_couple WHERE chat_id=?", (chat,))
    return cursor.fetchone()

# Welcome Cooldown Helpers (Used by premium_welcome)
def was_welcomed_recently(chat_id, user_id):
    cursor.execute("SELECT last_welcome FROM welcome_log WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    row = cursor.fetchone()
    if not row:
        return False
    last = row[0] or 0
    now = int(datetime.datetime.now().timestamp())
    return (now - last) < 86400

def update_welcome_time(chat_id, user_id):
    now = int(datetime.datetime.now().timestamp())
    cursor.execute(
        "INSERT OR REPLACE INTO welcome_log (chat_id, user_id, last_welcome) VALUES (?, ?, ?)",
        (chat_id, user_id, now)
    )
    db.commit()
    
# Greet Cooldown Helper (Used by couple_welcome)
def has_greeted(chat_id, user_id):
    cursor.execute("SELECT last_greet FROM greet_log WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    row = cursor.fetchone()
    if not row:
        return False
    last = row[0] or 0
    return (time.time() - last) < 86400  # 24 hours

def update_greet(chat_id, user_id):
    cursor.execute("INSERT OR REPLACE INTO greet_log(chat_id, user_id, last_greet) VALUES(?,?,?)",
                   (chat_id, user_id, int(time.time())))
    db.commit()

# -----------------------------
# STYLISH FONT SYSTEM
# -----------------------------
symbols = ["✦", "★", "✧", "❖", "✨", "⚡", "✪", "♛", "♜", "☘️", "🌸", "💮", "⭐", "🌺", "🌟"]
emojis = ["⚡", "✨", "🌸", "🌺", "💫", "🔥", "👑", "😈", "🌙", "🌼", "💥", "🌻", "🎀", "🐥"]

def stylish(text):
    if not text:
        return "User"
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    fancy = "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝓧𝙔𝚉"
    # Added a fix for Z and X not being in the original fancy string
    # Using transliteration might fail if character sets don't match exactly.
    # The original implementation seems to use a custom font that may not map all letters perfectly.
    # We will stick to the provided mapping for maximum compatibility with the original look.
    
    # Simple transliteration based on the provided strings
    mapping = str.maketrans(normal, fancy)
    return text.translate(mapping)


def format_user(member):
    # Fixed: Safely get first_name and handle None
    safe_name = stylish((member.first_name or "User").replace("<", "").replace(">", ""))
    emo = random.choice(emojis)
    sym = random.choice(symbols)
    return f"<a href='tg://user?id={member.id}'>{sym} {safe_name} {emo}</a>"

# SAFE SEND MESSAGE (Used by welcome system)
async def safe_send(event, text):
    try:
        await event.reply(text, parse_mode="html")
    except Exception as error:
        try:
            # Fallback attempt after a small pause
            await asyncio.sleep(0.5)
            await event.reply(text, parse_mode="html")
        except:
            logger.error(f"Failed to send welcome message: {error}")
            pass

# -----------------------------
# AUTO SAVE USERS FOR PM BROADCAST
# -----------------------------
@bot.on(events.NewMessage)
async def save_users(event):
    if event.is_private:
        # Note: For persistence across restarts, this should be saved to DB.
        users_db.add(event.sender_id)

    if event.is_group:
        add_group(event.chat_id)   # auto group save

# ============================================================
# MULTI ADMIN + OWNER FULL ACCESS SYSTEM
# ============================================================

def is_owner(user_id):
    return user_id == OWNER_ID

def is_bot_admin(user_id):
    return user_id == OWNER_ID or user_id in BOT_ADMINS
    
# =============== ADD ADMIN ===============
@bot.on(events.NewMessage(pattern=r"^/addadmin"))
async def addadmin(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Only Owner can add admins.")

    # reply-based
    if event.is_reply:
        target = await event.get_reply_message()
        if not target:
            return await event.reply("❌ Reply to a user to add them as admin.")
        uid = target.sender_id
    else:
        try:
            # Handle username/ID input
            parts = event.raw_text.split(" ", 1)
            if len(parts) < 2:
                return await event.reply("Usage: /addadmin @user OR reply to user")
            username = parts[1]
            ent = await bot.get_entity(username)
            uid = ent.id
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            return await event.reply("❌ Invalid user. Usage: /addadmin @user OR reply to user")

    if uid == OWNER_ID:
        return await event.reply("❌ You cannot add the owner as admin to the admin list.")

    BOT_ADMINS.add(uid)

    await event.reply(
        f"👑 <b>Added as Bot Admin:</b>\n<a href='tg://user?id={uid}'>User</a>",
        parse_mode="html"
    )

# =============== REMOVE ADMIN ===============
@bot.on(events.NewMessage(pattern=r"^/deladmin"))
async def deladmin(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Only Owner can remove admins.")

    if event.is_reply:
        target = await event.get_reply_message()
        if not target:
             return await event.reply("❌ Reply to a user to remove them from admin.")
        uid = target.sender_id
    else:
        try:
            parts = event.raw_text.split(" ", 1)
            if len(parts) < 2:
                return await event.reply("Usage: /deladmin @user OR reply to user")
            username = parts[1]
            ent = await bot.get_entity(username)
            uid = ent.id
        except Exception as e:
            logger.error(f"Error removing admin: {e}")
            return await event.reply("❌ Invalid user. Usage: /deladmin @user OR reply to user")

    if uid == OWNER_ID:
        return await event.reply("❌ You cannot remove the owner from the admin list.")

    BOT_ADMINS.discard(uid)

    await event.reply(
        f"❌ <b>Removed from Bot Admins:</b>\n<a href='tg://user?id={uid}'>User</a>",
        parse_mode="html"
    )
    
@bot.on(events.NewMessage(pattern=r"^/adminlist"))
async def adminlist(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Only Owner can check admin list.")

    if not BOT_ADMINS:
        return await event.reply("😶 No admins added yet.")

    txt = "👑 <b>Bot Global Admins</b>\n\n"

    for aid in BOT_ADMINS:
        try:
            user = await bot.get_entity(aid)
            name = user.first_name if user.first_name else f"User {aid}"
        except Exception as e:
            logger.error(f"Error getting admin info: {e}")
            name = f"Deleted User {aid}"

        txt += f"• <a href='tg://user?id={aid}'>{name}</a> (<code>{aid}</code>)\n"

    await event.reply(txt, parse_mode="html")
    
# ============================================================
# /group_stats — Owner Only | Shows All Group Stats
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/group_stats"))
async def group_stats(event):
    # Only OWNER can use this
    if not is_owner(event.sender_id):
        return await event.reply("❌ This command is only for the Bot Owner.")

    cursor.execute("SELECT chat_id FROM groups")
    rows = cursor.fetchall()

    if not rows:
        return await event.reply("😶 Bot is not added in any group yet!")

    total = len(rows)
    active = 0
    dead = 0

    msg_list = ""

    # Check each group
    for (chat_id,) in rows:
        try:
            chat = await bot.get_entity(chat_id)
            title = chat.title or "Unknown Group"
            msg_list += f"🔹 <b>{title}</b> — <code>{chat_id}</code>\n"
            active += 1
        except Exception as e: # Catching all exceptions like Chat not found, Banned, etc.
            logger.error(f"Error checking group {chat_id}: {e}")
            dead += 1
            msg_list += f"🔸 <b>Removed / Dead</b> — <code>{chat_id}</code>\n"

    final_msg = f"""
📊 <b><i>BOT GROUP STATISTICS</i></b> 📊

👥 <b>Total Groups:</b> {total}
✅ <b>Active:</b> {active}
❌ <b>Dead / Removed:</b> {dead}

———————————————
<b><i>GROUP LIST:</i></b>
———————————————

{msg_list}
""".strip()

    await event.reply(final_msg, parse_mode="html")
    
# ============================================================
# /fix — QUICK SELF REPAIR SYSTEM (OWNER ONLY)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/fix"))
async def quick_fix(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Only Owner can use /fix.")

    report = "🛠 <b>QUICK FIX REPORT</b>\n\n"
    
    # 1) Database check
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS groups(chat_id INTEGER PRIMARY KEY)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS welcome_log(
                chat_id INTEGER,
                user_id INTEGER,
                last_welcome INTEGER,
                PRIMARY KEY(chat_id, user_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_couple (
                chat_id INTEGER PRIMARY KEY,
                user1 INTEGER,
                user2 INTEGER,
                set_time INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perm_couple (
                chat_id INTEGER PRIMARY KEY,
                user1 INTEGER,
                user2 INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS greet_log (
                chat_id INTEGER,
                user_id INTEGER,
                last_greet INTEGER,
                PRIMARY KEY(chat_id, user_id)
            )
        """)
        db.commit()
        report += "✔ Database tables OK\n"
    except Exception as e:
        report += f"❌ DB check failed: <code>{e}</code>\n"

    # 2) Remove dead groups
    try:
        cursor.execute("SELECT chat_id FROM groups")
        rows = cursor.fetchall()
        removed = 0

        for (gid,) in rows:
            try:
                # Check if the group is still accessible
                await bot.get_entity(gid)
            except Exception: # If bot can't access, delete it
                cursor.execute("DELETE FROM groups WHERE chat_id=?", (gid,))
                removed += 1

        db.commit()
        report += f"✔ Removed {removed} dead groups\n"
    except Exception as e:
        report += f"❌ Dead group cleanup failed: <code>{e}</code>\n"

    # 3) Check session
    try:
        me = await bot.get_me()
        report += f"✔ Session OK: @{me.username}\n"
    except Exception as e:
        report += f"❌ Session error: <code>{e}</code>\n"

    # Final message
    report += "\n✨ <b>Quick Fix Completed!</b>\n"

    await event.reply(report, parse_mode="html")
    
# ============================================================
# /refresh — INSTANT MINI-RELOAD SYSTEM (OWNER ONLY)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/refresh"))
async def refresh_cmd(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Only Owner can use /refresh.")

    msg = await event.reply("🔄 <b>Refreshing bot…</b>", parse_mode="html")

    result = "✨ <b>REFRESH REPORT</b>\n\n"

    # 1) Session refresh
    try:
        me = await bot.get_me()
        result += f"✔ Session OK: @{me.username}\n"
    except Exception as e:
        result += f"❌ Session problem: <code>{e}</code>\n"

    # 2) Clear tagging status
    tagging.clear()
    result += "✔ Tagging status cleared\n"

    # Final message
    await msg.edit(result, parse_mode="html")
    
# -----------------------------
# AUTO DETECT BOT ADD / REMOVE
# -----------------------------
@bot.on(events.ChatAction)
async def handler(event):
    me = await bot.get_me()

    if event.user_added and event.added_by:
        if event.added_by.id == me.id:
            return
        if me.id in [user.id for user in event.users]:
            add_group(event.chat_id)
            await event.reply("✨ Bot added in group! Broadcast enabled.")

    if event.user_kicked and event.kicked_by:
        if me.id in [user.id for user in event.users]:
            remove_group(event.chat_id)

# -----------------------------
# CHECK ADMIN (FIXED with Failsafe)
# -----------------------------
async def is_admin(chat_id, user_id):
    try:
        # Check if the user is a group admin
        async for m in bot.iter_participants(chat_id, filter=ChannelParticipantsAdmins):
            if m.id == user_id:
                return True
        # Also check if the user is a global bot admin or owner
        return is_bot_admin(user_id)
    except (ChatAdminRequiredError, UserNotParticipantError):
        # Failsafe: If bot doesn't have permission to list admins,
        # only check if they are a global bot admin/owner.
        return is_bot_admin(user_id)
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return is_bot_admin(user_id)

# ============================================================
# ADMIN PANEL (Only Owner and Group Admins can use)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/panel"))
async def admin_panel(event):
    # Check if the sender is a Bot Admin OR a Group Admin
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
         
    if not is_bot_admin(event.sender_id) and not await is_admin(event.chat_id, event.sender_id):
        return await event.reply("❌ Only Admin/Owner can open admin panel.")

    buttons = [
        [Button.inline("⚡ Start UTAG", data=b"start_utag")],
        [Button.inline("👑 Admin Tag", data=b"admin_tag")],
        [Button.inline("📢 Broadcast (Owner/Admin)", data=b"broadcast")],
        [Button.inline("🛑 Stop Tagging", data=b"stop_tag")],
        [Button.inline("❌ Close", data=b"close_panel")],
    ]

    await event.reply("🛠 <b>Admin Control Panel</b>", buttons=buttons, parse_mode="html")

# BUTTON CALLBACKS
@bot.on(events.CallbackQuery)
async def callback(event):
    data = event.data.decode()
    chat = event.chat_id
    sender = event.sender_id
    
    if data == "close_panel":
        await event.delete()
        return

    if data in ("start_utag", "admin_tag", "broadcast", "stop_tag"):
        # Check if the sender is a Bot Admin OR a Group Admin
        if not is_bot_admin(sender) and not await is_admin(chat, sender):
            return await event.answer("❌ Only Admin/Owner can use this button.", alert=True)

    if data == "start_utag":
        await event.edit("Use: `/utag message` to start UTAG")
        return

    if data == "admin_tag":
        try:
            admins = [m async for m in bot.iter_participants(event.chat_id, filter=ChannelParticipantsAdmins)]
            mentions = [format_user(a) for a in admins]
            await event.edit("👑 <b>Admins Tag:</b>\n\n" + " , ".join(mentions), parse_mode="html")
        except Exception as e:
            logger.error(f"Error tagging admins: {e}")
            await event.edit("❌ Error tagging admins. Bot may need admin rights.")
        return

    if data == "broadcast":
        # Clarifying usage for group broadcast
        await event.edit("Use: `/Broadcast message` for group text broadcast\nUse: `/Broadcast_image` for image broadcast")
        return

    if data == "stop_tag":
        tagging[event.chat_id] = False
        await event.edit("🛑 Tagging Stopped.")
        return

# ============================================================
# /Broadcast — Group Text Broadcast (OWNER / BOT ADMIN ONLY)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/Broadcast"))
async def broadcast(event):
    # FIXED: Allow Bot Admins and Owner to use this
    if not is_bot_admin(event.sender_id):
        return await event.reply("❌ Only Owner and Global Bot Admins can use Broadcast command.")

    parts = event.raw_text.split(" ", 1)
    if len(parts) < 2:
        return await event.reply("Usage:\n`/Broadcast your message`", parse_mode="md")

    msg = parts[1]

    # Auto premium formatting
    formatted_msg = f"""
✨ <b><i>GLOBAL BROADCAST MESSAGE</i></b> ✨

{msg}

<b><i>— Sent by Admin Team</i></b> 👑
"""

    cursor.execute("SELECT chat_id FROM groups")
    groups = cursor.fetchall()

    sent = 0

    for (chat_id,) in groups:
        try:
            await bot.send_message(chat_id, formatted_msg, parse_mode="html")
            sent += 1
            await asyncio.sleep(0.25)
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")
            pass

    await event.reply(
        f"📢 <b>Broadcast delivered to {sent} groups successfully!</b>",
        parse_mode="html",
    )

# ============================================================
# /Broadcast_image START (OWNER / BOT ADMIN ONLY)
# ============================================================
waiting_for_broadcast_image = {}  # temporary storage

@bot.on(events.NewMessage(pattern=r"^/Broadcast_image"))
async def broadcast_image_start(event):
    # FIXED: Allow Bot Admins and Owner to use this
    if not is_bot_admin(event.sender_id):
        return await event.reply("❌ Only Owner and Global Bot Admins can send image broadcast.")

    waiting_for_broadcast_image[event.sender_id] = True

    await event.reply(
        "🖼️ <b>Send the broadcast image with caption.</b>\n"
        "<i>Caption will be delivered to all groups.</i>",
        parse_mode="html",
    )

# ============================================================
# Broadcast_image PROCESS (OWNER / BOT ADMIN ONLY)
# ============================================================
@bot.on(events.NewMessage(func=lambda e: e.sender_id in waiting_for_broadcast_image))
async def process_broadcast_image(event):
    sender = event.sender_id

    # Check if the user is still a Bot Admin (failsafe)
    if not is_bot_admin(sender):
        del waiting_for_broadcast_image[sender]
        return await event.reply("❌ Your broadcast session has expired or you are no longer an admin.")

    # Only accept photo
    if not event.photo:
        return await event.reply("❌ Please send a *photo* with caption.", parse_mode="md")

    caption = event.text or ""

    # Premium Caption Format
    final_caption = f"""
📣 <b><i>BROADCAST</i></b> 📣

{caption}

— <i>Admin Team</i> ⚡
""".strip()

    # Fetch groups from database
    cursor.execute("SELECT chat_id FROM groups")
    groups = cursor.fetchall()

    success = 0
    failed = 0
    total = len(groups)

    # Broadcast loop
    for (chat_id,) in groups:
        try:
            await bot.send_file(
                chat_id,
                event.photo,
                caption=final_caption,
                parse_mode="html"
            )
            success += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")
            failed += 1

    # Clean memory
    if sender in waiting_for_broadcast_image:
        del waiting_for_broadcast_image[sender]

    # Final Summary Message
    await event.reply(
        f"""
🎉 <b>BROADCAST COMPLETED</b> 🎉

👥 <b>Total Groups:</b> {total}
✅ <b>Successful:</b> {success}
❌ <b>Failed:</b> {failed}

<i>Broadcast delivered successfully!</i> 🚀
        """,
        parse_mode="html"
    )

# ============================================================
# PRIVATE BROADCAST (OWNER ONLY)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/pm"))
async def pmbc(event):
    if not is_owner(event.sender_id):
        return await event.reply("❌ Only Owner can PM Broadcast.")

    try:
        msg = event.raw_text.split(" ", 1)[1]
    except IndexError:
        return await event.reply("Usage: /pm message")

    count = 0
    for user in list(users_db): # Iterate over a copy in case of modification
        try:
            await bot.send_message(user, msg)
            count += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Failed to PM {user}: {e}")
            pass

    await event.reply(f"📩 PM Broadcast delivered to **{count} Users!**")

# ============================================================
# UTAG (ADMINS ONLY)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/utag"))
async def utag(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
         
    chat = event.chat_id
    sender = event.sender_id

    # Check if sender is Group Admin OR Bot Admin
    if not is_bot_admin(sender) and not await is_admin(chat, sender):
        return await event.reply("❌ Only Admin can use UTAG.")

    args = event.raw_text.split(maxsplit=1)
    custom = args[1] if len(args) > 1 else "✨ Tagging all members for attention!"

    tagging[chat] = True
    await event.reply("🚀 Stylish Tagging Started! Use /cancel to stop.")

    # Get all non-bot members
    try:
        members = [m async for m in bot.iter_participants(chat) if not m.bot]
    except Exception as e:
        logger.error(f"Error getting members: {e}")
        return await event.reply("❌ Cannot get member list. Bot needs admin rights to list members in this group.")

    BATCH = 7
    batch = []

    for user in members:
        if not tagging.get(chat, False):
            return await event.reply("🛑 Tagging Cancelled.")

        batch.append(format_user(user))

        if len(batch) == BATCH:
            try:
                await event.reply(f"{custom}\n\n" + " , ".join(batch), parse_mode="html")
            except Exception as e:
                logger.error(f"Error sending batch: {e}")
                await event.reply("❌ Error while sending tag batch. Pausing...")
                await asyncio.sleep(5)

            batch = []
            await asyncio.sleep(1.5) # Increased delay for safety

    if batch:
        await event.reply(f"{custom}\n\n" + " , ".join(batch), parse_mode="html")

    tagging[chat] = False
    await event.reply("✅ Stylish Tagging Completed!")

# ============================================================
# ATAG — Anyone Can Use (Tag Admins)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/(atag|admin)"))
async def atag(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
         
    try:
        admins = [m async for m in bot.iter_participants(event.chat_id, filter=ChannelParticipantsAdmins)]
    except Exception as e:
        logger.error(f"Error getting admins: {e}")
        return await event.reply("❌ Bot needs admin rights to tag other admins.")
        
    mentions = [format_user(a) for a in admins]
    await event.reply("👑 <b>Admins Tag:</b>\n\n" + " , ".join(mentions), parse_mode="html")

# ============================================================
# STOP TAGGING
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/cancel"))
async def cancel(event):
    tagging[event.chat_id] = False
    await event.reply("🛑 Tagging Stopped.")

# ============================================================
#     ⚡ FULL PREMIUM WELCOME SYSTEM (OWNER + ADMIN + USERS)
# ============================================================
# MAIN WELCOME SYSTEM LISTENER
@bot.on(events.NewMessage)
async def premium_welcome(event):
    if not event.is_group:
        return

    sender = event.sender_id
    chat = event.chat_id
    
    # Ensure event has a sender for checks
    if not sender:
        return

    # Skip bot messages
    me = await bot.get_me()
    if sender == me.id:
        return

    # Skip commands (avoid spam)
    if event.raw_text and event.raw_text.startswith("/"):
        return

    # If welcomed within 24 hours → skip
    if was_welcomed_recently(chat, sender):
        return

    # Mark welcome time
    update_welcome_time(chat, sender)
    
    # ------------------------------------------------------------
    # 👑 OWNER SPECIAL BOSS WELCOME
    # ------------------------------------------------------------
    if is_owner(sender):
        msg = f"""
✨<b><i>THE KING HAS ARRIVED</i></b> 👑

🔥 <b><i>Welcome Back, My Boss!</i></b>  
💥 <i>Your presence boosts power in the whole group!</i>  

🔱 <a href='tg://user?id={sender}'><b><i>⚡ THE REAL OWNER ⚡</i></b></a>

🌟 <i>The atmosphere just changed because the KING entered!</i>
"""
        return await safe_send(event, msg)

    # ------------------------------------------------------------
    # 🛡 ADMIN ROYAL VIP ENTRY
    # ------------------------------------------------------------
    # Check if sender is a Group Admin or a Bot Admin
    if await is_admin(chat, sender):
        msg = f"""
💎 <b><i>VIP ADMIN ARRIVAL</i></b> 💎

🎖 <b><i>Welcome Our Respected Admin</i></b>  
✨ <i>Your guidance keeps this group disciplined!</i>

👑 <a href='tg://user?id={sender}'><b>Royal Admin</b></a>  
🔥 <i>The group feels safer when you're here!</i>
"""
        return await safe_send(event, msg)

    # ------------------------------------------------------------
    # 😊 NORMAL USER — FRIENDLY PREMIUM WELCOME
    # ------------------------------------------------------------
    sender_entity = await event.get_sender()
    # Failsafe for name
    username = (sender_entity.first_name or "Friend").replace("<", "").replace(">", "")

    msg = f"""
🌟 <b><i>HELLO NEW FRIEND!</i></b> 🌟

😊 <b>Welcome to the chat!</b> ✨ 

<b>Welcome to the chat!</b> 
<a href='tg://user?id={sender}'><b>{username}</b></a> ❤️
 
🔥 <i>Feel free to talk, we're friendly here 💖</i>

🌈 <i>Your presence just made the chat brighter!</i>  

🎀 <b>Glad to have you here,</b>  
"""
    return await safe_send(event, msg)

# ============================================================
# PREMIUM OWNER INFO PANEL (Callback)
# ============================================================
@bot.on(events.CallbackQuery(data=b"owner_info"))
async def owner_panel(event):
    owner_id = OWNER_ID
    
    try:
        owner = await bot.get_entity(owner_id)
        owner_name = owner.first_name or "Owner"
        owner_username = owner.username
    except Exception as e:
        logger.error(f"Error getting owner info: {e}")
        owner_name = "Owner (Unknown)"
        owner_username = None

    msg = f"""
🌟 <b><i>PREMIUM OWNER PANEL</i></b> 🌟

👑 <b><i>Meet The Master Behind This Bot</i></b> 👑  
——————————————  
<b>Name:</b> <a href='tg://user?id={owner_id}'><i>{owner_name}</i></a>  
<b>Role:</b> <i>Bot Developer & Owner</i>  
<b>Power:</b> ⚡ Full Access  
——————————————  

✨ <i>This bot exists because of his skills & creativity.</i>  
🔥 <i>All premium features, tag systems & automation flows are crafted by him.</i>

🌸 <b><i>Aesthetic Mind • Smart Developer • Friendly Personality</i></b>  
💬 <i>You can contact him for support or collaborations.</i>

🪄 <b>“Behind every smooth bot… there is a sleepless owner.”</b>  
"""

    buttons_list = []
    
    # Check if username is available for a clean link
    if owner_username:
        buttons_list.append([Button.url("💬 MESSAGE OWNER", f"https://t.me/{owner_username}")])
    else:
        buttons_list.append([Button.url("💬 MESSAGE OWNER (ID Link)", f"tg://openmessage?user_id={owner_id}")])

    buttons_list.append([Button.inline("⬅ BACK", data=b"back_to_menu")])
    
    await event.edit(msg, buttons=buttons_list, parse_mode="html")

@bot.on(events.CallbackQuery(data=b"back_to_menu"))
async def back_menu(event):
    msg = """
🌙✨ <b><i>Returning to the Main Menu…</i></b> ✨🌙

𓆩♡𓆪 <i>Your journey continues...</i>  
💫 <i>Bringing you back to the home panel...</i>  
🎀 <i>Press /start anytime to explore more.</i>

<b>⚡ 𝘼𝙚𝙨𝙩𝙝𝙚𝙩𝙞𝙘 • 𝙎𝙢𝙤𝙤𝙩𝙝 • 𝙋𝙧𝙚𝙢𝙞𝙪𝙢 ⚡</b>
"""

    buttons = [
        [Button.inline("🏠 MAIN MENU", data=b"main_start")]
    ]

    await event.edit(msg, buttons=buttons, parse_mode="html")
    
# ============================================================
# GAME SYSTEM CALLBACKS (Redirect to /start)
# ============================================================
@bot.on(events.CallbackQuery(data=b"games_menu"))
async def games_menu_callback(event):
    msg = """
🎮 <b>PREMIUM GAMES MENU</b> 🎮

✨ <i>Try these commands in the group:</i>

* <code>/truth</code>
* <code>/dare</code>
* <code>/tod</code>
* <code>/spin</code>
* <code>/kiss_marry_kill</code>
* <code>/love @user</code>
"""
    buttons = [
        [Button.inline("🏠 BACK TO START", data=b"main_start")]
    ]
    await event.edit(msg, buttons=buttons, parse_mode="html")

@bot.on(events.CallbackQuery(data=b"help_menu"))
async def help_menu_callback(event):
    msg = """
📚 <b>BOT COMMANDS & HELP</b> 📚

* <code>/start</code>: Main Menu
* <code>/panel</code>: Admin Control Panel (Admin/Owner)
* <code>/utag [message]</code>: Tag all (Admin Only)
* <code>/atag</code> / <code>/admin</code>: Tag Admins (Anyone)
* <code>/cancel</code>: Stop /utag

* <code>/couple @u1/name/reply</code>: Set Temporary Couple
* <code>/pcouple @u1/name/reply</code>: Set Permanent Couple
* <code>/breakup</code>: Break Permanent Couple

* <code>/Broadcast [message]</code>: Group Broadcast (Admin/Owner)
* <code>/Broadcast_image</code>: Image Broadcast (Admin/Owner)
* <code>/pm [message]</code>: Private Broadcast (Owner Only)
"""
    buttons = [
        [Button.inline("🏠 BACK TO START", data=b"main_start")]
    ]
    await event.edit(msg, buttons=buttons, parse_mode="html")

# ============================================================
# PREMIUM GAME SYSTEM — TRUTH & DARE
# ============================================================
truth_list = [
    "What's the biggest lie you've ever told?",
    "Who was your first crush?",
    "What is a secret you've never told anyone?",
    "What is the most embarrassing thing you own?",
    "What's the best compliment you've ever received?",
    "What is the most childish thing you still do?",
    "What is one thing you would change about your life?",
    "Who is your favorite user in this group right now?",
]

dare_list = [
    "Send your last clicked selfie!",
    "Say something nice to the last person who messaged you!",
    "Describe your crush using emojis only!",
    "Send a voice note singing your favorite song for 10 seconds!",
    "Change your Telegram bio to a joke for 1 hour.",
    "Tag three random people and call them 'Cutie Patootie'!",
    "Write a 5-word horror story in the chat.",
    "Post a picture of your favorite food.",
]

spin_results = [
    "🎯 You got *DARE*!",
    "💘 Someone secretly likes you!",
    "🔥 Send a roast to someone!",
    "🤣 Tell a joke!",
    "🎭 You got *Truth*!",
    "💎 You are the star of the day!",
    "😳 Share your last emoji!",
]

@bot.on(events.NewMessage(pattern=r"^/spin"))
async def spin(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
    result = random.choice(spin_results)
    await event.reply(f"🎡 <b>SPINNING WHEEL...</b>\n\n{result}", parse_mode="html")
    
@bot.on(events.NewMessage(pattern=r"^/kiss_marry_kill"))
async def kiss_marry_kill(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
         
    # Ensure there are at least 3 members to sample from
    try:
        members = [m async for m in bot.iter_participants(event.chat_id) if not m.bot]
    except Exception as e:
        logger.error(f"Error getting members for game: {e}")
        return await event.reply("❌ Bot needs admin rights to get member list for this game.")

    if len(members) < 3:
        return await event.reply("Need at least 3 members!")

    # Use try/except in case random.sample fails for some reason
    try:
        a, b, c = random.sample(members, 3)
    except ValueError:
        return await event.reply("❌ Could not pick 3 unique members!")
    
    # Safely get names
    a_name = a.first_name if a.first_name else "User A"
    b_name = b.first_name if b.first_name else "User B"
    c_name = c.first_name if c.first_name else "User C"

    await event.reply(
        f"❤️‍🔥 <b>KISS:</b> <a href='tg://user?id={a.id}'>{a_name}</a>\n"
        f"💍 <b>MARRY:</b> <a href='tg://user?id={b.id}'>{b_name}</a>\n"
        f"🔪 <b>KILL:</b> <a href='tg://user?id={c.id}'>{c_name}</a>",
        parse_mode="html"
    )
    
@bot.on(events.NewMessage(pattern=r"^/love"))
async def love(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
         
    percent = random.randint(1, 100)
    user2_name = None
    user2_id = None
    
    # 1. Check for reply
    reply = await event.get_reply_message()
    if reply and reply.sender_id != event.sender_id:
        try:
            user2_entity = await bot.get_entity(reply.sender_id)
            user2_name = user2_entity.first_name
            user2_id = user2_entity.id
        except Exception as e:
            logger.error(f"Error getting reply user: {e}")
            pass

    # 2. Check for mention or username in text
    if not user2_name:
        try:
            # Check for @username mention or user ID entity in the text
            if event.message.entities:
                for ent in event.message.entities:
                    if hasattr(ent, 'user_id') and ent.user_id:
                        user2_entity = await bot.get_entity(ent.user_id)
                        user2_name = user2_entity.first_name
                        user2_id = user2_entity.id
                        break
        except Exception as e:
            logger.error(f"Error parsing mention: {e}")
            pass

    # If someone is mentioned or replied → show their love percentage
    if user2_name and user2_id:
        await event.reply(
            f"💞 <b>Love Match Result</b> 💞\n\n"
            f"❤️ <i>Your love with</i> <a href='tg://user?id={user2_id}'><b>{user2_name}</b></a> <i>is</i>:\n\n"
            f"💘 <b>{percent}%</b> 💘\n\n"
            f"✨ <i>Perfect pairing vibes!</i>",
            parse_mode="html"
        )
        return

    # Default: No user mentioned → self love
    sender = await event.get_sender()

    await event.reply(
        f"💖 <b>SELF LOVE METER</b> 💖\n\n"
        f"✨ <i>{sender.first_name}, your love level is</i>\n\n"
        f"💘 <b>{percent}%</b> 💘\n\n"
        f"💗 <i>You deserve all the love in the world!</i>",
        parse_mode="html"
    )

# ---------- TRUTH ----------
@bot.on(events.NewMessage(pattern=r"^/truth"))
async def truth_cmd(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
    q = random.choice(truth_list)
    await event.reply(f"🎭 <b><i>TRUTH QUESTION:</i></b>\n\n✨ {q}", parse_mode="html")

# ---------- DARE ----------
@bot.on(events.NewMessage(pattern=r"^/dare"))
async def dare_cmd(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
    q = random.choice(dare_list)
    await event.reply(f"🔥 <b><i>DARE CHALLENGE:</i></b>\n\n⚡ {q}", parse_mode="html")

# ---------- TRUTH OR DARE ----------
@bot.on(events.NewMessage(pattern=r"^/tod"))
async def tod_cmd(event):
    if not event.is_group:
         return await event.reply("❌ This command only works in groups.")
    mode = random.choice(["Truth", "Dare"])
    if mode == "Truth":
        q = random.choice(truth_list)
        await event.reply(f"🎭 <b>TRUTH</b> selected!\n\n✨ {q}", parse_mode="html")
    else:
        q = random.choice(dare_list)
        await event.reply(f"🔥 <b>DARE</b> selected!\n\n⚡ {q}", parse_mode="html")

# ============================================================
# /couple — AUTO TEMPORARY COUPLE (username, reply, name)
# ============================================================
async def find_user_by_name(chat_id, query):
    query = query.lower()

    # Iterate over members to find a name match
    async for member in bot.iter_participants(chat_id):
        # Safely get full name
        first_name = member.first_name or ""
        last_name = member.last_name or ""
        fullname = f"{first_name} {last_name}".lower().strip()

        if fullname == query:
            return member
        if fullname.startswith(query):
            return member
        if query in fullname:
            return member
    return None

@bot.on(events.NewMessage(pattern=r"^/couple"))
async def couple_auto(event):
    if not event.is_group:
        return await event.reply("❌ Yeh command sirf groups me kaam karti hai!")

    sender_id = event.sender_id

    # 1️⃣ Reply support
    target_id = None
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply:
            target_id = reply.sender_id

    if not target_id:
        # 2️⃣ Username, ID, or Name search
        parts = event.raw_text.split(maxsplit=1)
        if len(parts) < 2:
            return await event.reply("Usage: /couple @user or reply to user or name")

        user_arg = parts[1]

        # Try username/ID first
        try:
            target = await bot.get_entity(user_arg)
            target_id = target.id
        except Exception as e:
            logger.error(f"Error getting entity: {e}")
            # Search by name
            target = await find_user_by_name(event.chat_id, user_arg)
            if not target:
                return await event.reply("❌ User not found! Username ya naam sahi likho.")
            target_id = target.id

    if sender_id == target_id:
        return await event.reply("🥺❤️ Khud ka couple khud se nahi ban sakta baby!")

    # Final validation on target
    if not target_id:
        return await event.reply("❌ Invalid user selected for couple command.")

    # Delete existing temp couple if any
    delete_temp_couple(event.chat_id)
    # Set new temp couple
    set_temp_couple(event.chat_id, sender_id, target_id)

    # Fetch entities again for proper names
    try:
        u1 = await bot.get_entity(sender_id)
        u2 = await bot.get_entity(target_id)
        u1_name = u1.first_name or "Partner 1"
        u2_name = u2.first_name or "Partner 2"
    except Exception as e:
        logger.error(f"Error getting user entities: {e}")
        u1_name = "Partner 1"
        u2_name = "Partner 2"
    
    # Romantic text
    await event.reply(
        f"""
💞✨ <b><i>New Cute Couple Detected!</i></b> ✨💞

❤️ <a href='tg://user?id={sender_id}'>{u1_name}</a>
      +
💖 <a href='tg://user?id={target_id}'>{u2_name}</a>

🌸 <i>Aww... kitne cute lag rahe ho saath-saath! 💗</i>

💬 <i>Kabhi kabhi do log yun hi mil jaate hain…
Aur group ki vibe hi romantic ho jaati hai.</i> ✨

💕 <b>Temporary couple for now… par dil se permanent ho sakte ho!</b>
""",
        parse_mode="html"
    )

async def quick_find_user(chat_id, query):
    query = query.lower()

    exact = None
    starts = None
    contains = None

    async for member in bot.iter_participants(chat_id):
        first_name = member.first_name or ""
        last_name = member.last_name or ""
        fullname = f"{first_name} {last_name}".lower().strip()

        # 1️⃣ Exact match
        if fullname == query:
            return member

        # 2️⃣ Starts with match
        if fullname.startswith(query):
            if not starts:
                starts = member

        # 3️⃣ Contains match
        if query in fullname:
            if not contains:
                contains = member

    # Priority: exact > starts > contains
    return exact or starts or contains

# ============================================================
# /pcouple — PERMANENT COUPLE (username, reply, name)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/pcouple"))
async def couple_perm(event):
    if not event.is_group:
        return await event.reply("❌ Yeh command sirf groups me kaam karti hai!")

    sender_id = event.sender_id
    target_id = None

    # 1️⃣ If reply
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply:
            target_id = reply.sender_id

    if not target_id:
        # 2️⃣ Try to get user from text
        parts = event.raw_text.split(maxsplit=1)

        if len(parts) < 2:
            return await event.reply("Usage: /pcouple @user OR name OR reply")

        user_arg = parts[1]

        # Try username first
        try:
            target = await bot.get_entity(user_arg)
            target_id = target.id
        except Exception as e:
            logger.error(f"Error getting entity: {e}")
            # NEW Quick search method
            try:
                target = await quick_find_user(event.chat_id, user_arg)
                if not target:
                    return await event.reply("❌ User not found! Naam thoda sahi likho.")
                target_id = target.id
            except Exception as e:
                logger.error(f"Error finding user: {e}")
                return await event.reply("❌ Error fetching user for permanent couple.")

    if sender_id == target_id:
        return await event.reply("🥺❤️ Khud se permanent couple nahi ban sakte baby!")
    
    # Final validation on target
    if not target_id:
        return await event.reply("❌ Invalid user selected for permanent couple command.")

    # Fetch entities for names
    try:
        u1 = await bot.get_entity(sender_id)
        u2 = await bot.get_entity(target_id)
        u1_name = u1.first_name or "Partner 1"
        u2_name = u2.first_name or "Partner 2"
    except Exception as e:
        logger.error(f"Error getting user entities: {e}")
        u1_name = "Partner 1"
        u2_name = "Partner 2"

    msg = f"""
💍✨ <b><i>PERMANENT COUPLE REQUEST</i></b> ✨💍

❤️ <a href='tg://user?id={sender_id}'>{u1_name}</a>
<i>aapke saath hamesha ke liye juda rehna chahte hain…</i>

💖 <a href='tg://user?id={target_id}'>{u2_name}</a>,
<i>Kya aap unka haath thamein aur official couple banna chahoge? 💞</i>

🌸 <i>Mohabbat ka faisla dil se hota hai…
Aur dil hamesha sahi insaan ko pehchaan leta hai.</i> ❤️

👇 Choose your answer:
"""

    buttons = [
        [Button.inline("YES ❤️", data=f"pc_yes_{sender_id}_{target_id}".encode())],
        [Button.inline("NO ❌", data=f"pc_no_{sender_id}_{target_id}".encode())],
    ]

    await event.reply(msg, buttons=buttons, parse_mode="html")

# ============================================================
# YES / NO Handler — DO NOT CHANGE
# ============================================================
@bot.on(events.CallbackQuery(pattern=b"pc_"))
async def perm_couple_buttons(event):
    data = event.data.decode().split("_")
    if len(data) < 4:
        return await event.answer("Invalid callback data!", alert=True)
        
    action = data[1]
    sender_id = int(data[2])
    target_id = int(data[3])

    if event.sender_id != target_id:
        return await event.answer("⛔ Sirf jisey propose kiya gaya hai, wahi jawab de sakta hai!", alert=True)

    # Fetch entities for names
    try:
        u1 = await bot.get_entity(sender_id)
        u2 = await bot.get_entity(target_id)
        u1_name = u1.first_name or "Partner 1"
        u2_name = u2.first_name or "Partner 2"
    except Exception as e:
        logger.error(f"Error getting user entities: {e}")
        u1_name = "Partner 1"
        u2_name = "Partner 2"

    if action == "yes":
        # Set permanent couple & remove temporary couple (if any)
        set_perm_couple(event.chat_id, sender_id, target_id)
        delete_temp_couple(event.chat_id)

        await event.edit(
            f"""
💍❤️ <b><i>Permanent Couple Created!</i></b> ❤️💍

❤️ <a href='tg://user?id={sender_id}'>{u1_name}</a>
💖 <a href='tg://user?id={target_id}'>{u2_name}</a>

🌈✨ <i>Awww! Ab aap dono officially couple ho!  
Dua hai hamesha saath rahoge, muskuraoge, aur pyaar badhega 💞</i>

🌸 <i>Kismat se zyada khoobsurat hoti hai woh mulaqat,
jab sath ho koi apna, aur dil kare sirf unki baat.</i> ✨
""",
            parse_mode="html"
        )
    else:
        await event.edit(
            """
💔❌ <b>Couple Request Denied</b> ❌💔

<i>Mohabbat zabardasti nahi hoti…
Dil ko waqt lagta hai ✨</i>

🌸 <i>Kabhi kabhi na kehna bhi zaroori hota hai…
Taaki dil future mein sahi log ke liye jagah bana sake.</i> 💗
""",
            parse_mode="html"
        )

# ============================================================
# FINAL PREMIUM /BREAKUP COMMAND
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/breakup"))
async def breakup(event):
    if not event.is_group:
        return

    chat = event.chat_id
    sender = event.sender_id

    # Load permanent couple
    couple = get_perm_couple(chat)
    if not couple:
        return await event.reply(
            "❌ <b>Is group me koi permanent couple set nahi hai.</b>",
            parse_mode="html"
        )

    u1, u2 = couple

    # -----------------------------------------------------------
    # PERMISSION RULES (FINAL FIXED)
    # -----------------------------------------------------------
    allowed = False
    
    # 1️⃣ Couple ka banda breakup kar sakta hai
    if sender in (u1, u2):
        allowed = True

    # 2️⃣ Bot Owner breakup kar sakta hai (Emergency)
    elif is_owner(sender):
        allowed = True

    # 3️⃣ Group Admin or Global Bot Admin - can break up
    elif is_bot_admin(sender) or await is_admin(chat, sender):
        allowed = True
        
    # ❌ If NOT allowed → send warning
    if not allowed:
        return await event.reply(
            "❌ <b>Breakup Permission Denied!</b>\n\n"
            "💬 Sirf couple ka banda hi breakup kar sakta hai.\n"
            "🛡 Group Admin/Bot Admin ya Owner emergency me breakup kar sakte hain.",
            parse_mode="html"
        )

    # -----------------------------------------------------------
    # PROCESS BREAKUP
    # -----------------------------------------------------------
    delete_perm_couple(chat)
    
    # Get user entities for names
    try:
        u1_entity = await bot.get_entity(u1)
        u2_entity = await bot.get_entity(u2)
        
        u1_name = u1_entity.first_name if u1_entity.first_name else "Partner 1"
        u2_name = u2_entity.first_name if u2_entity.first_name else "Partner 2"
    except Exception as e:
        logger.error(f"Error getting user entities: {e}")
        u1_name = "Partner 1"
        u2_name = "Partner 2"

    # -----------------------------------------------------------
    # HUMAN STYLE EMOTIONAL BREAKUP MESSAGE
    # -----------------------------------------------------------
    msg = f"""
💔 <b>—  H E A R T B R E A K   C O M P L E T E —</b> 💔

<b>💞 Kabhi socha nahi था कि यह pal भी देखना पड़ेगा…</b>

❤️ <a href='tg://user?id={u1}'>{u1_name}</a>  
💖 <a href='tg://user?id={u2}'>{u2_name}</a>

<b>✨ Aaj se aap dono ke rishte ki kitaab ka ek aur safha band ho gaya...</b>

🌙 <i>Kehte hain kuch log hamesha ke liye nahi, sirf hume kuch sikhane aate hain…</i>  
🌧 <i>Shayad yeh judaai bhi ek naya raasta dikha de…</i>

🍃 <b>Zindagi rukti nahi… bas badal jaati hai.</b>  
🕊 <i>Duwa hai, aap dono jahan bhi raho— khush raho, muskurate raho.</i>

💫 <b>— Life Moves On —</b>
"""

    await event.reply(msg, parse_mode="html")
    
# ============================================================
# MAIN COUPLE WELCOME HANDLER
# ============================================================
@bot.on(events.NewMessage)
async def couple_welcome(event):
    if not event.is_group:
        return

    sender = event.sender_id
    chat = event.chat_id
    
    # Ensure event has a sender for checks
    if not sender:
        return

    # Skip bot messages and commands
    me = await bot.get_me()
    if sender == me.id or (event.raw_text and event.raw_text.startswith("/")):
        return

    # ------------------------------------------------------------
    # PERMANENT COUPLE CHECK
    # ------------------------------------------------------------
    perm = get_perm_couple(chat)
    if perm:
        u1, u2 = perm

        # Only couple users can trigger welcome
        if sender in (u1, u2):
            # Show welcome only once every 24 hours
            if not has_greeted(chat, sender):
                update_greet(chat, sender)
                
                try:
                    u1_entity = await bot.get_entity(u1)
                    u2_entity = await bot.get_entity(u2)
                    
                    u1_name = u1_entity.first_name if u1_entity.first_name else "Partner 1"
                    u2_name = u2_entity.first_name if u2_entity.first_name else "Partner 2"
                except Exception as e:
                    logger.error(f"Error getting user entities: {e}")
                    u1_name = "Partner 1"
                    u2_name = "Partner 2"

                msg = f"""
💞 <b>PREMIUM PERMANENT COUPLE ALERT</b> 💞

❤️ <a href='tg://user?id={u1}'>{u1_name}</a>
💖 <a href='tg://user?id={u2}'>{u2_name}</a>

🌸 Aap dono ka rishta permanent safar par hai…
💍 Bot Owner ki taraf se shadi mubarak & blessings ❤️

✨ Every 24 hours, love refreshes again!
"""
                # CRITICAL FIX: Ensure parse_mode is closed correctly
                await event.reply(msg, parse_mode="html")
        return

    # ------------------------------------------------------------
    # TEMPORARY COUPLE CHECK (VALID 24 HOURS ONLY)
    # ------------------------------------------------------------
    temp = get_temp_couple(chat)
    if temp:
        u1, u2, created_time = temp

        # If 24 hours passed → delete temp couple
        if time.time() - created_time > 86400:
            delete_temp_couple(chat)
            return

        if sender in (u1, u2):
            # Show welcome only once every 24 hours
            if not has_greeted(chat, sender):
                update_greet(chat, sender)
                
                try:
                    u1_entity = await bot.get_entity(u1)
                    u2_entity = await bot.get_entity(u2)
                    
                    u1_name = u1_entity.first_name if u1_entity.first_name else "Partner 1"
                    u2_name = u2_entity.first_name if u2_entity.first_name else "Partner 2"
                except Exception as e:
                    logger.error(f"Error getting user entities: {e}")
                    u1_name = "Partner 1"
                    u2_name = "Partner 2"

                msg = f"""
💞 <b>CUTE TEMPORARY COUPLE ALERT</b> 💞

❤️ <a href='tg://user?id={u1}'>{u1_name}</a>
💖 <a href='tg://user?id={u2}'>{u2_name}</a>

🌸 Aap dono 24 hours ke liye ek cute couple ho!
💍 Owner ki taraf se shadi mubarak ❤️

⏳ 24 hours complete hone par reset ho jayega…
"""
                # CRITICAL FIX: Ensure parse_mode is closed correctly
                await event.reply(msg, parse_mode="html")

# ============================================================
# 1. PREMIUM AESTHETIC START MENU (FOR /start COMMAND)
# ============================================================
@bot.on(events.NewMessage(pattern=r"^/start"))
async def start_menu_command(event):
    # FIX: Fetch sender name properly
    sender = await event.get_sender()
    sender_name = sender.first_name if sender.first_name else "User"

    photo_url = START_PHOTO_URL

    caption = f"""
<b>♡ 𝙄𝙩'𝙨 𝙈𝙚 ︵『{sender_name if event.is_private else "Your Tag Bot"}』 💖</b>

<b>⚡ 𝘼 𝙎𝙢𝙖𝙧𝙩 𝗧𝗮𝗴-𝗕𝗼𝘁 ⚡</b>
♡ 𝗙𝘂𝗻 Convers𝙖𝙩𝙞𝙤𝙣𝙨  
♡ 𝗪𝗼𝗿𝗸𝘀 𝗶𝗻 𝗚𝗿𝗼𝘂𝗽𝘀 & 𝗣𝗿𝗶𝘃𝗮𝘁𝗲  
♡ 𝗞𝗲𝗲𝗽𝘀 𝗖𝗵𝗮𝘁𝘀 𝗔𝗰𝘁𝗶𝘃𝗲 + 𝗙𝘂𝗻  
♡ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗧𝗮𝗴 𝗦𝘆𝘀𝘁𝗲𝗺  
♡ 𝗦𝘁𝘆𝗹𝗶𝘀𝗵 & 𝗦𝗺𝗼𝗼𝘁𝗵  
♡ 𝗚𝗮𝗺𝗲𝘀 • 𝗙𝘂𝗻 𝗧𝗼𝗼𝗹𝘀  
♡ 𝗔𝗻𝗶𝗺𝗲 & 𝗔𝗲𝘀𝘁𝗵𝗲𝘁𝗶𝗰 𝗧𝗵𝗲𝗺𝗲𝘀  
""".strip()

    try:
        me = await bot.get_me()
        bot_username = me.username
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        bot_username = ""

    buttons = [
        [Button.url("➕ ADD ME TO YOUR GROUP ➕", f"https://t.me/{bot_username}?startgroup=new")],

        [
            Button.inline("OWNER", data=b"owner_info"),
            Button.inline("GAME", data=b"games_menu")
        ],

        [Button.inline("HELP & COMMANDS", data=b"help_menu")],

        [
            Button.url("SUPPORT", f"https://t.me/{SUPPORT_CHAT}"),
            Button.url("UPDATES", f"https://t.me/{UPDATES_CHANNEL}")
        ]
    ]

    try:
        # Use send_file with the photo URL
        await bot.send_file(
            event.chat_id,
            photo_url,
            caption=caption,
            buttons=buttons,
            parse_mode="html"
        )
    except Exception as e:
        logger.error(f"Error sending start menu (try fallback): {e}")
        # Fallback to sending text if file fails
        await event.reply(caption, buttons=buttons, parse_mode="html")

# ============================================================
# 2. CALLBACK FOR BUTTON CLICKS (e.g., BACK TO MENU)
# ============================================================
@bot.on(events.CallbackQuery(data=b"main_start"))
async def start_menu_callback(event):
    sender = await event.get_sender()
    sender_name = sender.first_name if sender.first_name else "User"
    
    photo_url = START_PHOTO_URL

    caption = f"""
<b>♡ 𝙄𝙩'𝙨 𝙈𝙚 ︵『{sender_name}』 💖</b>

<b>⚡ 𝘼 𝙎𝙢𝙖𝙧𝙧 𝗧𝗮𝗴-𝗕𝗼𝘁 ⚡</b>
♡ 𝗙𝘂𝗻 Convers𝙖𝙩𝙞𝙤𝙣𝙨  
♡ 𝗪𝗼𝗿𝗸𝘀 𝗶𝗻 𝗚𝗿𝗼𝘂𝗽𝘀 & 𝗣𝗿𝗶𝘃𝗮𝘁𝗲  
♡ 𝗞𝗲𝗲𝗽𝘀 𝗖𝗵𝗮𝘁𝘀 𝗔𝗰𝘁𝗶𝘃𝗲 + 𝗙𝘂𝗻  
♡ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗧𝗮𝗴 𝗦𝘆𝘀𝘁𝗲𝗺  
♡ 𝗦𝘁𝘆𝗹𝗶𝘀𝗵 & 𝗦𝙢𝗼𝗼𝘁𝗵  
♡ 𝗚𝗮𝗺𝗲𝘀 • 𝗙𝘂𝗻 𝗧𝗼𝗼𝗹𝘀  
♡ 𝗔𝗻𝗶𝗺𝗲 & 𝗔𝗲𝘀𝘁𝗵𝗲𝘁𝗶𝗰 𝗧𝗵𝗲𝗺𝗲𝘀  
""".strip()
    
    try:
        me = await bot.get_me()
        bot_username = me.username
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        bot_username = ""
    
    buttons = [
        [Button.url("➕ ADD ME TO YOUR GROUP ➕", f"https://t.me/{bot_username}?startgroup=new")],

        [
            Button.inline("OWNER", data=b"owner_info"),
            Button.inline("GAME", data=b"games_menu")
        ],

        [Button.inline("HELP & COMMANDS", data=b"help_menu")],

        [
            Button.url("SUPPORT", f"https://t.me/{SUPPORT_CHAT}"),
            Button.url("UPDATES", f"https://t.me/{UPDATES_CHANNEL}")
        ]
    ]

    try:
        # Use edit with file=photo_url to update the media and text
        await event.edit(text=caption, buttons=buttons, file=photo_url, parse_mode="html")
    except Exception as e:
        logger.error(f"Error editing callback: {e}")
        # Fallback to editing text only if media edit fails
        await event.edit(text=caption, buttons=buttons, parse_mode="html")

print("🔥 FULL TAG BOT + BROADCAST + PANEL SYSTEM READY…")
bot.run_until_disconnected()
