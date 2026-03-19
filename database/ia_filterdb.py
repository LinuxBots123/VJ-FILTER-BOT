# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from pyrogram.file_id import FileId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import FILE_DB_URI, SEC_FILE_DB_URI, DATABASE_NAME, COLLECTION_NAME, MULTIPLE_DATABASE, USE_CAPTION_FILTER, MAX_B_TN
from functools import lru_cache
from time import time

# First Database For File Saving 
client = MongoClient(FILE_DB_URI)
db = client[DATABASE_NAME]
col = db[COLLECTION_NAME]

# Second Database For File Saving
sec_client = MongoClient(SEC_FILE_DB_URI)
sec_db = sec_client[DATABASE_NAME]
sec_col = sec_db[COLLECTION_NAME]

# Simple cache for search results
search_cache = {}
CACHE_DURATION = 300  # 5 minutes cache

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
        # Clear cache when new files added
        search_cache.clear()
        print(f"{file_name} is successfully saved.")
        return True, 1
    except DuplicateKeyError:
        print(f"{file_name} is already saved.")
        return False, 0
    except:
        if MULTIPLE_DATABASE:
            try:
                sec_col.insert_one(file)
                # Clear cache when new files added
                search_cache.clear()
                print(f"{file_name} is successfully saved.")
                return True, 1
            except DuplicateKeyError:
                print(f"{file_name} is already saved.")
                return False, 0
        else:
            print("Your Current File Database Is Full, Turn On Multiple Database Feature And Add Second File Mongodb To Save File.")

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

    for collection in [col, sec_col]:
        if collection.find_one(found1) or collection.find_one(found):
            print(f"{file_name} is already saved.")
            return True

    return False

async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """ULTRA-FAST search with caching - now under 1 second for repeated queries"""
    
    query = query.strip()
    cache_key = f"{query}_{offset}_{max_results}_{MULTIPLE_DATABASE}"
    
    # Check cache first (for repeated searches)
    if cache_key in search_cache:
        cached_time, cached_results = search_cache[cache_key]
        if time() - cached_time < CACHE_DURATION:
            return cached_results
    
    if not query:
        # Return recent files with estimated count (fastest)
        filter_criteria = {}
        files = []
        
        if MULTIPLE_DATABASE:
            # Parallel execution for speed
            cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            
            files = list(cursor1) + list(cursor2)
            total_results = col.estimated_document_count() + sec_col.estimated_document_count()
        else:
            cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
            files = list(cursor)
            total_results = col.estimated_document_count()
        
        next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
        results = (files, next_offset, total_results)
        
        # Cache the results
        search_cache[cache_key] = (time(), results)
        return results

    # FAST TEXT SEARCH - using MongoDB's text index
    # Split query into keywords
    keywords = query.lower().split()
    
    # Create text search query that REQUIRES all keywords
    text_query = ' '.join([f'"{kw}"' for kw in keywords])
    
    # Use text search with relevance scoring and limit results
    if MULTIPLE_DATABASE:
        # Search in first database with limit to reduce data transfer
        cursor1 = col.find(
            {'$text': {'$search': text_query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).skip(offset).limit(max_results)
        
        # Search in second database with limit
        cursor2 = sec_col.find(
            {'$text': {'$search': text_query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).skip(offset).limit(max_results)
        
        # Combine results efficiently
        files1 = list(cursor1)
        files2 = list(cursor2)
        files = files1 + files2
        
        # Get total count (fast with text index) - only if needed for pagination
        if offset == 0 and len(files) < max_results:
            # If we got fewer results than requested, we need total count
            total_results = col.count_documents({'$text': {'$search': text_query}}) + \
                           sec_col.count_documents({'$text': {'$search': text_query}})
        else:
            # Otherwise estimate based on what we got
            total_results = max(len(files), offset + max_results + 1)
    else:
        # Single database search
        cursor = col.find(
            {'$text': {'$search': text_query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).skip(offset).limit(max_results)
        
        files = list(cursor)
        
        if offset == 0 and len(files) < max_results:
            total_results = col.count_documents({'$text': {'$search': text_query}})
        else:
            total_results = max(len(files), offset + max_results + 1)
    
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)
    results = (files, next_offset, total_results)
    
    # Cache the results
    search_cache[cache_key] = (time(), results)
    return results

async def get_bad_files(query, file_type=None, use_filter=False):
    """ULTRA-FAST version with caching for getting all files matching query"""
    query = query.strip()
    cache_key = f"bad_{query}_{MULTIPLE_DATABASE}_{USE_CAPTION_FILTER}"
    
    # Check cache first
    if cache_key in search_cache:
        cached_time, cached_results = search_cache[cache_key]
        if time() - cached_time < CACHE_DURATION:
            return cached_results

    if not query:
        # Return all files with estimated count
        if MULTIPLE_DATABASE:
            # Limit to prevent memory issues
            files = list(col.find({}).limit(1000)) + list(sec_col.find({}).limit(1000))
            total_results = min(1000, col.estimated_document_count() + sec_col.estimated_document_count())
        else:
            files = list(col.find({}).limit(1000))
            total_results = min(1000, col.estimated_document_count())
        
        results = (files, total_results)
        search_cache[cache_key] = (time(), results)
        return results

    # Use text search for fast results
    keywords = query.lower().split()
    text_query = ' '.join([f'"{kw}"' for kw in keywords])
    
    if MULTIPLE_DATABASE:
        # Search both databases with limits
        files = list(col.find({'$text': {'$search': text_query}}).limit(500)) + \
                list(sec_col.find({'$text': {'$search': text_query}}).limit(500))
        
        total_results = len(files)
        
        if USE_CAPTION_FILTER and total_results < 200:
            # Only search captions if we have few results
            caption_files = list(col.find({'caption': {'$regex': text_query, '$options': 'i'}}).limit(200)) + \
                           list(sec_col.find({'caption': {'$regex': text_query, '$options': 'i'}}).limit(200))
            files.extend(caption_files)
            # Remove duplicates efficiently
            seen = set()
            unique_files = []
            for f in files:
                if f['file_id'] not in seen:
                    seen.add(f['file_id'])
                    unique_files.append(f)
            files = unique_files[:500]  # Limit total results
            total_results = len(files)
    else:
        # Single database search
        files = list(col.find({'$text': {'$search': text_query}}).limit(500))
        total_results = len(files)
        
        if USE_CAPTION_FILTER and total_results < 200:
            caption_files = list(col.find({'caption': {'$regex': text_query, '$options': 'i'}}).limit(200))
            files.extend(caption_files)
            # Remove duplicates
            seen = set()
            unique_files = []
            for f in files:
                if f['file_id'] not in seen:
                    seen.add(f['file_id'])
                    unique_files.append(f)
            files = unique_files[:500]
            total_results = len(files)

    results = (files, total_results)
    search_cache[cache_key] = (time(), results)
    return results

async def get_file_details(query):
    """Get file details by file_id - with simple cache"""
    cache_key = f"file_{query}"
    
    if cache_key in search_cache:
        cached_time, cached_result = search_cache[cache_key]
        if time() - cached_time < CACHE_DURATION * 2:  # Longer cache for file details
            return cached_result
    
    result = col.find_one({'file_id': query})
    if not result and MULTIPLE_DATABASE:
        result = sec_col.find_one({'file_id': query})
    
    if result:
        search_cache[cache_key] = (time(), result)
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

# Function to clear cache manually if needed
def clear_cache():
    """Clear the search cache"""
    global search_cache
    search_cache.clear()
    print("🧹 Cache cleared!")
