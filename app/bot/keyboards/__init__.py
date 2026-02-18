from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_format_selection_keyboard(job_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🎵 MP3", callback_data=f"select_format:mp3:{job_id}"),
            InlineKeyboardButton("🎬 MP4", callback_data=f"select_format:mp4:{job_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quality_keyboard(format_type: str, job_id: str) -> InlineKeyboardMarkup:
    if format_type == "mp3":
        options = ["128", "192", "320"]
        label = "kbps"
    else:
        options = ["480", "720", "1080"]
        label = "p"
        
    keyboard = []
    row = []
    for opt in options:
        row.append(InlineKeyboardButton(f"{opt}{label}", callback_data=f"start_job:{format_type}:{opt}:{job_id}"))
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"back_to_format:{job_id}")])
    
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard(job_id: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancel:{job_id}")]]
    return InlineKeyboardMarkup(keyboard)
