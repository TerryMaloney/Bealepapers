import sys; sys.path.insert(0, '.')
from corpus.keytexts.loader import normalize_and_cache, load_normalized

normalize_and_cache('webb_freemason_monitor', hyphen='keep')
norm = load_normalized('webb_freemason_monitor')
if norm:
    tc = norm["token_count"]
    t10 = norm["tokens"][:10]
    print(f"Webb: {tc} tokens, first 10: {t10}")
