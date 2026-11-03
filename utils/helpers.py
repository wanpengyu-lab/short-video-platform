# -*- coding: utf-8 -*-
import hashlib, hmac, os, base64, random, time
from config import CRAWL_CONFIG

# ========== 密码哈希 ==========
# 采用 PBKDF2-HMAC-SHA256 + 每用户随机盐 + 多次迭代。
# 存储格式：pbkdf2_sha256$迭代次数$base64(盐)$base64(派生密钥)
#
# 旧格式 sha256(固定盐 + 密码) 仍可校验，以便平滑过渡：
# 用户使用旧格式密码成功登录后，由登录流程自动升级为当前格式。
_PBKDF2_ITERATIONS = 200_000
_LEGACY_STATIC_SALT = "short_video_2024"
_HASH_PREFIX = "pbkdf2_sha256$"


def hash_password(password: str) -> str:
    """生成密码哈希（PBKDF2，每用户独立随机盐）"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt, _PBKDF2_ITERATIONS
    )
    return "{}{}${}${}".format(
        _HASH_PREFIX,
        _PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode('ascii'),
        base64.b64encode(dk).decode('ascii'),
    )


def _legacy_hash_password(password: str) -> str:
    """旧版哈希算法，仅用于校验历史数据，不再用于生成新哈希"""
    return hashlib.sha256(
        (_LEGACY_STATIC_SALT + password).encode('utf-8')
    ).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """
    校验密码。兼容当前 PBKDF2 格式与历史 sha256 格式。
    使用 compare_digest 做定长时间比较，避免计时侧信道。
    """
    if not password or not hashed:
        return False

    if hashed.startswith(_HASH_PREFIX):
        try:
            _, iterations, salt_b64, dk_b64 = hashed.split('$')
            dk = hashlib.pbkdf2_hmac(
                'sha256', password.encode('utf-8'),
                base64.b64decode(salt_b64), int(iterations)
            )
            return hmac.compare_digest(base64.b64encode(dk).decode('ascii'), dk_b64)
        except (ValueError, TypeError):
            return False

    # 历史格式：sha256(固定盐 + 密码)
    return hmac.compare_digest(_legacy_hash_password(password), hashed)


def needs_rehash(hashed: str) -> bool:
    """判断存储的哈希是否为旧格式，需要在下次成功登录时升级"""
    return not (hashed or '').startswith(_HASH_PREFIX)

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
