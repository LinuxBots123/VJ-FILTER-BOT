# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging
from pyrogram import Client, emoji
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultCachedDocument,
    InlineQuery
)

from database.ia_filterdb import get_search_results
from utils import is_subscribed, get_size, temp
from info import CACHE_TIME, AUTH_USERS, AUTH_CHANNEL, CUSTOM_FILE_CAPTION

logger = logging.getLogger(__name__)
cache_time = 0 if AUTH_USERS or AUTH_CHANNEL else CACHE_TIME


# ✅ CHECK USER
async def inline_users(query: InlineQuery):
    if AUTH_USERS:
        if query.from_user and query.from_user.id in AUTH_USERS:
            return True
        else:
            return False
    if query.from_user and query.from_user.id not in temp.BANNED_USERS:
        return True
    return False


# ✅ INLINE HANDLER
@Client.on_inline_query()
async def answer(bot, query: InlineQuery):

    # ❌ NOT ALLOWED
    if not await inline_users(query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text='Not allowed',
            switch_pm_parameter="start"
        )
        return

    # ❌ FORCE JOIN
    if AUTH_CHANNEL and not await is_subscribed(bot, query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text='Join my channel to use bot',
            switch_pm_parameter="subscribe"
        )
        return

    results = []

    # 🔍 SPLIT QUERY
    if '|' in query.query:
        string, file_type = query.query.split('|', maxsplit=1)
        string = string.strip()
        file_type = file_type.strip().lower()
    else:
        string = query.query.strip()
        file_type = None

    offset = int(query.offset or 0)

    reply_markup = get_reply_markup(query=string)

    # 🔥🔥🔥 MAIN FIX (PROFESSOR STYLE)
    if not string:
        files, next_offset, total = await get_search_results(
            "",
            file_type=None,
            max_results=10,
            offset=offset
        )
    else:
        files, next_offset, total = await get_search_results(
            string,
            file_type=file_type,
            max_results=10,
            offset=offset
        )

    # 🧠 DEBUG (remove later if needed)
    print("INLINE FILES:", len(files))

    # 🎬 BUILD RESULTS
    for file in files:
        title = file.get('file_name')
        size = get_size(file.get('file_size'))
        f_caption = file.get('caption')

        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name=title or '',
                    file_size=size or '',
                    file_caption=f_caption or ''
                )
            except Exception as e:
                logger.exception(e)

        if not f_caption:
            f_caption = title or "No Name"

        results.append(
            InlineQueryResultCachedDocument(
                title=title,
                document_file_id=file['file_id'],
                caption=f_caption,
                description=f"Size: {size}",
                reply_markup=reply_markup
            )
        )

    # ✅ SEND RESULTS
    if results:
        if not string:
            switch_pm_text = f"🆕 Latest Movies ({total})"
        else:
            switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total} for {string}"

        try:
            await query.answer(
                results=results,
                is_personal=True,
                cache_time=cache_time,
                switch_pm_text=switch_pm_text,
                switch_pm_parameter="start",
                next_offset=str(next_offset)
            )
        except QueryIdInvalid:
            pass
        except Exception as e:
            logger.exception(e)

    # ❌ NO RESULTS
    else:
        if not string:
            switch_pm_text = "❌ No movies in database"
        else:
            switch_pm_text = f'❌ No results for "{string}"'

        await query.answer(
            results=[],
            is_personal=True,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="start"
        )


# 🔁 BUTTON
def get_reply_markup(query):
    buttons = [[
        InlineKeyboardButton(
            '⟳ sᴇᴀʀᴄʜ ᴀɢᴀɪɴ',
            switch_inline_query_current_chat=query
        )
    ]]
    return InlineKeyboardMarkup(buttons)
