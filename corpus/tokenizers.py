"""
Tokenizer Presets - Multiple tokenization strategies for DOI text.

Tests different ways of splitting DOI text into words to find correct method.
"""

import re
from typing import List, Dict, Callable
from dataclasses import dataclass


@dataclass
class TokenizerRules:
    """Rules for tokenization."""
    hyphen: str  # 'keep' or 'split'
    apostrophe: str  # 'keep' or 'strip'
    punctuation: str  # 'strict' or 'light'
    case: str  # 'lower' or 'preserve'
    headers: str  # 'include' or 'exclude'
    numbers: str = 'remove'  # 'keep' or 'remove'


class Tokenizer:
    """Tokenizes DOI text according to specific rules."""
    
    def __init__(self, name: str, rules: TokenizerRules):
        self.name = name
        self.rules = rules
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text according to rules."""
        
        # Apply case transformation first
        if self.rules.case == 'lower':
            text = text.lower()
        
        # Handle apostrophes
        if self.rules.apostrophe == 'strip':
            text = text.replace("'", "")
        
        # Handle hyphens
        if self.rules.hyphen == 'split':
            text = text.replace("-", " ")
        
        # Handle punctuation
        if self.rules.punctuation == 'strict':
            # Remove all punctuation except hyphens (if kept)
            if self.rules.hyphen == 'keep':
                text = re.sub(r'[^\w\s-]', '', text)
            else:
                text = re.sub(r'[^\w\s]', '', text)
        else:  # light
            # Remove common punctuation but keep structure
            text = re.sub(r'[.,;:!?"\(\)\[\]]', '', text)
        
        # Split on whitespace
        tokens = text.split()
        
        # Handle numbers
        if self.rules.numbers == 'remove':
            tokens = [t for t in tokens if not t.isdigit()]
        
        # Filter empty strings
        tokens = [t for t in tokens if t]
        
        return tokens
    
    def __repr__(self):
        return f"Tokenizer('{self.name}')"


class TokenizerRegistry:
    """Registry of predefined tokenizer presets."""
    
    PRESETS = {
        "strict_word": TokenizerRules(
            hyphen='split',
            apostrophe='strip',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
        "punct_tokens": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='light',
            case='lower',
            headers='exclude'
        ),
        "hyphen_split": TokenizerRules(
            hyphen='split',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
        "hyphen_keep": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
        "apostrophe_split": TokenizerRules(
            hyphen='keep',
            apostrophe='strip',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
        "apostrophe_keep": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
        "case_preserve": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='strict',
            case='preserve',
            headers='exclude'
        ),
        "minimal": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='light',
            case='preserve',
            headers='exclude'
        ),
        
        # NEW Phase 8+9 presets
        "header_include": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='include'  # Include "IN CONGRESS" header
        ),
        "header_include_hyphen_split": TokenizerRules(
            hyphen='split',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='include'
        ),
        "numbers_keep": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='exclude',
            numbers='keep'  # Keep "1776" as token
        ),
        "aggressive_split": TokenizerRules(
            hyphen='split',
            apostrophe='strip',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
        "header_include_aggressive": TokenizerRules(
            hyphen='split',
            apostrophe='strip',
            punctuation='strict',
            case='lower',
            headers='include'
        ),
        "case_preserve_header": TokenizerRules(
            hyphen='keep',
            apostrophe='keep',
            punctuation='strict',
            case='preserve',
            headers='include'
        ),
        # Beale DOI patch: hyphen_split + self-evident/mean-time quirks
        # Use with nara_beale_patched edition (pre-tokenized, split on whitespace)
        "beale_patch_hyphen_split": TokenizerRules(
            hyphen='split',
            apostrophe='keep',
            punctuation='strict',
            case='lower',
            headers='exclude'
        ),
    }
    
    @classmethod
    def get_tokenizer(cls, name: str) -> Tokenizer:
        """Get a tokenizer by preset name."""
        if name not in cls.PRESETS:
            raise ValueError(f"Unknown tokenizer preset: {name}. "
                           f"Available: {list(cls.PRESETS.keys())}")
        
        rules = cls.PRESETS[name]
        return Tokenizer(name, rules)
    
    @classmethod
    def list_presets(cls) -> List[str]:
        """List all available tokenizer presets."""
        return list(cls.PRESETS.keys())
    
    @classmethod
    def get_all_tokenizers(cls) -> List[Tokenizer]:
        """Get all tokenizers as list."""
        return [cls.get_tokenizer(name) for name in cls.list_presets()]


def test_tokenizers():
    """Test tokenizer presets."""
    print("=" * 80)
    print("TOKENIZER PRESETS TEST")
    print("=" * 80)
    
    # Test text with various edge cases
    test_text = "We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness."
    
    print(f"\nTest text:\n{test_text}\n")
    print(f"Length: {len(test_text)} characters")
    print("=" * 80)
    
    presets = TokenizerRegistry.list_presets()
    print(f"\nTesting {len(presets)} tokenizer presets:\n")
    
    results = {}
    for preset_name in presets:
        tokenizer = TokenizerRegistry.get_tokenizer(preset_name)
        tokens = tokenizer.tokenize(test_text)
        results[preset_name] = tokens
        
        print(f"{preset_name:20s} | {len(tokens):3d} tokens")
        print(f"  Rules: h={tokenizer.rules.hyphen}, a={tokenizer.rules.apostrophe}, "
              f"p={tokenizer.rules.punctuation}, c={tokenizer.rules.case}")
        print(f"  Sample: {' '.join(tokens[:10])}...")
        print()
    
    # Compare differences
    print("=" * 80)
    print("KEY DIFFERENCES:")
    print("=" * 80)
    
    # Check how "self-evident" is handled
    print("\nHandling of 'self-evident':")
    for preset_name, tokens in results.items():
        joined = ' '.join(tokens)
        if 'selfevident' in joined:
            print(f"  {preset_name:20s}: selfevident (merged)")
        elif 'self' in joined and 'evident' in joined:
            if 'self-evident' in joined:
                print(f"  {preset_name:20s}: self-evident (kept hyphen)")
            else:
                print(f"  {preset_name:20s}: self evident (split)")
    
    # Check how "Creator" case is handled
    print("\nHandling of 'Creator' (case):")
    for preset_name, tokens in results.items():
        joined = ' '.join(tokens)
        if 'Creator' in joined:
            print(f"  {preset_name:20s}: Creator (preserved)")
        elif 'creator' in joined:
            print(f"  {preset_name:20s}: creator (lowercased)")
    
    print("\n" + "=" * 80)
    print("TOKENIZER TEST COMPLETE")
    print("=" * 80)
    print(f"\n{len(presets)} tokenizer presets ready for oracle sweep.")
    
    return results


if __name__ == "__main__":
    test_tokenizers()
