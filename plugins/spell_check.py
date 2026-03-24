import re
import logging
from spellchecker import SpellChecker
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import MAX_LIST_ELM

logger = logging.getLogger(__name__)

# Initialize spell checker
spell = SpellChecker()

def clean_query(text):
    """Remove common words, numbers, and punctuation for better spelling check."""
    # Remove common filler words
    words_to_remove = {
        'movie', 'film', 'watch', 'download', 'hd', '720p', '1080p', 'web',
        'hindi', 'english', 'tamil', 'telugu', 'malayalam', 'kannada', 'bangla',
        'dual', 'audio', 'x264', 'x265', 'hevc', 'aac', 'mp4', 'mkv'
    }
    # Keep only letters and spaces
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    words = text.split()
    cleaned = [w for w in words if w.lower() not in words_to_remove]
    return ' '.join(cleaned)

def get_spell_suggestions(query):
    """
    Return a list of correctly spelled suggestions for the given query.
    """
    cleaned = clean_query(query)
    if not cleaned:
        return []

    # Get candidate corrections for each word
    corrections = []
    for word in cleaned.split():
        corrected = spell.correction(word)
        if corrected and corrected != word:
            corrections.append(corrected)

    # If we have multiple words corrected, try to combine them
    if corrections and len(corrections) > 1:
        full_corrected = ' '.join(corrections)
        if full_corrected != cleaned:
            corrections.append(full_corrected)

    # Remove duplicates and limit
    suggestions = list(dict.fromkeys(corrections))
    # Limit to MAX_LIST_ELM (default from info.py)
    max_suggestions = int(MAX_LIST_ELM) if MAX_LIST_ELM and str(MAX_LIST_ELM).isdigit() else 5
    return suggestions[:max_suggestions]

def generate_spell_buttons(suggestions, user_id):
    """
    Create inline buttons for each suggestion, storing the user id for validation.
    """
    buttons = []
    for idx, sugg in enumerate(suggestions):
        # Store index and user id in callback data
        buttons.append([InlineKeyboardButton(sugg, callback_data=f"spol#{user_id}#{idx}")])
    # Add a close button
    buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"spol#{user_id}#close_spellcheck")])
    return InlineKeyboardMarkup(buttons)

async def show_spell_suggestions(client, message, user_id, suggestions):
    """
    Send the spell suggestion message with buttons.
    """
    text = (
        "**🔍 SPELLING MISTAKE BRO!**\n\n"
        "No worries — choose the correct one below:\n\n"
        "**Movie Request Format**\n"
        "`#request Movie Name Year`\n\n"
        "Or click one of the suggestions to search again."
    )
    # Store suggestions in a global dict for later retrieval
    from utils import SPELL_CHECK
    SPELL_CHECK[message.id] = suggestions

    await message.reply_text(
        text,
        reply_markup=generate_spell_buttons(suggestions, user_id),
        quote=True
    )
