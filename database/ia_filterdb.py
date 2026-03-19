# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
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
        'caption': media.caption.html if media.caption else None
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


# 🔥🔥🔥 FINAL PRODUCTION SEARCH FUNCTION
async def get_search_results(*args, file_type=None, max_results=10, offset=0, filter=False):

    # HANDLE BOTH CALLS
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
    if MULTIPLE_DATABASE:
        total = col.count_documents(filter_query) + sec_col.count_documents(filter_query)
    else:
        total = col.count_documents(filter_query)

    # 🔥 FETCH EXTRA (IMPORTANT FOR MERGE)
    fetch_limit = offset + max_results + 20

    if MULTIPLE_DATABASE:
        files1 = list(
            col.find(filter_query)
            .sort("_id", -1)
            .limit(fetch_limit)
        )

        files2 = list(
            sec_col.find(filter_query)
            .sort("_id", -1)
            .limit(fetch_limit)
        )

        merged = files1 + files2

        # 🔥 CORRECT SORT (TIME BASED)
        merged = sorted(
            merged,
            key=lambda x: x["_id"].generation_time,
            reverse=True
        )

    else:
        merged = list(
            col.find(filter_query)
            .sort("_id", -1)
            .limit(fetch_limit)
        )

    # ✅ PAGINATION AFTER MERGE
    files = merged[offset: offset + max_results]

    next_offset = "" if (offset + max_results) >= total else (offset + max_results)

    return files, next_offset, total


# APPROVE SYSTEM
async def get_bad_files(query, file_type=None, use_filter=False):

    query = str(query).strip()

    filter_query = {}

    if query:
        keywords = query.lower().split()
        filter_query["file_name"] = {
            "$regex": ".*".join(keywords),
            "$options": "i"
        }

    if MULTIPLE_DATABASE:
        files = list(col.find(filter_query)) + list(sec_col.find(filter_query))
    else:
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
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
