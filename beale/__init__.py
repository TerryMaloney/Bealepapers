"""Clean-room Beale cipher engine.

Self-contained package: parses the ciphers and the numbered Declaration of
Independence directly from beale_papers.txt, decodes book ciphers, verifies
the known Cipher 2 solution, and searches candidate key texts for Ciphers 1
and 3. Deliberately does not import any legacy module from the repo root.
"""

__version__ = "0.1.0"
