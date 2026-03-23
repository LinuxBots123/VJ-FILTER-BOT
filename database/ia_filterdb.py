# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN

client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

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
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id, file_name):
    for collection in [col, sec_col]:
        if collection.find_one({'file_name': file_name}) or collection.find_one({'file_id': file_id}):
            return True
    return False

# 🔥 FIXED SEARCH
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip()

    if not query:
        if MULTIPLE_DATABASE:
            files = list(col.find().sort('$natural', -1).skip(offset).limit(max_results)) + \
                    list(sec_col.find().sort('$natural', -1).skip(offset).limit(max_results))
            total_results = col.estimated_document_count() + sec_col.estimated_document_count()
        else:
            files = list(col.find().sort('$natural', -1).skip(offset).limit(max_results))
            total_results = col.estimated_document_count()

        next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
        return files, next_offset, total_results

    keywords = query.lower().split()
    regex_pattern = ".*".join(keywords)

    search_query = {
        'file_name': {
            '$regex': regex_pattern,
            '$options': 'i'
        }
    }

    if MULTIPLE_DATABASE:
        files = list(col.find(search_query).skip(offset).limit(max_results)) + \
                list(sec_col.find(search_query).skip(offset).limit(max_results))
        total_results = col.count_documents(search_query) + sec_col.count_documents(search_query)
    else:
        files = list(col.find(search_query).skip(offset).limit(max_results))
        total_results = col.count_documents(search_query)

    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    return files, next_offset, total_results


async def get_bad_files(query, file_type=None, use_filter=False):
    query = query.strip()

    if not query:
        if MULTIPLE_DATABASE:
            files = list(col.find({})) + list(sec_col.find({}))
            total_results = col.estimated_document_count() + sec_col.estimated_document_count()
        else:
            files = list(col.find({}))
            total_results = col.estimated_document_count()
        return files, total_results

    keywords = query.lower().split()
    regex_pattern = ".*".join(keywords)

    search_query = {
        'file_name': {
            '$regex': regex_pattern,
            '$options': 'i'
        }
    }

    if MULTIPLE_DATABASE:
        files = list(col.find(search_query)) + list(sec_col.find(search_query))
        total_results = col.count_documents(search_query) + sec_col.count_documents(search_query)
    else:
        files = list(col.find(search_query))
        total_results = col.count_documents(search_query)

    return files, total_results


async def get_file_details(query):
    result = col.find_one({'file_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'file_id': query})
    return result


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
    file_id = encode_file_id(
        pack("<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id
