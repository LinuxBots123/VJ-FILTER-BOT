# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client
from typing import Any, Optional
from pyrogram.types import Message
from pyrogram.file_id import FileId

from TechVJ.server.exceptions import FIleNotFound


async def parse_file_id(message: "Message") -> Optional[FileId]:
    media = get_media_from_message(message)

    if media and getattr(media, "file_id", None):
        return FileId.decode(media.file_id)

    return None


async def parse_file_unique_id(message: "Message") -> Optional[str]:
    media = get_media_from_message(message)

    if media:
        return getattr(media, "file_unique_id", None)

    return None


async def get_file_ids(
    client: Client,
    chat_id: int,
    id: int
) -> Optional[FileId]:

    message = await client.get_messages(chat_id, id)

    # Telegram did not return the message
    if not message or message.empty:
        raise FIleNotFound

    media = get_media_from_message(message)

    # Message has no supported media
    if not media:
        raise FIleNotFound

    file_unique_id = await parse_file_unique_id(message)
    file_id = await parse_file_id(message)

    # File ID could not be extracted
    if not file_id or not file_unique_id:
        raise FIleNotFound

    setattr(
        file_id,
        "file_size",
        getattr(media, "file_size", 0)
    )

    setattr(
        file_id,
        "mime_type",
        getattr(media, "mime_type", "")
    )

    setattr(
        file_id,
        "file_name",
        getattr(media, "file_name", "")
    )

    setattr(
        file_id,
        "unique_id",
        file_unique_id
    )

    return file_id


def get_media_from_message(message: "Message") -> Any:
    media_types = (
        "audio",
        "document",
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )

    for attr in media_types:
        media = getattr(message, attr, None)

        if media:
            return media

    return None


def get_hash(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)

    if not media:
        return ""

    return getattr(
        media,
        "file_unique_id",
        ""
    )[:6]


def get_name(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)

    if not media:
        return ""

    return getattr(
        media,
        "file_name",
        ""
    )


def get_media_file_size(m) -> int:
    media = get_media_from_message(m)

    if not media:
        return 0

    return getattr(
        media,
        "file_size",
        0
    )
