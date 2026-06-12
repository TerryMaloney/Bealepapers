# Key-document dossier — what the cipher numbers alone reveal

*Method: count->letter posteriors calibrated on Cipher 2's verified
key table; structural statistics vs the known-genuine C2 baseline.*

## Cipher 3 key document

- **Length**: at least 975 words (highest index used). Usage density in the top decile of the range: 10 distinct indices — the document likely ends near word 975 (dense usage to the edge).
- **Indices used**: 263 distinct of 618 positions; 124 used once.
- **Usage habit**: lag-1 number autocorrelation +0.61 — the encoder worked LOCALLY, drifting through nearby words rather than jumping freely (unlike the C2 encoder, who jumped).
- **Most-consulted words** (count -> most likely initials, calibrated on C2's verified key):
    - word #96 (used 13x): starts with e (13%), t (12%), n (9%)
    - word #18 (used 11x): starts with e (13%), t (12%), n (9%)
    - word #89 (used 10x): starts with e (13%), t (12%), n (9%)
    - word #19 (used 9x): starts with e (13%), t (12%), n (9%)
    - word #66 (used 9x): starts with e (13%), t (12%), n (9%)
    - word #81 (used 8x): starts with e (13%), t (12%), n (9%)
    - word #28 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #77 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #44 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #11 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #82 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #84 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #65 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #48 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #218 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #8 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #112 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #98 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #116 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #32 (used 5x): starts with e (13%), t (12%), n (9%)

## Cipher 1 key document

- **Length**: at least 2906 words (highest index used). Usage density in the top decile of the range: 1 distinct indices — sparse near the top; the document may extend well beyond word 2906.
- **Indices used**: 298 distinct of 520 positions; 177 used once.
- **Usage habit**: lag-1 number autocorrelation +0.25 — the encoder worked LOCALLY, drifting through nearby words rather than jumping freely (unlike the C2 encoder, who jumped).
- **Most-consulted words** (count -> most likely initials, calibrated on C2's verified key):
    - word #18 (used 8x): starts with e (13%), t (12%), n (9%)
    - word #216 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #19 (used 7x): starts with e (13%), t (12%), n (9%)
    - word #16 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #84 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #81 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #88 (used 6x): starts with e (13%), t (12%), n (9%)
    - word #71 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #38 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #11 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #63 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #64 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #10 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #36 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #34 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #86 (used 5x): starts with e (13%), t (12%), n (9%)
    - word #95 (used 4x): starts with a (12%), o (10%), e (10%)
    - word #14 (used 4x): starts with a (12%), o (10%), e (10%)
    - word #150 (used 4x): starts with a (12%), o (10%), e (10%)
    - word #17 (used 4x): starts with a (12%), o (10%), e (10%)

## Cross-cutting verdicts (phase 4)

- Repeated-pattern test: genuine encoding (C2) leaves repeated
  number n-grams that decode to top English bigrams (ed, ve, th,
  in / her, nds, ove); **C1 and C3 contain none** (z ~ 0). Number
  VALUE locality without PATTERN repetition is the opposite of
  what encoded English produced for this encoder.
- Soft fingerprint matcher: validated to rank the true key #1 on
  C2's numbers alone, but with sub-threshold margin; C3/C1 scans
  produced no lead separating from noise.
- If C3 encodes anything by first letters, its key is an
  alphabetized or locally-scanned word list rather than prose
  consulted at random — see the dictionary-key attack verdict.
