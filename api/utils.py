import xxhash


def get_hash(s: str) -> str:
    """Fast hashing function"""
    return xxhash.xxh64(s).hexdigest()
