# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, re, asyncio
from utils import temp
from info import ADMINS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

# ✅ SAFE EDIT FUNCTION (ANTI FLOOD)
async def safe_edit(msg, text, reply_markup=None):
    try:
        return await msg.edit_text(text=text, reply_markup=reply_markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await msg.edit_text(text=text, reply_markup=reply_markup)
    except MessageNotModified:
        pass
    except:
        pass


@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")

    _, raju, chat, lst_msg_id, from_user = query.data.split("#")

    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(int(from_user),
            f'Your Submission for indexing {chat} has been declined.',
            reply_to_message_id=int(lst_msg_id))
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)

    msg = query.message
    await query.answer('Processing...⏳', show_alert=True)

    await safe_edit(
        msg,
        "Starting Indexing",
        InlineKeyboardMarkup([[InlineKeyboardButton('Cancel', callback_data='index_cancel')]])
    )

    try:
        chat = int(chat)
    except:
        pass

    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        temp.CURRENT = int(skip)
        await message.reply(f"Skip set to {skip}")
    else:
        await message.reply("Give skip number")


# 🔥 MAIN INDEX FUNCTION (FIXED)
async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0

    async with lock:
        try:
            current = temp.CURRENT
            temp.CANCEL = False

            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):

                if temp.CANCEL:
                    await safe_edit(msg, f"❌ Cancelled\nSaved: {total_files}")
                    break

                current += 1

                # ✅ 🔥 EDIT ONLY EVERY 1000 FILES
                if total_files % 1000 == 0 and total_files != 0:
                    await safe_edit(
                        msg,
                        f"📦 Indexed: <code>{total_files}</code>\n"
                        f"Duplicate: <code>{duplicate}</code>\n"
                        f"Deleted: <code>{deleted}</code>\n"
                        f"Skipped: <code>{no_media + unsupported}</code>\n"
                        f"Errors: <code>{errors}</code>"
                    )

                # ✅ SMALL DELAY (ANTI FLOOD)
                await asyncio.sleep(0.02)

                if message.empty:
                    deleted += 1
                    continue

                if not message.media:
                    no_media += 1
                    continue

                if message.media not in [
                    enums.MessageMediaType.VIDEO,
                    enums.MessageMediaType.AUDIO,
                    enums.MessageMediaType.DOCUMENT
                ]:
                    unsupported += 1
                    continue

                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue

                media.caption = message.caption

                aynav, vnay = await save_file(media)

                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                else:
                    errors += 1

        except Exception as e:
            logger.exception(e)
            await safe_edit(msg, f"❌ Error: {e}")

        else:
            # ✅ FINAL RESULT
            await safe_edit(
                msg,
                f"✅ Done Indexing\n\n"
                f"Saved: <code>{total_files}</code>\n"
                f"Duplicate: <code>{duplicate}</code>\n"
                f"Deleted: <code>{deleted}</code>\n"
                f"Skipped: <code>{no_media + unsupported}</code>\n"
                f"Errors: <code>{errors}</code>"
            )
