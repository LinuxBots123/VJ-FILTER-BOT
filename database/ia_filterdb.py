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
    """Save file in the database."""

    file_id = unpack_new_file_id(media.file_id)

    # 🔥 CLEAN FILE NAME
    file_name = clean_file_name(media.file_name)

    # 🔥 CLEAN CAPTION
    caption = None
    if media.caption:
        caption = re.sub(r'@\w+', '', str(media.caption), flags=re.IGNORECASE).strip()

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
        print(f"{file_name} is successfully saved.")
        return True, 1

    except DuplicateKeyError:
        print(f"{file_name} is already saved.")
        return False, 0

    except:
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
                print(f"{file_name} is successfully saved.")
                return True, 1

            except DuplicateKeyError:
                print(f"{file_name} is already saved.")
                return False, 0
        else:
            print("Database full, enable MULTIPLE_DATABASE.")


def clean_file_name(file_name):
    """Clean and format the file name."""

    file_name = str(file_name)

    # 🔥 REMOVE @tags
    file_name = re.sub(r'@\w+', '', file_name, flags=re.IGNORECASE)

    # Existing cleaning
    file_name = re.sub(r"(_|\-|\.|\+)", " ", file_name)

    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    # Remove links & leftover junk
    file_name = ' '.join(
        filter(
            lambda x: not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'),
            file_name.split()
        )
    )

    return file_name.strip()


def is_file_already_saved(file_id, file_name):
    """Check if file exists."""

    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            print(f"{file_name} is already saved.")
            return True

    return False


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):

    query = query.strip()

    if not query:
        filter_criteria = {}

        if MULTIPLE_DATABASE:
            cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)

            files = list(cursor1) + list(cursor2)
            total_results = col.estimated_document_count() + sec_col.estimated_document_count()

        else:
            cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            files = list(cursor)
            total_results = col.estimated_document_count()

        next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
        return files, next_offset, total_results

    keywords = query.lower().split()
    text_query = ' '.join([f'"{kw}"' for kw in keywords])

    if MULTIPLE_DATABASE:
        cursor1 = col.find(
            {'$text': {'$search': text_query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).skip(offset).limit(max_results)

        cursor2 = sec_col.find(
            {'$text': {'$search': text_query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).skip(offset).limit(max_results)

        files = list(cursor1) + list(cursor2)

        total_results = col.count_documents({'$text': {'$search': text_query}}) + \
                        sec_col.count_documents({'$text': {'$search': text_query}})

    else:
        cursor = col.find(
            {'$text': {'$search': text_query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).skip(offset).limit(max_results)

        files = list(cursor)
        total_results = col.count_documents({'$text': {'$search': text_query}})

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
    text_query = ' '.join([f'"{kw}"' for kw in keywords])

    if MULTIPLE_DATABASE:
        files = list(col.find({'$text': {'$search': text_query}})) + \
                list(sec_col.find({'$text': {'$search': text_query}}))

        total_results = col.count_documents({'$text': {'$search': text_query}}) + \
                        sec_col.count_documents({'$text': {'$search': text_query}})

    else:
        files = list(col.find({'$text': {'$search': text_query}}))
        total_results = col.count_documents({'$text': {'$search': text_query}})

    return files, total_results


async def get_file_details(query):
    result = col.find_one({'file_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'file_id': query}
)
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
