# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re, base64, json
from struct import pack
from typing import List, Tuple, Optional
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

# Quality patterns to extract from filenames
QUALITY_PATTERNS = {
    '2160p': r'\b2160[pi]\b|4k\b',
    '1440p': r'\b1440[pi]\b|2k\b',
    '1080p': r'\b1080[pi]\b',
    '720p': r'\b720[pi]\b',
    '540p': r'\b540[pi]\b',
    '480p': r'\b480[pi]\b',
    '360p': r'\b360[pi]\b',
    'HDRip': r'\bHDRip\b',
    'WEB-DL': r'\bWEB[- ]DL\b',
    'WEBRip': r'\bWEBRip\b',
    'BluRay': r'\bBluRay\b',
    'DVDRip': r'\bDVDRip\b',
    'HDTV': r'\bHDTV\b',
    'HQ': r'\bHQ\b',
    'HDR': r'\bHDR\b',
    'x264': r'\bx264\b',
    'x265': r'\bx265\b',
    'HEVC': r'\bHEVC\b'
}

def extract_quality(file_name: str) -> str:
    """Extract quality information from filename"""
    if not file_name:
        return 'Unknown'
    
    file_name_lower = file_name.lower()
    qualities_found = []
    
    for quality, pattern in QUALITY_PATTERNS.items():
        if re.search(pattern, file_name_lower, re.IGNORECASE):
            qualities_found.append(quality)
    
    # Return the highest quality found
    if qualities_found:
        # Prioritize resolution over rip type
        resolution_order = ['2160p', '1440p', '1080p', '720p', '540p', '480p', '360p']
        for res in resolution_order:
            if res in qualities_found:
                return res
        
        # Check for codec info
        codec_order = ['x265', 'HEVC', 'x264']
        for codec in codec_order:
            if codec in qualities_found:
                return codec
                
        return qualities_found[0]  # Return first found if no resolution
    return 'Unknown'

def extract_file_size_mb(file_size: int) -> float:
    """Convert file size from bytes to MB"""
    return round(file_size / (1024 * 1024), 2) if file_size else 0

def clean_file_name(file_name: str) -> str:
    """Clean and format the file name."""
    if not file_name:
        return ""
    
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(file_name)) 
    unwanted_chars = ['[', ']', '(', ')', '{', '}']
    
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')
        
    return ' '.join(filter(lambda x: not x.startswith('@') and not x.startswith('http') and not x.startswith('www.') and not x.startswith('t.me'), file_name.split()))

def is_file_already_saved(file_id: str, file_name: str, quality: str = None) -> bool:
    """Check if the file is already saved in either collection."""
    # Check by file_id (most accurate)
    found_by_id = {'file_id': file_id}
    
    # Check by file_name and quality combination
    if quality and quality != 'Unknown':
        found_by_name = {
            'file_name': {'$regex': f'.*{re.escape(file_name)}.*', '$options': 'i'},
            'quality': quality
        }
    else:
        found_by_name = {'file_name': {'$regex': f'.*{re.escape(file_name)}.*', '$options': 'i'}}

    for collection in [col, sec_col]:
        if collection.find_one(found_by_id):
            return True
        if collection.find_one(found_by_name):
            return True
            
    return False

async def save_file(media):
    """Save file in the database with quality information."""
    
    try:
        file_id = unpack_new_file_id(media.file_id)
        original_name = media.file_name or "Unknown"
        file_name = clean_file_name(original_name)
        new_file_name = f"@VJ_Bots {file_name}"
        
        # Extract quality and other metadata
        quality = extract_quality(original_name)
        file_size_mb = extract_file_size_mb(media.file_size)
        
        file = {
            'file_id': file_id,
            'file_name': new_file_name,
            'original_name': original_name,
            'file_size': media.file_size,
            'file_size_mb': file_size_mb,
            'quality': quality,
            'caption': media.caption.html if media.caption else None,
            'has_caption': bool(media.caption)
        }

        # Check if file already exists
        if is_file_already_saved(file_id, file_name, quality):
            print(f"{file_name} ({quality}) is already saved.")
            return False, 0

        # Try to save in primary database
        try:
            col.insert_one(file)
            print(f"{file_name} ({quality}) is successfully saved in primary DB.")
            return True, 1
        except DuplicateKeyError:
            print(f"{file_name} ({quality}) already exists in primary DB.")
            return False, 0
        except Exception as e:
            print(f"Error saving to primary DB: {e}")
            
            # If multiple database is enabled, try secondary
            if MULTIPLE_DATABASE:
                try:
                    sec_col.insert_one(file)
                    print(f"{file_name} ({quality}) is successfully saved in secondary DB.")
                    return True, 1
                except DuplicateKeyError:
                    print(f"{file_name} ({quality}) already exists in secondary DB.")
                    return False, 0
                except Exception as e2:
                    print(f"Error saving to secondary DB: {e2}")
                    return False, 0
            else:
                print("Your Current File Database Is Full, Turn On Multiple Database Feature And Add Second File Mongodb To Save File.")
                return False, 0
                
    except Exception as e:
        print(f"Error in save_file: {e}")
        return False, 0

