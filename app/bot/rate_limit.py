import time
from typing import Dict
from telegram import Update
from telegram.ext import ContextTypes
from app.core.config import settings

class RateLimiter:
    def __init__(self):
        self.user_last_action: Dict[int, float] = {}

    def is_rate_limited(self, user_id: int) -> bool:
        current_time = time.time()
        last_action = self.user_last_action.get(user_id, 0)
        
        # Simple cooldown (e.g., 3 seconds)
        if current_time - last_action < 3:
            return True
            
        self.user_last_action[user_id] = current_time
        return False

rate_limiter = RateLimiter()
