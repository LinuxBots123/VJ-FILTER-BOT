import re, base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE

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

    caption = None
    if media.caption:
        caption = re.sub(r'@\w+|\bMNTGX\b', '', str(media.caption), flags=re.IGNORECASE).strip()

    file = {
        'file_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': caption
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
    file_name = str(file_name)

    file_name = re.sub(r'@\w+|\bMNTGX\b', '', file_name, flags=re.IGNORECASE)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", file_name)

    for char in ['[', ']', '(', ')', '{', '}']:
        file_name = file_name.replace(char, '')

    file_name = ' '.join(
        filter(
            lambda x: not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'),
            file_name.split()
        )
    )

    return file_name.strip()


def is_file_already_saved(file_id, file_name):
    for collection in [col, sec_col]:
        if collection.find_one({'file_id': file_id}) or collection.find_one({'file_name': file_name}):
            return True
    return False


# ✅ MAIN SEARCH FIX (OPTIMIZED)
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip().lower()

    # Projection for faster response
    projection = {
        'file_id': 1,
        'file_name': 1,
        'file_size': 1,
        'caption': 1,
        '_id': 0
    }

    if not query:
        cursor = col.find({}, projection).sort('_id', -1).skip(offset).limit(max_results)
        files = list(cursor)
        total_results = col.count_documents({})
        next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
        return files, next_offset, total_results

    # Normalize S/E
    query = re.sub(r'\bs(\d{1})\b', r's0\1', query)
    query = re.sub(r'\be(\d{1})\b', r'e0\1', query)

    keywords = query.split()

    # Faster AND-based regex (index friendly)
    search_filter = {
        '$and': [
            {'file_name': {'$regex': re.escape(k), '$options': 'i'}}
            for k in keywords
        ]
    }

    if MULTIPLE_DATABASE:
        import asyncio

        async def fetch(cursor):
            return list(cursor)

        cursor1 = col.find(search_filter, projection).sort('_id', -1).skip(offset).limit(max_results)
        cursor2 = sec_col.find(search_filter, projection).sort('_id', -1).skip(offset).limit(max_results)

        files1, files2 = await asyncio.gather(
            fetch(cursor1),
            fetch(cursor2)
        )

        files = files1 + files2

        total_results = col.count_documents(search_filter) + sec_col.count_documents(search_filter)

    else:
        cursor = col.find(search_filter, projection).sort('_id', -1).skip(offset).limit(max_results)
        files = list(cursor)
        total_results = col.count_documents(search_filter)

    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    return files, next_offset, total_results


# ✅ FIXED (RESTORED FUNCTION + OPTIMIZED)
async def get_bad_files(query, file_type=None, use_filter=False):

    query = query.strip().lower()

    if not query:
        if MULTIPLE_DATABASE:
            files = list(col.find({}, {'_id': 0})) + list(sec_col.find({}, {'_id': 0}))
            total_results = col.count_documents({}) + sec_col.count_documents({})
        else:
            files = list(col.find({}, {'_id': 0}))
            total_results = col.count_documents({})
        return files, total_results

    query = re.sub(r'\bs(\d{1})\b', r's0\1', query)
    query = re.sub(r'\be(\d{1})\b', r'e0\1', query)

    keywords = query.split()

    search_filter = {
        '$and': [
            {'file_name': {'$regex': re.escape(k), '$options': 'i'}}
            for k in keywords
        ]
    }

    projection = {
        'file_id': 1,
        'file_name': 1,
        'file_size': 1,
        'caption': 1,
        '_id': 0
    }

    if MULTIPLE_DATABASE:
        files = list(col.find(search_filter, projection)) + list(sec_col.find(search_filter, projection))
        total_results = col.count_documents(search_filter) + sec_col.count_documents(search_filter)
    else:
        files = list(col.find(search_filter, projection))
        total_results = col.count_documents(search_filter)

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
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id