async def get_search_results(chat_id: str, query: str, file_type: str = None, max_results: int = 10, offset: int = 0, filter: bool = False, quality: str = None):
    """For given query return (results, next_offset, total_results) with quality filtering"""
    
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
        
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    # Build filter criteria
    filter_criteria = {'file_name': regex}
    
    # Add quality filter if specified
    if quality and quality != 'all':
        filter_criteria['quality'] = quality
    
    files = []
    
    if MULTIPLE_DATABASE:
        # Get from primary database
        cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        for file in cursor1:
            files.append(file)
        
        # Get from secondary database
        cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        for file in cursor2:
            files.append(file)
    else:
        cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(max_results)
        for file in cursor:
            files.append(file)

    # Get total results count
    if MULTIPLE_DATABASE:
        total_results = col.count_documents(filter_criteria) + sec_col.count_documents(filter_criteria)
    else:
        total_results = col.count_documents(filter_criteria)
        
    next_offset = "" if (offset + max_results) >= total_results else (offset + max_results)

    return files, next_offset, total_results

async def get_bad_files(query: str, file_type: str = None, use_filter: bool = False):
    """For given query return files"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = rf'(\b|[.+-_]){re.escape(query)}(\b|[.+-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[s.+-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return [], 0

    filter_criteria = {'file_name': regex}
    if USE_CAPTION_FILTER:
        filter_criteria = {'$or': [filter_criteria, {'caption': regex}]}

    def count_documents(collection):
        return collection.count_documents(filter_criteria)

    if MULTIPLE_DATABASE:
        total_results = count_documents(col) + count_documents(sec_col)
    else:
        total_results = count_documents(col)

    def find_documents(collection):
        return list(collection.find(filter_criteria))

    if MULTIPLE_DATABASE:
        files = find_documents(col) + find_documents(sec_col)
    else:
        files = find_documents(col)

    return files, total_results

async def get_file_details(query: str):
    """Get file details by file_id"""
    return col.find_one({'file_id': query}) or sec_col.find_one({'file_id': query})

async def get_files_by_quality(query: str, quality: str) -> List[dict]:
    """Get files filtered by quality"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    else:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
    
    filter_criteria = {
        'file_name': regex,
        'quality': quality
    }
    
    files = []
    if MULTIPLE_DATABASE:
        files.extend(list(col.find(filter_criteria)))
        files.extend(list(sec_col.find(filter_criteria)))
    else:
        files.extend(list(col.find(filter_criteria)))
    
    return files

async def get_files_by_quality_and_query(query: str, quality: str, limit: int = 10, offset: int = 0):
    """Get files filtered by both query and quality with pagination"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
        
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
    
    # Build filter criteria
    filter_criteria = {
        'file_name': regex,
        'quality': {'$regex': f'^{quality}$', '$options': 'i'}
    }
    
    files = []
    total_results = 0
    
    if MULTIPLE_DATABASE:
        # Get from primary database
        cursor1 = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(limit)
        for file in cursor1:
            files.append(file)
        
        # Get from secondary database
        cursor2 = sec_col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(limit)
        for file in cursor2:
            files.append(file)
            
        total_results = col.count_documents(filter_criteria) + sec_col.count_documents(filter_criteria)
    else:
        cursor = col.find(filter_criteria).sort('$natural', -1).skip(offset).limit(limit)
        for file in cursor:
            files.append(file)
        total_results = col.count_documents(filter_criteria)
    
    return files, total_results

async def get_available_qualities(query: str) -> List[str]:
    """Get all available qualities for a given movie"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    else:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
    
    filter_criteria = {'file_name': regex}
    
    qualities = set()
    
    if MULTIPLE_DATABASE:
        for file in col.find(filter_criteria):
            if file.get('quality') and file['quality'] != 'Unknown':
                qualities.add(file['quality'])
        for file in sec_col.find(filter_criteria):
            if file.get('quality') and file['quality'] != 'Unknown':
                qualities.add(file['quality'])
    else:
        for file in col.find(filter_criteria):
            if file.get('quality') and file['quality'] != 'Unknown':
                qualities.add(file['quality'])
    
    # Sort qualities by priority
    priority_order = ['2160p', '1440p', '1080p', '720p', '540p', '480p', '360p', 'WEB-DL', 'BluRay', 'HDRip', 'WEBRip', 'DVDRip', 'HDTV']
    sorted_qualities = sorted(list(qualities), key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order))
    
    return sorted_qualities

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
    """Return file_id"""
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

# Helper function to get quality options for inline keyboard
def get_quality_keyboard(qualities: List[str], query: str) -> List[List[dict]]:
    """Generate inline keyboard for quality selection"""
    keyboard = []
    row = []
    
    # Map quality names to display text
    quality_display = {
        '360p': '360P',
        '480p': '480P',
        '540p': '540P',
        '720p': '720P',
        '1080p': '1080P',
        '1440p': '1440P',
        '2160p': '2160P',
        'HDRip': 'HDRip',
        'WEB-DL': 'WEB-DL',
        'WEBRip': 'WEBRip',
        'BluRay': 'BluRay',
        'DVDRip': 'DVDRip',
        'HDTV': 'HDTV',
        'x264': 'x264',
        'x265': 'x265'
    }
    
    for quality in qualities:
        if quality in quality_display:
            button_text = quality_display[quality]
            # Encode query to handle special characters
            encoded_query = query.replace(' ', '_')[:50]
            callback_data = f"quality_{quality}_{encoded_query}"
            row.append({'text': button_text, 'callback_data': callback_data})
            
            if len(row) == 2:  # 2 buttons per row
                keyboard.append(row.copy())
                row = []
    
    # Add remaining buttons
    if row:
        keyboard.append(row)
    
    return keyboard
