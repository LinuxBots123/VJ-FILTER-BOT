# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER, MAX_B_TN

# DB CONNECTION
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]


# ✅ SAVE FILE
async def save_file(media):
    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)

    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None
    }

    if is_file_already_saved(file_id, file_name):
        return False, 0

    try:
        col.insert_one(file)
        print(f"{file_name} saved.")
        return True, 1
    except DuplicateKeyError:
        return False, 0


# ✅ CLEAN FILE NAME
def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted = ['[', ']', '(', ')', '{', '}']
    for ch in unwanted:
        file_name = file_name.replace(ch, '')

    return ' '.join(
        filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split())
    )


# ✅ CHECK DUPLICATE
def is_file_already_saved(file_id, file_name):
    if col.find_one({'file_id': file_id}) or col.find_one({'file_name': file_name}):
        return True
    return False


# 🔥🔥🔥 FINAL FIXED SEARCH (SINGLE DB, SCALABLE)
async def get_search_results(*args, file_type=None, max_results=10, offset=0, filter=False):

    # SUPPORT BOTH CALL TYPES
    if len(args) == 2:
        chat_id, query = args
    else:
        query = args[0]

    if isinstance(query, int):
        query = ""

    query = str(query).strip()

    filter_query = {}

    # 🔍 SEARCH FILTER
    if query:
        keywords = query.lower().split()
        filter_query["file_name"] = {
            "$regex": ".*".join(keywords),
            "$options": "i"
        }

    # ✅ TOTAL COUNT
    total = col.count_documents(filter_query)

    # ✅ PROPER PAGINATION (NO DATA LOSS)
    cursor = col.find(filter_query).sort("_id", -1).skip(offset).limit(max_results)
    files = list(cursor)

    next_offset = "" if (offset + max_results) >= total else (offset + max_results)

    return files, next_offset, total


# ✅ REQUIRED FOR APPROVE
async def get_bad_files(query, file_type=None, use_filter=False):

    query = str(query).strip()

    filter_query = {}

    if query:
        keywords = query.lower().split()
        filter_query["file_name"] = {
            "$regex": ".*".join(keywords),
            "$options": "i"
        }

    files = list(col.find(filter_query))

    # REMOVE DUPLICATES
    seen = set()
    unique = []
    for f in files:
        if f['file_id'] not in seen:
            seen.add(f['file_id'])
            unique.append(f)

    # SORT LATEST
    unique = sorted(unique, key=lambda x: x["_id"].generation_time, reverse=True)

    return unique, len(unique)


# ✅ GET FILE DETAILS
async def get_file_details(query):
    return col.find_one({'file_id': query})


# ✅ ENCODE FILE ID
def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


# ✅ DECODE FILE ID
def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    return encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
