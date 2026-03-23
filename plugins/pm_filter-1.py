# Don't Remove Credit @VJ_Bots
# Fixed IMDb + Spell Check (Ready to Upload)

import re
from pyrogram import Client, filters
from fuzzywuzzy import process
from IMDBKit import IMDB

imdb = IMDB()

# ---------------- SPELL CHECK ---------------- #

def spell_check(query, movie_list):
    try:
        match = process.extractOne(query, movie_list)
        if match:
            return match[0]
        return query
    except Exception as e:
        print("Spell Check Error:", e)
        return query

# ---------------- IMDb FUNCTION ---------------- #

async def get_imdb_details(query):
    try:
        data = await imdb.search(query)
        if not data:
            return None

        movie = data[0]

        return {
            "title": movie.get("title"),
            "year": movie.get("year"),
            "rating": movie.get("rating"),
            "poster": movie.get("poster"),
            "plot": movie.get("plot"),
        }

    except Exception as e:
        print("IMDb Error:", e)
        return None

# ---------------- MAIN FILTER ---------------- #

@Client.on_message(filters.private & filters.text)
async def pm_filter(client, message):

    search = message.text.strip()

    # 🔹 FETCH FILES FROM DB (EDIT THIS IF YOUR COLLECTION NAME IS DIFFERENT)
    files = []
    async for file in client.db.files.find({}):
        files.append(file)

    # 🔹 CREATE MOVIE LIST FOR SPELL CHECK
    movie_list = [file.get("file_name", "") for file in files if file.get("file_name")]

    # 🔹 APPLY SPELL CHECK
    search = spell_check(search, movie_list)

    # 🔹 SEARCH FILES
    results = []
    for file in files:
        name = file.get("file_name", "")
        if search.lower() in name.lower():
            results.append(file)

    if not results:
        return await message.reply_text("❌ No files found.")

    # 🔹 IMDb DATA
    imdb_data = await get_imdb_details(search)

    if imdb_data:
        caption = f"""🎬 **{imdb_data['title']} ({imdb_data['year']})**
⭐ Rating: {imdb_data['rating']}

📝 {imdb_data['plot']}
"""
        poster = imdb_data['poster']
    else:
        caption = f"Results for: {search}"
        poster = None

    # 🔹 SEND RESPONSE
    if poster:
        await message.reply_photo(photo=poster, caption=caption)
    else:
        await message.reply_text(caption)

    # 🔹 SEND FILE LIST (LIMIT 10)
    for file in results[:10]:
        await message.reply_text(file.get("file_name", "Unknown File"))
