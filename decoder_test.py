import re
from pathlib import Path
print("BEALE DECODER RUNNING...")
with open("beale_papers.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]
print(f"Cipher 1: {len(cipher1)} numbers, first 10: {cipher1[:10]}")
