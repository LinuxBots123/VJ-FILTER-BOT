import logging, asyncio, os, re, random, pytz, aiohttp, requests, string, json, http.client
from info import *
from imdbkit import IMDBKit
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from pyrogram.errors import *
from typing import Union, List
from Script import script
from datetime import datetime, date
from database.users_chats_db import db
from database.join_reqs import JoinReqs
from bs4 import BeautifulSoup
from shortzy import Shortzy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

join_db = JoinReqs
imdb = IMDBKit()

# ---------------- FIXED IMDB FUNCTION ---------------- #

async def get_poster(query, bulk=False, id=False, file=None):
    try:
        if not id:
            results = imdb.search_movie(query)

            if not results or not results.titles:
                return None

            movie_data = results.titles[0]
            imdb_id = movie_data.imdbId.replace("tt", "")

            movie = imdb.get_movie(imdb_id)
        else:
            imdb_id = query.replace("tt", "")
            movie = imdb.get_movie(imdb_id)

        if not movie:
            return None

        plot = movie.plot or "No description available"
        if plot and len(plot) > 800:
            plot = plot[:800] + "..."

        return {
            'title': movie.title,
            'votes': "N/A",
            "aka": "N/A",
            "seasons": "N/A",
            "box_office": "N/A",
            'localized_title': movie.title,
            'kind': "movie",
            "imdb_id": f"tt{movie.imdbId}",
            "cast": "N/A",
            "runtime": "N/A",
            "countries": "N/A",
            "certificates": "N/A",
            "languages": "N/A",
            "director": "N/A",
            "writer": "N/A",
            "producer": "N/A",
            "composer": "N/A",
            "cinematographer": "N/A",
            "music_team": "N/A",
            "distributors": "N/A",
            'release_date': movie.year,
            'year': movie.year,
            'genres': ", ".join(movie.genres) if movie.genres else "N/A",
            'poster': movie.image,
            'plot': plot,
            'rating': str(movie.rating) if movie.rating else "N/A",
            'url': f"https://www.imdb.com/title/tt{movie.imdbId}"
        }

    except Exception as e:
        logger.error(f"IMDb Error: {e}")
        return None


# ---------------- REST OF YOUR ORIGINAL CODE ---------------- #

async def pub_is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append(
                [InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)]
            )
        except Exception:
            pass
    return btn


async def is_subscribed(bot, query):
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    except:
        return False


def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    else:
        return ', '.join(str(i) for i in k)


def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'
