"""
HYPOTHESIS GENERATION: Systematic Analysis of Known Facts vs Cipher Theory

Based on Phases 1-7 findings, generate testable hypotheses.
"""

print("=" * 80)
print("BEALE CIPHER 1: SYSTEMATIC HYPOTHESIS GENERATION")
print("=" * 80)

print("\n" + "=" * 80)
print("WHAT WE KNOW FOR CERTAIN")
print("=" * 80)

confirmed = {
    "DOI is key book": "98.1% of cipher numbers fall within DOI range (510/520)",
    "Position-dependent extraction": "Repeat analysis: same cipher# yields different letters by position",
    "Transposition exists": "Route ciphers consistently outscore sequential reads by 3-5 points",
    "NOT first-letter like Cipher 2": "First-letter extraction scores only 26/100",
    "Caesar shift ruled out": "All 26 rotations tested, zero improvement",
    "No discrete segments": "Phase 6: segment-specific rules score worse than uniform",
    "DOI edition is wrong": "Cipher 2 oracle: 26.5% match (should be >95%)",
    "Signal is real": "37/100 vs random 15/100 = 15.3 sigma above noise"
}

for fact, evidence in confirmed.items():
    print(f"\n[OK] {fact}")
    print(f"     Evidence: {evidence}")

print("\n" + "=" * 80)
print("WHAT'S TENTATIVE (Not Ruled Out)")
print("=" * 80)

tentative = {
    "Exact extraction formula": "position_times_2 and cycle_every_5 both score ~37/100",
    "Correct DOI edition": "1776 Dunlap? Stone engraving? Modified text?",
    "Word numbering offset": "What if beale_papers numbering starts at wrong word?",
    "Homophonic elements": "Could some numbers be nulls/variants for same word?",
    "Partial plaintext": "37/100 suggests ~40% correct - where is it?",
    "Author's intent": "Error-prone encoding? Intentional obscuration? Hoax?"
}

for item, question in tentative.items():
    print(f"\n[?] {item}")
    print(f"    Question: {question}")

print("\n" + "=" * 80)
print("CIPHER THEORY: What Do We Expect?")
print("=" * 80)

cipher_principles = [
    ("Book cipher brittleness", 
     "ONE word difference in key text destroys decoding. Our 26.5% Cipher 2 match is fatal."),
    
    ("Historical cipher simplicity",
     "1820s hand ciphers were simpler than modern cryptography. Likely 1-2 layers max."),
    
    ("Consistency principle",
     "If Cipher 2 uses simple first-letter, Cipher 1 probably uses SIMILAR logic with variation."),
    
    ("Error accumulation",
     "Hand-encoded ciphers have transcription errors. Publisher (1885) may have introduced more."),
    
    ("Signal preservation",
     "37/100 score means ~40% of our method is CORRECT. We're close but systematically off."),
    
    ("Partial match pattern",
     "High signal + no plaintext = systematic misalignment, NOT wrong method family.")
]

for principle, explanation in cipher_principles:
    print(f"\n- {principle}")
    print(f"  => {explanation}")

print("\n" + "=" * 80)
print("CRITICAL INSIGHT: The 26.5% vs 37/100 Paradox")
print("=" * 80)

print("""
OBSERVATION:
- Cipher 2 with first-letter extraction on our DOI: 26.5% match
- Cipher 1 with position-extraction + transposition:  37.0% signal score

PARADOX:
Cipher 1 scores HIGHER than Cipher 2, but Cipher 2 has known plaintext!

POSSIBLE EXPLANATIONS:

A) Our DOI numbering has OFFSET error
   - Text is correct, but word indices are shifted
   - Cipher 2: expects word #115 -> we give word #114 or #116
   - Small offset = catastrophic for first-letter (no error correction)
   - But position-extraction + transposition has MORE TOLERANCE
   - Testable: Try offsets of +/-1, +/-2, +/-3, etc.

B) Cipher 2 is MORE sensitive to DOI errors than Cipher 1
   - First-letter extraction: ZERO error tolerance
   - Position-modulated extraction: averages over word length, smooths errors
   - Transposition: further scrambles, masking alignment errors
   - This explains why C1 scores higher despite using wrong DOI

C) The numbered DOI in beale_papers is a RECONSTRUCTION
   - 1885 publisher tried to reproduce encoder's DOI
   - Got TEXT mostly right, but NUMBERING wrong
   - Small numbering errors accumulate across 1322 words
   - Testable: Systematic offset search
""")

