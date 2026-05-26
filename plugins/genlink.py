# Don't Remove Credit @Linux_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import os
import json
import base64
import logging
import urllib.parse

from utils import temp

from pyrogram import filters, Client, enums

from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    UsernameInvalid,
    UsernameNotModified
)

from info import (
    ADMINS,
    LOG_CHANNEL,
    FILE_STORE_CHANNEL,
    PUBLIC_FILE_STORE,
    URL
)

from database.ia_filterdb import unpack_new_file_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# =========================================================
# ALLOWED
# =========================================================

async def allowed(_, __, message):

    if PUBLIC_FILE_STORE:
        return True

    if (
        message.from_user
        and message.from_user.id in ADMINS
    ):
        return True

    return False


# =========================================================
# SINGLE FILE LINK
# =========================================================

@Client.on_message(
    filters.command(['link', 'plink'])
    & filters.create(allowed)
)
async def gen_link_s(bot, message):

    vj = await bot.ask(
        chat_id=message.from_user.id,
        text="Send the file (video/audio/document)."
    )

    file_type = vj.media

    if file_type not in [
        enums.MessageMediaType.VIDEO,
        enums.MessageMediaType.AUDIO,
        enums.MessageMediaType.DOCUMENT
    ]:

        return await vj.reply(
            "❌ Only video/audio/document allowed."
        )

    media = getattr(vj, file_type.value)

    # FILE ID
    file_id = unpack_new_file_id(media.file_id)

    # HASH
    secure_hash = media.file_unique_id[:6]

    # FILE NAME
    file_name = getattr(
        media,
        "file_name",
        f"{file_id}.mp4"
    )

    # URL ENCODE
    file_name = urllib.parse.quote(file_name)

    # WATCH URL
    watch_url = (
        f"{URL}/watch/"
        f"{file_id}/"
        f"{file_name}"
        f"?hash={secure_hash}"
    )

    # STREAM URL
    stream_url = (
        f"{URL}/"
        f"{file_id}/"
        f"{file_name}"
        f"?hash={secure_hash}"
    )

    txt = (
        f"✅ Link Generated\n\n"

        f"🎥 Watch Link:\n"
        f"{watch_url}\n\n"

        f"📥 Download Link:\n"
        f"{stream_url}"
    )

    await message.reply(
        txt,
        disable_web_page_preview=True
    )


# =========================================================
# BATCH LINK
# =========================================================

@Client.on_message(
    filters.command(['batch', 'pbatch'])
    & filters.create(allowed)
)
async def gen_link_batch(bot, message):

    if " " not in message.text:

        return await message.reply(
            "❌ Use:\n"
            "/batch first_link last_link"
        )

    links = message.text.strip().split(" ")

    if len(links) != 3:

        return await message.reply(
            "❌ Use:\n"
            "/batch first_link last_link"
        )

    cmd, first, last = links

    regex = re.compile(
        r"(https://)?"
        r"(t\.me/|telegram\.me/|telegram\.dog/)"
        r"(c/)?"
        r"(\d+|[a-zA-Z_0-9]+)/(\d+)$"
    )

    # FIRST LINK
    match = regex.match(first)

    if not match:
        return await message.reply(
            "❌ Invalid first link"
        )

    f_chat_id = match.group(4)

    f_msg_id = int(match.group(5))

    if f_chat_id.isnumeric():
        f_chat_id = int("-100" + f_chat_id)

    # LAST LINK
    match = regex.match(last)

    if not match:
        return await message.reply(
            "❌ Invalid second link"
        )

    l_chat_id = match.group(4)

    l_msg_id = int(match.group(5))

    if l_chat_id.isnumeric():
        l_chat_id = int("-100" + l_chat_id)

    if f_chat_id != l_chat_id:

        return await message.reply(
            "❌ Chat IDs do not match."
        )

    try:

        chat_id = (
            await bot.get_chat(f_chat_id)
        ).id

    except ChannelInvalid:

        return await message.reply(
            "❌ Make me admin in channel."
        )

    except (
        UsernameInvalid,
        UsernameNotModified
    ):

        return await message.reply(
            "❌ Invalid link."
        )

    except Exception as e:

        return await message.reply(
            f"❌ Error:\n{e}"
        )

    sts = await message.reply(
        "⏳ Processing..."
    )

    outlist = []

    total = 0

    async for msg in bot.iter_messages(
        f_chat_id,
        l_msg_id,
        f_msg_id
    ):

        if msg.empty or msg.service:
            continue

        if not msg.media:
            continue

        try:

            file_type = msg.media

            media = getattr(
                msg,
                file_type.value
            )

            caption = getattr(
                msg,
                "caption",
                ""
            )

            if caption:
                caption = caption.html

            file_name = getattr(
                media,
                "file_name",
                f"{msg.id}.mp4"
            )

            file_name = urllib.parse.quote(
                file_name
            )

            file_id = unpack_new_file_id(
                media.file_id
            )

            secure_hash = (
                media.file_unique_id[:6]
            )

            watch = (
                f"{URL}/watch/"
                f"{file_id}/"
                f"{file_name}"
                f"?hash={secure_hash}"
            )

            stream = (
                f"{URL}/"
                f"{file_id}/"
                f"{file_name}"
                f"?hash={secure_hash}"
            )

            data = {

                "watch": watch,

                "stream": stream,

                "caption": caption,

                "title": file_name,
            }

            outlist.append(data)

            total += 1

        except Exception:
            pass

    file_path = (
        f"batchmode_"
        f"{message.from_user.id}.json"
    )

    with open(file_path, "w+") as out:
        json.dump(outlist, out, indent=4)

    post = await bot.send_document(
        LOG_CHANNEL,
        file_path,
        file_name="Batch.json",
        caption="Generated Batch Links"
    )

    os.remove(file_path)

    await sts.edit(
        f"✅ Batch Generated\n"
        f"Total Files: {total}"
    )
