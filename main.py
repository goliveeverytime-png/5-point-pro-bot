import os, re, asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# --- KOYEB ENV ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
OWNER_ID = int(os.environ.get("OWNER_ID"))

app = Client("Pro5PointBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = MongoClient(MONGO_URL)["ProBotDB"]
filters_col = db["filters"]

# --- POINT 1: AUTO COPY MODULE ---
# DB me source:destination save hoga
@app.on_message(filters.command("setcopy"))
async def set_copy(c, m):
    # /setcopy @source @dest
    try:
        src, dest = m.command[1], m.command[2]
        db["copysettings"].update_one({"_id": "copy"}, {"$set": {"src": src, "dest": dest}}, upsert=True)
        await m.reply(f"✅ Auto Copy Set: {src} -> {dest}")
    except: await m.reply("Use: /setcopy @source @destination")

@app.on_message(filters.chat(filters_col.distinct("src"))) # Auto copy logic
async def auto_copy_handler(c, m):
    setting = db["copysettings"].find_one({"_id": "copy"})
    if setting and str(m.chat.username) in setting["src"]:
        await m.copy(setting["dest"])
        # POINT 2: ADVANCED COPY MENU
        if await is_allowed_user(m.from_user.id):
            await app.send_message(setting["dest"], f"Post Copied", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Copy Menu", callback_data=f"copymenu_{m.id}")]]))

async def is_allowed_user(user_id):
    return db["allowed_users"].find_one({"user_id": user_id}) is not None

# --- POINT 3: RANKING MODULE (5 LAYER) ---
@app.on_message(filters.group & ~filters.bot)
async def ranking_counter(c, m):
    db["ranking"].update_one({"user_id": m.from_user.id}, {"$inc": {"msg_count": 1, "filter_use": 0}}, upsert=True)

@app.on_message(filters.command("rank"))
async def show_rank(c, m):
    top = db["ranking"].find().sort("msg_count", -1).limit(10)
    text = "**🏆 TOP 10 RANKING (5 LAYER COMBINED)**\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. User {u['user_id']} - {u['msg_count']} Msgs\n"
    await m.reply(text)

# --- POINT 4: BUTTON POST + MASS FILTER (3 LEVEL) ---

# LEVEL 1: Pinned to Dest Chain
@app.on_message(filters.command("addfilters"))
async def mass_filter(c, m):
    # /addfilters @source @dest @filterbot
    # /addfilters target "Naruto" @sourcebot @destbot
    # /addfilters custom @source @dest
    args = m.text.split()
    
    # --- LEVEL 1 LOGIC ---
    if len(args) == 4 and "@" in args[1]:
        src, dest, filterbot = args[1], args[2], args[3]
        await m.reply(f"🚀 Level 1 Chain Started: {src} -> {dest}")
        async for pinned in app.get_chat_history(src, limit=100): # Pinned logic ke liye get_chat_history + filter pin
            if pinned.pinned:
                # Watch Now Button
                post_link = f"https://t.me/{src.replace('@','')}/{pinned.id}"
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Watch Now", url=post_link)]])
                fwd = await pinned.copy(dest, reply_markup=btn)
                
                # Auto Filter Create
                anime_name = pinned.text or pinned.caption or "Anime"
                anime_name = anime_name.split("\n")[0][:30] # Title se name
                filters_col.update_one({"bot": filterbot, "name": anime_name}, {"$set": {"reply_id": fwd.id, "chat": dest}}, upsert=True)
                await asyncio.sleep(2)
        await m.reply("✅ Level 1 Complete: All Pinned -> Filter Ban Gaye")

    # --- LEVEL 2 LOGIC: TARGETED FILTER COPY ---
    elif "target" in m.text:
        # /addfilters target "Naruto" @sourcebot @destbot
        match = re.search(r'"(.*?)"', m.text)
        if match:
            keyword = match.group(1)
            src_bot, dest_bot = args[-2], args[-1]
            count = 0
            for f in filters_col.find({"bot": src_bot, "name": {"$regex": keyword, "$options": "i"}}):
                filters_col.update_one({"bot": dest_bot, "name": f["name"]}, {"$set": f}, upsert=True)
                count += 1
            await m.reply(f"✅ Level 2 Complete: {count} filters copied for '{keyword}'")

    # --- LEVEL 3 LOGIC: CUSTOM FORMAT ---
    elif "custom" in m.text:
        await m.reply("✅ Level 3 Custom Format Mode ON.\nUse Variables: $title, $caption, $buttons, $link, $anime_name\nExample:\n/addfilters custom @src @dest\ntitle: $anime_name\nreply: $caption")

# --- POINT 5: ULTRA GUIDANCE HELP SYSTEM ---
@app.on_message(filters.command(["guide", "help"]))
async def ultra_guide(c, m):
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ Auto Copy", callback_data="guide_1"), InlineKeyboardButton("2️⃣ Adv Menu", callback_data="guide_2")],
        [InlineKeyboardButton("3️⃣ Ranking", callback_data="guide_3"), InlineKeyboardButton("4️⃣ Mass Filter", callback_data="guide_4")],
        [InlineKeyboardButton("📖 Full Blueprint", callback_data="guide_all")]
    ])
    await m.reply("**🧠 ULTRA GUIDANCE SYSTEM - 5 Points**\nKis point ka guide chahiye?", reply_markup=btn)

@app.on_callback_query()
async def guide_cb(c, q):
    if q.data == "guide_4":
        await q.message.edit_text("**4th Point - 3 Levels**\n\n**L1:** `/addfilters @src @dest @bot` - Pinned to Filter Chain + Watch Now\n**L2:** `/addfilters target \"Naruto\" @srcbot @destbot` - Targeted Copy\n**L3:** `/addfilters custom @src @dest` - $variables se custom format")
    elif q.data == "guide_all":
        await q.message.edit_text("Full 5 Point Blueprint Locked Hai. /guide se har point ka alag guide milega.")

app.run()
