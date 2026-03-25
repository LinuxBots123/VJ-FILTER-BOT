# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN

# First Database
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


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
            print("Database full, enable MULTIPLE_DATABASE")


def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    for char in ['[', ']', '(', ')', '{', '}']:
        file_name = file_name.replace(char, '')

    old_file_name = ' '.join(
        x for x in file_name.split()
        if not x.startswith('@')
        and not x.startswith('http')
        and not x.startswith('www.')
        and not x.startswith('t.me')
    )

    return add_space_between_e_and_number(old_file_name)


def add_space_between_e_and_number(input_string):
    return re.sub(r'(e|E)([0-9])', r'\1 \2', input_string)


def is_file_already_saved(file_id, file_name):
    query_id = {'file_id': file_id}
    query_name = {'file_name': file_name}

    for collection in [col, sec_col]:
        if collection.find_one(query_id) or collection.find_one(query_name):
            return True
    return False


# 🚀 OPTIMIZED SEARCH FUNCTION
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip()

    if not query:
        regex = re.compile(".")
    else:
        # ✅ INDEX-FRIENDLY PREFIX SEARCH
        pattern = f'^{re.escape(query)}'
        regex = re.compile(pattern, re.IGNORECASE)

    filter = {'file_name': regex}

    files = []

    # ✅ Fetch only needed fields (FASTER)
    projection = {"file_id": 1, "file_name": 1, "file_size": 1, "caption": 1}

    if MULTIPLE_DATABASE:
        cursor1 = col.find(filter, projection).sort("_id", -1).skip(offset).limit(max_results)
        cursor2 = sec_col.find(filter, projection).sort("_id", -1).skip(offset).limit(max_results)

        files.extend(list(cursor1))
        files.extend(list(cursor2))

    else:
        cursor = col.find(filter, projection).sort("_id", -1).skip(offset).limit(max_results)
        files = list(cursor)

    total_results = (
        col.count_documents(filter) + sec_col.count_documents(filter)
        if MULTIPLE_DATABASE else col.count_documents(filter)
    )

    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    return files, next_offset, total_results


# ⚡ FAST BAD FILE SEARCH
async def get_bad_files(query, file_type=None, use_filter=False):

    query = query.strip()

    if not query:
        regex = re.compile(".")
    else:
        pattern = f'^{re.escape(query)}'
        regex = re.compile(pattern, re.IGNORECASE)

    filter_criteria = {'file_name': regex}

    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def fetch(collection):
        return list(collection.find(filter_criteria, {"file_id": 1, "file_name": 1}))

    if MULTIPLE_DATABASE:
        files = fetch(col) + fetch(sec_col)
        total = col.count_documents(filter_criteria) + sec_col.count_documents(filter_criteria)
    else:
        files = fetch(col)
        total = col.count_documents(filter_criteria)

    return files, total


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
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
