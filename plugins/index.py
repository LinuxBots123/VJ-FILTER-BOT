async def save_file(media):
    """Save file in the database."""
    try:
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
            return False, 0  # Duplicate

        try:
            col.insert_one(file)
            print(f"✅ {file_name} is successfully saved.")
            return True, 1  # Success
        except DuplicateKeyError:
            print(f"⏭️ {file_name} is already saved.")
            return False, 0  # Duplicate
        except Exception as e:
            print(f"❌ Error in first DB: {e}")
            if MULTIPLE_DATABASE:
                try:
                    sec_col.insert_one(file)
                    print(f"✅ {file_name} is successfully saved in second DB.")
                    return True, 1  # Success
                except DuplicateKeyError:
                    print(f"⏭️ {file_name} is already saved in second DB.")
                    return False, 0  # Duplicate
                except Exception as e2:
                    print(f"❌ Error in second DB: {e2}")
                    return False, 2  # Error
            else:
                print("Database Full! Enable MULTIPLE_DATABASE.")
                return False, 2  # Error
    except Exception as e:
        print(f"❌ Critical error in save_file: {e}")
        return False, 2  # Error
