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
    except:
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
                return True, 1
            except DuplicateKeyError:
                return False, 0
        else:
            print("Database Full!")


# ✅ CLEAN FILE NAME
def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted_chars = ['[', ']', '(', ')', '{', '}']

    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    return ' '.join(
        filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split())
    )


# ✅ CHECK DUPLICATE
def is_file_already_saved(file_id, file_name):
    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            return True
    return False


# 🔥🔥🔥 FIXED UNIVERSAL SEARCH FUNCTION
async def get_search_results(*args, file_type=None, max_results=10, offset=0, filter=False):

    # ✅ SUPPORT BOTH CALL TYPES
    if len(args) == 2:
        chat_id, query = args
    else:
        query = args[0]

    # 🛡️ FIX ERROR (int → string)
    if isinstance(query, int):
        query = ""

    query = str(query).strip()

    # ✅ SHOW LATEST FILES
    if not query:
        if MULTIPLE_DATABASE:
            files1 = list(col.find({}).sort("_id", -1).skip(offset).limit(max_results))
            files2 = list(sec_col.find({}).sort("_id", -1).skip(offset).limit(max_results))

            files = files1 + files2
            files = sorted(files, key=lambda x: x["_id"], reverse=True)[:max_results]

            total_results = col.estimated_document_count() + sec_col.estimated_document_count()
        else:
            files = list(col.find({}).sort("_id", -1).skip(offset).limit(max_results))
            total_results = col.estimated_document_count()

        next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
        return files, next_offset, total_results

    # ✅ TEXT SEARCH
    keywords = query.lower().split()
    text_query = ' '.join([f'"{kw}"' for kw in keywords])

    if MULTIPLE_DATABASE:
        files = list(col.find({'$text': {'$search': text_query}})) + \
                list(sec_col.find({'$text': {'$search': text_query}}))

        files = sorted(files, key=lambda x: x["_id"], reverse=True)[:max_results]

        total_results = col.count_documents({'$text': {'$search': text_query}}) + \
                        sec_col.count_documents({'$text': {'$search': text_query}})
    else:
        files = list(col.find({'$text': {'$search': text_query}}))

        files = sorted(files, key=lambda x: x["_id"], reverse=True)[:max_results]

        total_results = col.count_documents({'$text': {'$search': text_query}})

    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    return files, next_offset, total_results


# ✅ REQUIRED FOR APPROVE PLUGIN
async def get_bad_files(query, file_type=None, use_filter=False):

    query = str(query).strip()

    if not query:
        if MULTIPLE_DATABASE:
            files = list(col.find({}).sort("_id", -1)) + list(sec_col.find({}).sort("_id", -1))
        else:
            files = list(col.find({}).sort("_id", -1))

        return files, len(files)

    keywords = query.lower().split()
    text_query = ' '.join([f'"{kw}"' for kw in keywords])

    if MULTIPLE_DATABASE:
        files = list(col.find({'$text': {'$search': text_query}})) + \
                list(sec_col.find({'$text': {'$search': text_query}}))
    else:
        files = list(col.find({'$text': {'$search': text_query}}))

    seen = set()
    unique_files = []
    for f in files:
        if f['file_id'] not in seen:
            seen.add(f['file_id'])
            unique_files.append(f)

    unique_files = sorted(unique_files, key=lambda x: x["_id"], reverse=True)

    return unique_files, len(unique_files)


# ✅ GET FILE DETAILS
async def get_file_details(query):
    result = col.find_one({'file_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'file_id': query})
    return result


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
