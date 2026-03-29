# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ

import re, base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE

# ------------------ DATABASE ------------------
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


# ------------------ CLEAN FILE NAME ------------------
def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))

    for ch in ['[', ']', '(', ')', '{', '}']:
        file_name = file_name.replace(ch, '')

    return ' '.join(
        filter(lambda x: not x.startswith('@') and not x.startswith('http'), file_name.split())
    )


# ------------------ SAVE FILE ------------------
async def save_file(media):
    file_id = unpack_new_file_id(media.file_id)
    file_name = clean_file_name(media.file_name)

    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': media.caption.html if media.caption else None
    }

    try:
        col.insert_one(file)
        return True, 1
    except DuplicateKeyError:
        return False, 0


# ------------------ QUERY CLEAN ------------------
def normalize_query(query):
    query = query.lower()

    remove_words = [
        "movie", "full", "film", "cinema",
        "hd", "hdrip", "webrip", "bluray"
    ]

    words = query.split()
    words = [w for w in words if w not in remove_words]

    return " ".join(words).strip()


# ------------------ 🔥 MAIN SEARCH ------------------
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = normalize_query(query)

    if not query:
        cursor = col.find({}).sort('_id', -1).skip(offset).limit(max_results)
        files = list(cursor)
        total = col.estimated_document_count()
        next_offset = "" if (offset + max_results) >= total else (offset + max_results)
        return files, next_offset, total

    keywords = query.split()

    # 🔥 STRICT AND SEARCH
    regex = "".join([f"(?=.*{re.escape(k)})" for k in keywords])

    filter_criteria = {
        "file_name": {
            "$regex": regex,
            "$options": "i"
        }
    }

    cursor = col.find(filter_criteria).sort('_id', -1).skip(offset).limit(max_results)
    files = list(cursor)

    total = col.count_documents(filter_criteria)
    next_offset = "" if (offset + max_results) >= total else (offset + max_results)

    return files, next_offset, total


# ------------------ 🔥 REQUIRED FIX ------------------
async def get_bad_files(query, file_type=None, use_filter=False):

    query = normalize_query(query)

    if not query:
        files = list(col.find({}))
        total = col.estimated_document_count()
        return files, total

    keywords = query.split()

    regex = "".join([f"(?=.*{re.escape(k)})" for k in keywords])

    filter_criteria = {
        "file_name": {
            "$regex": regex,
            "$options": "i"
        }
    }

    files = list(col.find(filter_criteria))
    total = col.count_documents(filter_criteria)

    return files, total


# ------------------ FILE DETAILS ------------------
async def get_file_details(query):
    result = col.find_one({'file_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'file_id': query})
    return result


# ------------------ FILE ID ------------------
def encode_file_id(s: bytes) -> str:
    return base64.urlsafe_b64encode(s).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    return encode_file_id(
        pack("<iiqq",
             int(decoded.file_type),
             decoded.dc_id,
             decoded.media_id,
             decoded.access_hash)
    )