print("\n" + "=" * 80)
print("TESTABLE HYPOTHESES (Priority Order)")
print("=" * 80)

hypotheses = [
    {
        "id": "H1",
        "name": "Word Numbering Offset",
        "hypothesis": "The DOI word indices have a systematic offset error of +/-1 to +/-5 positions.",
        "prediction": "Shifting all cipher numbers by constant offset will improve scores.",
        "test": "For offset in [-10..+10]: map cipher_num to (cipher_num + offset), test best extractors.",
        "expected": "One offset shows >40/100 for Cipher 1 AND >50% for Cipher 2.",
        "cost": "~5 minutes (21 offsets × 10 extractors × 5 transpositions)",
        "priority": "HIGHEST - Immediately testable, explains the paradox"
    },
    {
        "id": "H2",
        "name": "Progressive Drift",
        "hypothesis": "Numbering offset INCREASES through the text (early words correct, late words drift).",
        "prediction": "Early cipher positions decode better than late positions.",
        "test": "Score cipher in 100-number segments, check if quality degrades.",
        "expected": "Positions 1-100 score >45/100, positions 400-520 score <30/100.",
        "cost": "~2 minutes",
        "priority": "HIGH - Explains partial signal"
    },
    {
        "id": "H3",
        "name": "Homophonic Substitution",
        "hypothesis": "Multiple cipher numbers map to same word (like 807, 1005 appearing frequently).",
        "prediction": "High-frequency cipher numbers are intentional variants/nulls.",
        "test": "Map cipher numbers to words, check if high-freq numbers give same word.",
        "expected": "Top 10 cipher numbers by frequency map to <5 unique DOI words.",
        "cost": "~1 minute",
        "priority": "MEDIUM - Common in period ciphers"
    },
    {
        "id": "H4",
        "name": "Two-Key System",
        "hypothesis": "Cipher 1 uses DOI for MOST numbers, but switches key book for certain ranges.",
        "prediction": "OOR numbers (>1322) + clusters map to secondary source.",
        "test": "Check if OOR numbers + nearby ranges form coherent subsequence.",
        "expected": "Numbers 1700-2900 decode coherently with alternate key.",
        "cost": "Requires alternate key text (not immediately testable)",
        "priority": "LOW - Requires additional resources"
    },
    {
        "id": "H5",
        "name": "Plaintext Already Visible",
        "hypothesis": "37/100 score means plaintext is ALREADY 40% present but scrambled.",
        "prediction": "Current best stream contains fragments if we look differently.",
        "test": "Use word-boundary detection, anagram search, fragment assembly.",
        "expected": "Fragments like 'BEDFORD', 'VAULT', 'FEET', 'STONE' present but scattered.",
        "cost": "~10 minutes (new analysis code)",
        "priority": "MEDIUM - Different analysis angle"
    }
]

for h in hypotheses:
    print(f"\n{h['id']}: {h['name']}")
    print(f"{'='*80}")
    print(f"Hypothesis:  {h['hypothesis']}")
    print(f"Prediction:  {h['prediction']}")
    print(f"Test:        {h['test']}")
    print(f"Expected:    {h['expected']}")
    print(f"Cost:        {h['cost']}")
    print(f"Priority:    {h['priority']}")

print("\n" + "=" * 80)
print("RECOMMENDED NEXT STEP")
print("=" * 80)

print("""
TEST H1 (Word Numbering Offset) IMMEDIATELY.

WHY THIS IS THE STRONGEST HYPOTHESIS:
1. Explains Cipher 2 low match (26.5%) - first-letter has no error tolerance
2. Explains Cipher 1 higher score (37%) - position methods average over errors
3. Testable with existing code in ~5 minutes
4. If correct, will show DRAMATIC improvement (>10 points)
5. Book cipher theory predicts exactly this failure mode

THE TEST:
For each offset in range [-10, +10]:
  - Shift all cipher numbers by offset
  - Decode Cipher 2 with first-letter
  - Decode Cipher 1 with best Phase 6 method
  - Look for offset where BOTH improve

SUCCESS CRITERIA:
- Cipher 2 match jumps from 26.5% -> >60%
- Cipher 1 score jumps from 37 -> >45/100
- Same offset works for both ciphers

If H1 succeeds -> Immediate breakthrough
If H1 fails -> Rules out "simple offset" and narrows to H2 (progressive drift)

Estimated runtime: 5 minutes
Code required: ~50 lines (modify cipher_num indexing)
""")

print("\n" + "=" * 80)
print("END OF HYPOTHESIS ANALYSIS")
print("=" * 80)
