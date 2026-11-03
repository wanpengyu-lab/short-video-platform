# -*- coding: utf-8 -*-
import hashlib, random, time
from config import CRAWL_CONFIG

def hash_password(password: str) -> str:
    salt = "short_video_2024"
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def get_random_ua() -> str:
    return random.choice(CRAWL_CONFIG['USER_AGENT_POOL'])

def random_delay():
    delay = random.uniform(CRAWL_CONFIG['REQUEST_DELAY_MIN'], CRAWL_CONFIG['REQUEST_DELAY_MAX'])
    time.sleep(delay)

def format_count(count_str: str) -> int:
    if not count_str:
        return 0
    count_str = str(count_str).strip()
    try:
        if '万' in count_str or 'w' in count_str.lower():
            num = float(count_str.replace('万', '').replace('w', '').replace('W', ''))
            return int(num * 10000)
        elif '亿' in count_str:
            num = float(count_str.replace('亿', ''))
            return int(num * 100000000)
        else:
            return int(float(count_str))
    except (ValueError, TypeError):
        return 0

def paginate(total: int, page: int, per_page: int = 10) -> dict:
    pages = (total + per_page - 1) // per_page
    page = max(1, min(page, pages)) if pages > 0 else 1
    offset = (page - 1) * per_page
    return {'total': total, 'page': page, 'per_page': per_page, 'pages': pages, 'offset': offset}
