# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER

client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

CACHE = {}

async def save_file(media):
    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)
    new_file_name = f"@VJ_Bots {file_name}"

    file = {
        'file_id': file_id,
        'file_name': new_file_name,
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
    for c in ['[', ']', '(', ')', '{', '}']:
        file_name = file_name.replace(c, '')
    return ' '.join(file_name.split())

def is_file_already_saved(file_id, file_name):
    for collection in [col, sec_col]:
        if collection.find_one({'file_id': file_id}) or collection.find_one({'file_name': file_name}):
            return True
    return False


# 🚀 FINAL FIXED SEARCH (WORKS FOR QUALITY CLICK)
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip().lower()

    if query in CACHE:
        return CACHE[query]

    words = query.split()
    main_word = words[0] if words else ""

    # 🔥 REGEX (better than text search)
    raw_pattern = query.replace(' ', r'.*')
    regex = re.compile(raw_pattern, re.IGNORECASE)

    files = []

    def match(name):
        name = name.lower()

        # must contain movie name
        if main_word and main_word not in name:
            return False

        return True

    if MULTIPLE_DATABASE:
        cursor1 = col.find({'file_name': regex}).skip(offset).limit(50)
        cursor2 = sec_col.find({'file_name': regex}).skip(offset).limit(50)

        for file in cursor1:
            if match(file['file_name']):
                files.append(file)

        for file in cursor2:
            if match(file['file_name']):
                files.append(file)

    else:
        cursor = col.find({'file_name': regex}).skip(offset).limit(50)

        for file in cursor:
            if match(file['file_name']):
                files.append(file)

    files = files[:max_results]

    total_results = len(files)
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    result = (files, next_offset, total_results)
    CACHE[query] = result

    return result


async def get_bad_files(query, file_type=None, use_filter=False):
    regex = re.compile(query.replace(' ', r'.*'), re.IGNORECASE)

    files = list(col.find({'file_name': regex}))
    if MULTIPLE_DATABASE:
        files += list(sec_col.find({'file_name': regex}))

    return files, len(files)


async def get_file_details(query):
    return col.find_one({'file_id': query}) or sec_col.find_one({'file_id': query})


def encode_file_id(s: bytes) -> str:
    r = b""; n = 0
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
    return encode_file_id(pack("<iiqq",
        int(decoded.file_type),
        decoded.dc_id,
        decoded.media_id,
        decoded.access_hash
    ))
