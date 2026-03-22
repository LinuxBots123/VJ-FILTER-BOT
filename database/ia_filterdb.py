# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER

# First Database
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]


async def save_file(media):
    """Save file in the database - WITHOUT @VJ_Bots prefix"""
    try:
        file_id = unpack_new_file_id(media.file_id)
        file_name = clean_file_name(media.file_name)
        
        # REMOVED: f"@VJ_Bots {file_name}" - now saving without prefix
        new_file_name = file_name  # Save with cleaned name only, no prefix

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
            print(f"✅ {file_name} is successfully saved.")
            return True, 1
        except DuplicateKeyError:
            print(f"⏭️ {file_name} is already saved.")
            return False, 0
        except Exception as e:
            print(f"❌ Error in first DB: {e}")
            if MULTIPLE_DATABASE:
                try:
                    sec_col.insert_one(file)
                    print(f"✅ {file_name} is successfully saved in second DB.")
                    return True, 1
                except DuplicateKeyError:
                    print(f"⏭️ {file_name} is already saved in second DB.")
                    return False, 0
                except Exception as e2:
                    print(f"❌ Error in second DB: {e2}")
                    return False, 2
            else:
                print("Database Full! Enable MULTIPLE_DATABASE.")
                return False, 2
    except Exception as e:
        print(f"❌ Critical error in save_file: {e}")
        return False, 2


def clean_file_name(file_name):
    if not file_name:
        return "Unknown"
    
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name))
    unwanted_chars = ['[', ']', '(', ')', '{', '}']

    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    # Remove any existing @ mentions but keep the rest of the name
    return ' '.join(
        x for x in file_name.split()
        if not x.startswith('@')
        and not x.startswith('http')
        and not x.startswith('www.')
        and not x.startswith('t.me')
    )


def is_file_already_saved(file_id, file_name):
    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            print(f"⏭️ {file_name} already exists.")
            return True

    return False


# 🔥 FAST SEARCH (FIXED - WITH IMPROVED SEARCH LOGIC)
async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip()

    if not query:
        files = []
        if MULTIPLE_DATABASE:
            cursor1 = col.find().sort('$natural', -1).skip(offset).limit(max_results)
            cursor2 = sec_col.find().sort('$natural', -1).skip(offset).limit(max_results)

            for f in cursor1:
                files.append(f)
            for f in cursor2:
                files.append(f)

            total = col.count_documents({}) + sec_col.count_documents({})
        else:
            cursor = col.find().sort('$natural', -1).skip(offset).limit(max_results)

            for f in cursor:
                files.append(f)

            total = col.count_documents({})

        next_offset = "" if (offset + max_results) >= total else offset + max_results
        return files, next_offset, total

    # 🚀 IMPROVED TEXT SEARCH - FLEXIBLE MATCHING WITH AND LOGIC
    # Split query into keywords
    keywords = query.lower().split()
    
    # Build search string with AND operator for multiple keywords
    # Using quotes for exact word matching but not strict phrase matching
    if len(keywords) == 1:
        # Single keyword - search for the word
        search_string = keywords[0]
    else:
        # Multiple keywords - use AND operator to require all words
        # Format: "word1" "word2" "word3"
        search_string = ' '.join([f'"{kw}"' for kw in keywords])
    
    filter_query = {"$text": {"$search": search_string}}

    files = []

    if MULTIPLE_DATABASE:
        cursor1 = col.find(filter_query, {"score": {"$meta": "textScore"}})\
            .sort([("score", {"$meta": "textScore"})]).skip(offset).limit(max_results)

        cursor2 = sec_col.find(filter_query, {"score": {"$meta": "textScore"}})\
            .sort([("score", {"$meta": "textScore"})]).skip(offset).limit(max_results)

        for f in cursor1:
            files.append(f)
        for f in cursor2:
            files.append(f)

        total = col.count_documents(filter_query) + sec_col.count_documents(filter_query)

    else:
        cursor = col.find(filter_query, {"score": {"$meta": "textScore"}})\
            .sort([("score", {"$meta": "textScore"})]).skip(offset).limit(max_results)

        for f in cursor:
            files.append(f)

        total = col.count_documents(filter_query)

    next_offset = "" if (offset + max_results) >= total else offset + max_results

    return files, next_offset, total


async def get_bad_files(query, file_type=None, use_filter=False):
    query = query.strip()
    regex = re.compile(query, re.IGNORECASE)

    filter_criteria = {'file_name': regex}

    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    files = list(col.find(filter_criteria))
    if MULTIPLE_DATABASE:
        files += list(sec_col.find(filter_criteria))

    return files, len(files)


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
    return encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
