import sys, glob, importlib, logging, logging.config, pytz, asyncio, os
from pathlib import Path
from aiohttp import web
from pyrogram import idle
from datetime import date, datetime

# Logging
logging.basicConfig(level=logging.INFO)

# Import your modules
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins.clone import restart_bots

from TechVJ.bot import TechVJBot
from TechVJ.bot.clients import initialize_clients

# ------------------- IMPORTANT -------------------
PORT = int(os.environ.get("PORT", 8080))  # Render dynamic port
# -------------------------------------------------

ppath = "plugins/*.py"
files = glob.glob(ppath)

TechVJBot.start()
loop = asyncio.get_event_loop()

# ------------------- WEB SERVER -------------------
async def web_server():
    app = web.Application()

    async def home(request):
        return web.Response(text="Bot is running ✅")

    app.router.add_get("/", home)
    return app
# -------------------------------------------------

async def start():
    print("🚀 Initializing Your Bot")

    await initialize_clients()

    # Load plugins
    for name in files:
        patt = Path(name)
        plugin_name = patt.stem
        import_path = f"plugins.{plugin_name}"

        spec = importlib.util.spec_from_file_location(import_path, name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[import_path] = module

        print("✅ Loaded =>", plugin_name)

    # DB banned users
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    me = await TechVJBot.get_me()
    temp.BOT = TechVJBot
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name

    logging.info("🤖 Bot Started Successfully")

    # Restart log
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    today = date.today()

    try:
        await TechVJBot.send_message(
            chat_id=LOG_CHANNEL,
            text=f"✅ Bot Restarted\n📅 {today}\n⏰ {now.strftime('%H:%M:%S')}"
        )
    except:
        print("⚠️ Make bot admin in log channel")

    # Start web server (VERY IMPORTANT FOR RENDER)
    app = web.AppRunner(await web_server())
    await app.setup()
    await web.TCPSite(app, "0.0.0.0", PORT).start()

    print(f"🌐 Web server started on port {PORT}")

    await idle()


if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        print("❌ Bot stopped")
