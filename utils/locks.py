# bot_utils/locks.py
import asyncio
from collections import defaultdict

user_locks = defaultdict(asyncio.Lock)
