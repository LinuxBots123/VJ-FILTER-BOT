# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging
import re
import asyncio

from utils import temp
from info import ADMINS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    ChatAdminRequired,
    UsernameInvalid,
    UsernameNotModified
)
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lock = asyncio.Lock()


@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")

    _, raju, chat, lst_msg_id, from_user = query.data.split("#")

    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been declined by moderators.',
            reply_to_message_id=int(lst_msg_id)
        )
        return

    if lock.locked():
        return await query.answer(
            'Wait until previous process completes.',
            show_alert=True
        )

    msg = query.message
    await query.answer('Processing...⏳', show_alert=True)

    if int(from_user) not in ADMINS:
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been accepted and will be processed.',
            reply_to_message_id=int(lst_msg_id)
        )

    await msg.edit(
        "Starting Indexing...",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )

    try:
        chat = int(chat)
    except:
        pass

    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command('index'))
async def send_for_index(bot, message):
    vj = await bot.ask(
        message.chat.id,
        "**Send Channel Last Post Link or Forward Last Message.\n\n"
        "Set skip using /setskip number**"
    )

    if vj.forward_from_chat and vj.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = vj.forward_from_message_id
        chat_id = vj.forward_from_chat.username or vj.forward_from_chat.id

    elif vj.text:
        regex = re.compile(
            "(https://)?(t\\.me/|telegram\\.me/|telegram\\.dog/)(c/)?(\\d+|[a-zA-Z_0-9]+)/(\d+)$"
        )
        match = regex.match(vj.text)

        if not match:
            return await vj.reply('Invalid link\n\nTry again /index')

        chat_id = match.group(4)
        last_msg_id = int(match.group(5))

        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)

    else:
        return

    try:
        await bot.get_chat(chat_id)

    except ChannelInvalid:
        return await vj.reply(
            'Private channel. Make me admin first.'
        )

    except (UsernameInvalid, UsernameNotModified):
        return await vj.reply('Invalid link.')

    except Exception as e:
        logger.exception(e)
        return await vj.reply(f'Error - {e}')

    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply(
            'Make sure I am admin in channel.'
        )

    if k.empty:
        return await message.reply(
            'I am not admin in that group/channel.'
        )

    if message.from_user.id in ADMINS:
        buttons = [
            [InlineKeyboardButton(
                'Yes',
                callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}'
            )],
            [InlineKeyboardButton('Close', callback_data='close_data')]
        ]

        return await message.reply(
            f'Index this?\n\nChat: <code>{chat_id}</code>\nMsgID: <code>{last_msg_id}</code>',
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # User request → send to log channel
    if isinstance(chat_id, int):
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Need admin + invite permission.')
    else:
        link = f"@{chat_id}"

    buttons = [
        [InlineKeyboardButton(
            'Accept',
            callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}'
        )],
        [InlineKeyboardButton(
            'Reject',
            callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'
        )]
    ]

    await bot.send_message(
        LOG_CHANNEL,
        f'#IndexRequest\n\nBy: {message.from_user.mention}\n'
        f'Chat: <code>{chat_id}</code>\nMsgID: <code>{last_msg_id}</code>\nLink: {link}',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await message.reply('Request sent for approval.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("Skip must be integer.")

        temp.CURRENT = skip
        await message.reply(f"Skip set to {skip}")
    else:
        await message.reply("Provide skip number.")


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
                    break

                current += 1

                if current % 100 == 0:
                    try:
                        await msg.edit_text(
                            f"Fetched: <code>{current}</code>\nSaved: <code>{total_files}</code>\n"
                            f"Duplicate: <code>{duplicate}</code>\nDeleted: <code>{deleted}</code>\n"
                            f"Skipped: <code>{no_media + unsupported}</code>\nErrors: <code>{errors}</code>",
                            reply_markup=InlineKeyboardMarkup(
                                [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                            )
                        )
                    except MessageNotModified:
                        pass

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

                # ✅ FIXED (IMPORTANT)
                media.file_type = message.media.value
                media.caption = message.caption

                try:
                    aynav, vnay = await save_file(media)
                except Exception as e:
                    errors += 1
                    continue

                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                elif vnay == 2:
                    errors += 1

        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')

        else:
            await msg.edit(
                f'Done ✅\n\nSaved: <code>{total_files}</code>\n'
                f'Duplicate: <code>{duplicate}</code>\n'
                f'Deleted: <code>{deleted}</code>\n'
                f'Skipped: <code>{no_media + unsupported}</code>\n'
                f'Errors: <code>{errors}</code>'
    )
