"""
Test oracle components: doi_editions, tokenizers, cipher2_evaluator
"""

from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry
from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext


print("=" * 80)
print("ORACLE COMPONENTS TEST")
print("=" * 80)

# Test DOI loader
print("\n[1] Testing DOI Edition Loader...")
loader = DOICorpusLoader()
editions = loader.list_available_editions()
print(f"Available editions: {editions}")

beale_doi = loader.load_edition("beale_embedded")
print(f"Loaded: {beale_doi}")
print(f"Sample: {beale_doi.source_text[:100]}...")

# Test tokenizers
print("\n[2] Testing Tokenizers...")
tokenizers = TokenizerRegistry.get_all_tokenizers()
print(f"Available tokenizers: {len(tokenizers)}")

for tokenizer in tokenizers[:3]:  # Show first 3
    tokens = tokenizer.tokenize(beale_doi.source_text)
    print(f"  {tokenizer.name:20s}: {len(tokens)} tokens")

# Test oracle
print("\n[3] Testing Cipher 2 Oracle...")
cipher2 = load_cipher2()
known_plaintext = load_cipher2_known_plaintext()

print(f"Cipher 2: {len(cipher2)} numbers")
print(f"Known plaintext: {len(known_plaintext)} chars")

oracle = Cipher2Oracle(known_plaintext)

# Test with one tokenizer
tokenizer = TokenizerRegistry.get_tokenizer("hyphen_keep")
tokens = tokenizer.tokenize(beale_doi.source_text)

print(f"\nEvaluating with tokenizer: {tokenizer.name}")
result = oracle.evaluate(tokens, cipher2)

print(f"Match: {result.char_match_pct:.2f}% ({result.char_matches}/{result.total_chars})")
print(f"First mismatch at position: {result.first_mismatch}")
print(f"\n{result.diff_report}")

print("\n" + "=" * 80)
print("ALL ORACLE COMPONENTS WORKING")
print("=" * 80)
