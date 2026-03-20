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
            f'Your Submission for indexing {chat} has been decliened by our moderators.',
            reply_to_message_id=int(lst_msg_id)
        )
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('Processing...⏳', show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',
            reply_to_message_id=int(lst_msg_id)
        )
    await msg.edit(
        "Starting Indexing",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command('index'))
async def send_for_index(bot, message):
    # Fix: Use message instead of vj for consistent variable naming
    ask_msg = await bot.ask(
        message.chat.id, 
        "**Now Send Me Your Channel Last Post Link Or Forward A Last Message From Your Index Channel.\n\nAnd You Can Set Skip Number By - /setskip yourskipnumber**",
        timeout=60  # Add timeout to prevent hanging
    )
    
    if not ask_msg:
        return await message.reply("**Timeout! Please try again.**")
    
    # Check if it's a forwarded message from channel
    if ask_msg.forward_from_chat and ask_msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = ask_msg.forward_from_message_id
        chat_id = ask_msg.forward_from_chat.username or ask_msg.forward_from_chat.id
        chat_title = ask_msg.forward_from_chat.title
        
    # Check if it's a text link
    elif ask_msg.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(ask_msg.text)
        if not match:
            return await ask_msg.reply('❌ **Invalid link**\n\nPlease send a valid channel link or forward a message from the channel.\n\nExample: https://t.me/yourchannel/100')
        
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        
        # Convert to proper chat ID format
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
        chat_title = chat_id
    else:
        return await ask_msg.reply('❌ **Invalid input**\n\nPlease send a valid channel link or forward a message from the channel.')

    # Verify bot is admin in the channel
    try:
        chat = await bot.get_chat(chat_id)
        chat_title = chat.title
    except ChannelInvalid:
        return await ask_msg.reply('❌ **Channel Invalid**\n\nMake sure:\n1. The channel exists\n2. I am an admin in that channel')
    except Exception as e:
        logger.exception(e)
        return await ask_msg.reply(f'❌ **Error:** {e}')

    # Check if message exists
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
        if k.empty:
            return await ask_msg.reply('❌ **Message not found**\n\nMake sure the message ID is correct and I have access to it.')
    except Exception as e:
        return await ask_msg.reply(f'❌ **Error accessing message:** {e}')

    # If user is admin, ask directly
    if message.from_user.id in ADMINS:
        buttons = [[
            InlineKeyboardButton('✅ Yes, Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],[
            InlineKeyboardButton('❌ Cancel', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'📁 **Channel:** {chat_title}\n'
            f'📊 **Total Messages:** {last_msg_id}\n\n'
            f'Do you want to index this channel?',
            reply_markup=reply_markup
        )

    # For non-admin users, send request to log channel
    try:
        if type(chat_id) is int:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        else:
            link = f"https://t.me/{chat_id}"
    except ChatAdminRequired:
        return await message.reply('❌ I need to be admin in the channel to create invite links.')

    buttons = [[
        InlineKeyboardButton('✅ Accept', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}'),
        InlineKeyboardButton('❌ Reject', callback_data=f'index#reject#{chat_id}#{ask_msg.id}#{message.from_user.id}')
    ]]
    
    await bot.send_message(
        LOG_CHANNEL,
        f"#IndexRequest\n\n"
        f"**From:** {message.from_user.mention} (`{message.from_user.id}`)\n"
        f"**Channel:** {chat_title}\n"
        f"**Chat ID:** `{chat_id}`\n"
        f"**Last Message:** `{last_msg_id}`\n"
        f"**Invite Link:** {link}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    await message.reply('✅ **Request Sent!**\n\nYour indexing request has been sent to admins. They will review and start indexing soon.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("❌ Skip number should be an integer.")
        await message.reply(f"✅ Successfully set SKIP number as {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply("❌ Give me a skip number\n\nExample: `/setskip 100`")


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
            
            await msg.edit("🔄 **Starting Indexing...**")
            
            async for message in bot.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
                    await msg.edit(f"❌ **Cancelled!**\n\n"
                                   f"✅ Saved: {total_files}\n"
                                   f"⏭️ Duplicate: {duplicate}\n"
                                   f"🗑️ Deleted: {deleted}\n"
                                   f"📝 No Media: {no_media}\n"
                                   f"❌ Unsupported: {unsupported}\n"
                                   f"⚠️ Errors: {errors}")
                    break
                
                current += 1
                
                # Update progress every 50 messages
                if current % 50 == 0:
                    try:
                        await msg.edit_text(
                            text=f"🔄 **Indexing Progress**\n\n"
                                 f"📊 **Fetched:** {current}\n"
                                 f"✅ **Saved:** {total_files}\n"
                                 f"⏭️ **Duplicate:** {duplicate}\n"
                                 f"🗑️ **Deleted:** {deleted}\n"
                                 f"📝 **No Media:** {no_media}\n"
                                 f"❌ **Unsupported:** {unsupported}\n"
                                 f"⚠️ **Errors:** {errors}",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton('❌ Cancel', callback_data='index_cancel')
                            ]])
                        )
                    except MessageNotModified:
                        pass
                
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
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
                elif vnay == 2:
                    errors += 1
                    
        except FloodWait as e:
            logger.warning(f"FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.exception(e)
            await msg.edit(f"❌ **Error:** {str(e)[:100]}")
        else:
            status = "✅ **Completed!**" if not temp.CANCEL else "❌ **Cancelled!**"
            await msg.edit(f"{status}\n\n"
                          f"✅ Saved: {total_files}\n"
                          f"⏭️ Duplicate: {duplicate}\n"
                          f"🗑️ Deleted: {deleted}\n"
                          f"📝 No Media: {no_media}\n"
                          f"❌ Unsupported: {unsupported}\n"
                          f"⚠️ Errors: {errors}")
