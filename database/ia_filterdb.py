# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from datetime import datetime
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN

# DB CONNECTION
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


# SAVE FILE
async def save_file(media):
    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)

    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None,
        'created_at': datetime.utcnow()
    }

    if is_file_already_saved(file_id, file_name):
        return False, 0

    try:
        col.insert_one(file)
        return True, 1
    except DuplicateKeyError:
        return False, 0
    except:
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
                return True, 1
            except DuplicateKeyError:
                return False, 0
        else:
            print("Database Full!")


# CLEAN NAME
def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted = ['[', ']', '(', ')', '{', '}']
    for ch in unwanted:
        file_name = file_name.replace(ch, '')

    return ' '.join(
        filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split())
    )


# DUPLICATE CHECK
def is_file_already_saved(file_id, file_name):
    for collection in [col, sec_col]:
        if collection.find_one({'file_id': file_id}) or collection.find_one({'file_name': file_name}):
            return True
    return False


# 🔥🔥🔥 FINAL REAL-TIME SEARCH ENGINE
async def get_search_results(*args, file_type=None, max_results=10, offset=0, filter=False):

    # SUPPORT BOTH CALLS
    if len(args) == 2:
        chat_id, query = args
    else:
        query = args[0]

    if isinstance(query, int):
        query = ""

    query = str(query).strip().lower()

    # ✅ FETCH ALL FILES
    if MULTIPLE_DATABASE:
        all_files = list(col.find({})) + list(sec_col.find({}))
    else:
        all_files = list(col.find({}))

    # 🔥 SORT BY TIME (PERFECT SYNC)
    all_files = sorted(
        all_files,
        key=lambda x: x.get("created_at", x["_id"].generation_time),
        reverse=True
    )

    # 🔍 FILTER SEARCH
    if query:
        keywords = query.split()
        filtered = []

        for file in all_files:
            name = file.get("file_name", "").lower()
            if all(k in name for k in keywords):
                filtered.append(file)

        all_files = filtered

    total_results = len(all_files)

    # 📄 PAGINATION AFTER MERGE
    files = all_files[offset: offset + max_results]

    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    return files, next_offset, total_results


# APPROVE SYSTEM
async def get_bad_files(query, file_type=None, use_filter=False):

    query = str(query).strip().lower()

    if MULTIPLE_DATABASE:
        files = list(col.find({})) + list(sec_col.find({}))
    else:
        files = list(col.find({}))

    files = sorted(
        files,
        key=lambda x: x.get("created_at", x["_id"].generation_time),
        reverse=True
    )

    if query:
        keywords = query.split()
        files = [f for f in files if all(k in f.get("file_name", "").lower() for k in keywords)]

    # REMOVE DUPLICATES
    seen = set()
    unique = []
    for f in files:
        if f['file_id'] not in seen:
            seen.add(f['file_id'])
            unique.append(f)

    return unique, len(unique)


# FILE DETAILS
async def get_file_details(query):
    result = col.find_one({'file_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'file_id': query})
    return result


# ENCODE
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


# DECODE
def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    return encode_file_id(
        pack("<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
