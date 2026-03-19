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

# Second Database - Always define it, even if MULTIPLE_DATABASE is False
sec_client = None
sec_db = None
sec_col = None

if MULTIPLE_DATABASE and SEC_FILE_DB_URI:
    try:
        sec_client = MongoClient(SEC_FILE_DB_URI)
        sec_db = sec_client[DATABASE_NAME]
        sec_col = sec_db[COLLECTION_NAME]
    except:
        print("⚠️ Second database connection failed, continuing with single database")
        sec_col = None

async def save_file(media):
    """Save file in the database."""
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
        print(f"{file_name} is successfully saved.")
        return True, 1
    except DuplicateKeyError:
        print(f"{file_name} is already saved.")
        return False, 0
    except Exception as e:
        # If first DB fails and multiple DB is enabled, try second
        if MULTIPLE_DATABASE and sec_col is not None:
            try:
                sec_col.insert_one(file)
                print(f"{file_name} is successfully saved in second database.")
                return True, 1
            except DuplicateKeyError:
                print(f"{file_name} is already saved in second database.")
                return False, 0
            except Exception as e2:
                print(f"Error saving to second database: {e2}")
                return False, 0
        else:
            print(f"Error saving file: {e}")
            return False, 0

def clean_file_name(file_name):
    """Clean and format the file name."""
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name)) 
    unwanted_chars = ['[', ']', '(', ')', '{', '}']

    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id, file_name):
    """Check if the file is already saved in either collection."""
    found1 = {'file_name': file_name}
    found = {'file_id': file_id}

    # Check first database
    if col.find_one(found1) or col.find_one(found):
        print(f"{file_name} is already saved in first database.")
        return True
    
    # Check second database if enabled
    if MULTIPLE_DATABASE and sec_col is not None:
        if sec_col.find_one(found1) or sec_col.find_one(found):
            print(f"{file_name} is already saved in second database.")
            return True

    return False

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """SIMPLE and FAST search - minimal overhead"""
    
    query = query.strip()
    
    # Handle empty query - return recent files
    if not query:
        filter_criteria = {}
        files = []
        
        # Get from first database
        cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        files = list(cursor)
        total_results = col.estimated_document_count()
        
        # Add from second database if enabled
        if MULTIPLE_DATABASE and sec_col is not None:
            cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            files.extend(list(cursor2))
            total_results += sec_col.estimated_document_count()
        
        next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
        return files, next_offset, total_results

    # SIMPLE TEXT SEARCH - using your existing text index
    keywords = query.lower().split()
    text_query = ' '.join([f'"{kw}"' for kw in keywords])
    
    files = []
    
    # Search first database
    cursor = col.find({'$text': {'$search': text_query}}).sort('$natural', -1).skip(offset).limit(max_results)
    files = list(cursor)
    total_results = col.count_documents({'$text': {'$search': text_query}})
    
    # Search second database if enabled
    if MULTIPLE_DATABASE and sec_col is not None:
        cursor2 = sec_col.find({'$text': {'$search': text_query}}).sort('$natural', -1).skip(offset).limit(max_results)
        files.extend(list(cursor2))
        total_results += sec_col.count_documents({'$text': {'$search': text_query}})
    
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    return files, next_offset, total_results

async def get_bad_files(query, file_type=None, use_filter=False):
    """Simple version for getting all files"""
    query = query.strip()

    if not query:
        files = list(col.find({}))
        total_results = len(files)
        
        if MULTIPLE_DATABASE and sec_col is not None:
            files.extend(list(sec_col.find({})))
            total_results = len(files)
        
        return files, total_results

    # Simple text search
    keywords = query.lower().split()
    text_query = ' '.join([f'"{kw}"' for kw in keywords])
    
    files = list(col.find({'$text': {'$search': text_query}}))
    total_results = len(files)
    
    if MULTIPLE_DATABASE and sec_col is not None:
        files.extend(list(sec_col.find({'$text': {'$search': text_query}})))
        total_results = len(files)

    return files, total_results

async def get_file_details(query):
    """Get file details by file_id"""
    result = col.find_one({'file_id': query})
    
    if not result and MULTIPLE_DATABASE and sec_col is not None:
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
    """Return file_id from new file_id format"""
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
