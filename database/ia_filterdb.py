# OPTIMIZED DB + SEARCH SYSTEM (FAST + QUALITY FIXED)

import re, base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import *

client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

# ⚡ CREATE INDEX (RUN ONCE)
col.create_index("file_name")
sec_col.create_index("file_name")

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

def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    for char in ['[', ']', '(', ')', '{', '}']:
        file_name = file_name.replace(char, '')

    return ' '.join(
        x for x in file_name.split()
        if not x.startswith('@')
        and not x.startswith('http')
        and not x.startswith('www.')
        and not x.startswith('t.me')
    )

def is_file_already_saved(file_id, file_name):
    for collection in [col, sec_col]:
        if collection.find_one({'file_id': file_id}) or collection.find_one({'file_name': file_name}):
            return True
    return False

# 🚀 FIXED SEARCH (QUALITY WORKING) - now uses multi-word regex
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip()
    if not query:
        return [], "", 0

    projection = {"file_id": 1, "file_name": 1, "file_size": 1, "caption": 1}

    # Split query into words and create a regex that matches all words (order ignored)
    words = re.findall(r'\w+', query.lower())
    if words:
        # Build a regex that requires each word to appear somewhere in the filename
        regex_parts = [rf'(?=.*{re.escape(w)})' for w in words]
        regex = ''.join(regex_parts)
        # Example: for query "kgf 1080p", regex becomes (?=.*kgf)(?=.*1080p)
        filter_cond = {"file_name": {"$regex": regex, "$options": "i"}}
    else:
        filter_cond = {"file_name": {"$regex": re.escape(query), "$options": "i"}}

    def fetch(collection):
        return list(collection.find(filter_cond, projection).sort("_id", -1).skip(offset).limit(max_results))

    files = fetch(col)
    if MULTIPLE_DATABASE:
        files += fetch(sec_col)

    total = col.count_documents(filter_cond) + (sec_col.count_documents(filter_cond) if MULTIPLE_DATABASE else 0)
    next_offset = "" if (offset + max_results) >= total else (offset + max_results)

    return files[:max_results], next_offset, total

async def get_bad_files(query, file_type=None, use_filter=False):

    query = query.strip()
    if not query:
        return [], 0

    regex = {"$regex": re.escape(query), "$options": "i"}

    filter_criteria = {'file_name': regex}

    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def fetch(collection):
        return list(collection.find(filter_criteria, {"file_id": 1, "file_name": 1}))

    if MULTIPLE_DATABASE:
        files = fetch(col) + fetch(sec_col)
    else:
        files = fetch(col)

    return files, len(files)

async def get_file_details(query):
    return col.find_one({'file_id': query}) or sec_col.find_one({'file_id': query})

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
