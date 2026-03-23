# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN

# First Database For File Saving 
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database For File Saving
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

# 🔥 CACHE (speed boost)
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
        else:
            print("Database full")

def clean_file_name(file_name):
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name)) 
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
        
    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id, file_name):
    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            return True
    return False


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    query = query.strip().lower()
    words = query.split()

    if query in CACHE:
        return CACHE[query]

    if not query:
        search_filter = {}
    else:
        search_filter = {"$text": {"$search": query}}

    files = []

    def match_all_words(name):
        name = name.lower()
        return all(word in name for word in words)

    try:
        if MULTIPLE_DATABASE:
            cursor1 = col.find(search_filter).skip(offset).limit(50)
            cursor2 = sec_col.find(search_filter).skip(offset).limit(50)

            for file in cursor1:
                if match_all_words(file['file_name']):
                    files.append(file)

            for file in cursor2:
                if match_all_words(file['file_name']):
                    files.append(file)

        else:
            cursor = col.find(search_filter).skip(offset).limit(50)

            for file in cursor:
                if match_all_words(file['file_name']):
                    files.append(file)

    except:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
        regex = re.compile(raw_pattern, re.IGNORECASE)
        fallback_filter = {'file_name': regex}

        if MULTIPLE_DATABASE:
            for file in col.find(fallback_filter).skip(offset).limit(50):
                if match_all_words(file['file_name']):
                    files.append(file)
            for file in sec_col.find(fallback_filter).skip(offset).limit(50):
                if match_all_words(file['file_name']):
                    files.append(file)
        else:
            for file in col.find(fallback_filter).skip(offset).limit(50):
                if match_all_words(file['file_name']):
                    files.append(file)

    files = files[:max_results]

    total_results = len(files)
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    result = (files, next_offset, total_results)
    CACHE[query] = result

    return result


async def get_bad_files(query, file_type=None, use_filter=False):
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = rf'(\b|[.+-_]){query}(\b|[.+-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[s.+-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], 0

    filter_criteria = {'file_name': regex}
    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def count_documents(collection):
        return collection.count_documents(filter_criteria)

    total_results = (count_documents(col) + count_documents(sec_col) if MULTIPLE_DATABASE else count_documents(col))

    def find_documents(collection):
        return list(collection.find(filter_criteria))

    files = (find_documents(col) + find_documents(sec_col) if MULTIPLE_DATABASE else find_documents(col))

    return files, total_results


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
