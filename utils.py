import logging, asyncio, os, re, random, pytz, aiohttp, requests, string, json, http.client
from info import *
from imdb import IMDB 
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

imdb = IMDB()

# ---------------- FIXED IMDB FUNCTION ---------------- #

async def get_poster(query, bulk=False, id=False, file=None):
    try:
        if not id:
            data = await imdb.search(query)
            if not data:
                return None
            movie = data[0]
        else:
            movie = await imdb.get_by_id(query)
            if not movie:
                return None

        plot = movie.get("plot") or "No description available"
        if plot and len(plot) > 800:
            plot = plot[:800] + "..."

        return {
            'title': movie.get('title'),
            'votes': "N/A",
            "aka": "N/A",
            "seasons": "N/A",
            "box_office": "N/A",
            'localized_title': movie.get('title'),
            'kind': "movie",
            "imdb_id": movie.get("id"),
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
            'release_date': movie.get('year'),
            'year': movie.get('year'),
            'genres': "N/A",
            'poster': movie.get('poster'),
            'plot': plot,
            'rating': str(movie.get("rating")),
            'url': movie.get("url")
        }

    except Exception as e:
        logger.error(f"IMDb Error: {e}")
        return None
