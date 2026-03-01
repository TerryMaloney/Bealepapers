"""
TRANSPOSITION TEST FRAMEWORK
Apply various reordering transformations to extracted character streams.

Each transposition method takes a string and returns a reordered version
that might reveal hidden English patterns.
"""

from typing import Callable

class Transposition:
    """Base class for transposition methods"""
    
    def __init__(self, name: str):
        self.name = name
    
    def apply(self, stream: str) -> str:
        """Apply transposition to stream"""
        raise NotImplementedError
    
    def __repr__(self):
        return f"Transposition({self.name})"


# ============================================================================
# NO TRANSPOSITION (BASELINE)
# ============================================================================

class NoTransposition(Transposition):
    """No transformation - baseline"""
    def __init__(self):
        super().__init__("none")
    
    def apply(self, stream: str) -> str:
        return stream


# ============================================================================
# CHUNK GROUPING
# ============================================================================

class ChunkReverse(Transposition):
    """Reverse chunks of specified size"""
    def __init__(self, chunk_size: int):
        super().__init__(f"chunk_reverse_{chunk_size}")
        self.chunk_size = chunk_size
    
    def apply(self, stream: str) -> str:
        chunks = [stream[i:i+self.chunk_size] for i in range(0, len(stream), self.chunk_size)]
        return ''.join(chunk[::-1] for chunk in chunks)


class ChunkSwap(Transposition):
    """Swap adjacent chunks of specified size"""
    def __init__(self, chunk_size: int):
        super().__init__(f"chunk_swap_{chunk_size}")
        self.chunk_size = chunk_size
    
    def apply(self, stream: str) -> str:
        chunks = [stream[i:i+self.chunk_size] for i in range(0, len(stream), self.chunk_size)]
        result = []
        for i in range(0, len(chunks)-1, 2):
            result.append(chunks[i+1])
            result.append(chunks[i])
        if len(chunks) % 2 == 1:
            result.append(chunks[-1])
        return ''.join(result)


# ============================================================================
# COLUMNAR TRANSPOSITION
# ============================================================================

class ColumnarTransposition(Transposition):
    """Write in rows of width W, read in columns"""
    def __init__(self, width: int):
        super().__init__(f"columnar_w{width}")
        self.width = width
    
    def apply(self, stream: str) -> str:
        if not stream or self.width <= 0:
            return stream
        
        # Pad stream to fill grid
        rows = (len(stream) + self.width - 1) // self.width
        padded = stream + '_' * (rows * self.width - len(stream))
        
        # Read in columns
        result = []
        for col in range(self.width):
            for row in range(rows):
                idx = row * self.width + col
                if idx < len(padded):
                    result.append(padded[idx])
        
        return ''.join(result)


# ============================================================================
# ZIGZAG READING
# ============================================================================

class ZigzagRead(Transposition):
    """Read in zigzag pattern across rows of width W"""
    def __init__(self, width: int):
        super().__init__(f"zigzag_w{width}")
        self.width = width
    
    def apply(self, stream: str) -> str:
        if not stream or self.width <= 0:
            return stream
        
        # Split into rows
        rows = [stream[i:i+self.width] for i in range(0, len(stream), self.width)]
        
        # Read alternating directions
        result = []
        for i, row in enumerate(rows):
            if i % 2 == 0:
                result.append(row)
            else:
                result.append(row[::-1])
        
        return ''.join(result)


# ============================================================================
# EVERY NTH CHARACTER
# ============================================================================

class EveryNth(Transposition):
    """Extract every Nth character, cycling through offsets"""
    def __init__(self, n: int):
        super().__init__(f"every_{n}th")
        self.n = n
    
    def apply(self, stream: str) -> str:
        if not stream or self.n <= 0:
            return stream
        
        result = []
        # Collect every nth character, starting from each offset 0..(n-1)
        for offset in range(self.n):
            for i in range(offset, len(stream), self.n):
                result.append(stream[i])
        
        return ''.join(result)


# ============================================================================
# REVERSE PATTERNS
# ============================================================================

class ReverseAll(Transposition):
    """Reverse entire stream"""
    def __init__(self):
        super().__init__("reverse_all")
    
    def apply(self, stream: str) -> str:
        return stream[::-1]


class ReverseHalves(Transposition):
    """Swap and reverse first and second halves"""
    def __init__(self):
        super().__init__("reverse_halves")
    
    def apply(self, stream: str) -> str:
        if len(stream) < 2:
            return stream
        mid = len(stream) // 2
        first_half = stream[:mid]
        second_half = stream[mid:]
        return second_half[::-1] + first_half[::-1]


# ============================================================================
# HISTORICAL CIPHER METHODS (Phase 3)
# ============================================================================

class RailFenceCipher(Transposition):
    """Rail fence cipher - zigzag write pattern, common in 1800s"""
    def __init__(self, rails: int):
        super().__init__(f"railfence_{rails}")
        self.rails = rails
    
    def apply(self, stream: str) -> str:
        if not stream or self.rails <= 1:
            return stream
        
        # Create rail pattern
        rails_data = [[] for _ in range(self.rails)]
        rail = 0
        direction = 1
        
        for char in stream:
            rails_data[rail].append(char)
            rail += direction
            if rail == 0 or rail == self.rails - 1:
                direction *= -1
        
        # Read sequentially
        return ''.join(''.join(rail) for rail in rails_data)


class ProgressiveOffset(Transposition):
    """Progressive Caesar shift - each character shifted by increasing amount"""
    def __init__(self, start: int = 1):
        super().__init__(f"progressive_offset_{start}")
        self.start = start
    
    def apply(self, stream: str) -> str:
        result = []
        for i, char in enumerate(stream):
            if char.isalpha():
                # Shift by (start + i) positions
                shift = (self.start + i) % 26
                shifted = chr((ord(char) - ord('A') + shift) % 26 + ord('A'))
                result.append(shifted)
            else:
                result.append(char)
        return ''.join(result)


class SpiralRead(Transposition):
    """Write in grid, read in spiral pattern (clockwise inward)"""
    def __init__(self, width: int):
        super().__init__(f"spiral_w{width}")
        self.width = width
    
    def apply(self, stream: str) -> str:
        if not stream or self.width <= 0:
            return stream
        
        # Create grid
        height = (len(stream) + self.width - 1) // self.width
        grid = []
        idx = 0
        for _ in range(height):
            row = []
            for _ in range(self.width):
                if idx < len(stream):
                    row.append(stream[idx])
                else:
                    row.append('_')
                idx += 1
            grid.append(row)
        
        # Read spiral (simplified: just outer ring, then recurse)
        result = []
        top, bottom = 0, height - 1
        left, right = 0, self.width - 1
        
        while top <= bottom and left <= right:
            # Top row
            for i in range(left, right + 1):
                if top < len(grid) and i < len(grid[top]):
                    result.append(grid[top][i])
            top += 1
            
            # Right column
            for i in range(top, bottom + 1):
                if i < len(grid) and right < len(grid[i]):
                    result.append(grid[i][right])
            right -= 1
            
            # Bottom row
            if top <= bottom:
                for i in range(right, left - 1, -1):
                    if bottom < len(grid) and i < len(grid[bottom]):
                        result.append(grid[bottom][i])
                bottom -= 1
            
            # Left column
            if left <= right:
                for i in range(bottom, top - 1, -1):
                    if i < len(grid) and left < len(grid[i]):
                        result.append(grid[i][left])
                left += 1
        
        return ''.join(result)


class DiagonalRead(Transposition):
    """Write in rows, read diagonally"""
    def __init__(self, width: int):
        super().__init__(f"diagonal_w{width}")
        self.width = width
    
    def apply(self, stream: str) -> str:
        if not stream or self.width <= 0:
            return stream
        
        # Create grid
        height = (len(stream) + self.width - 1) // self.width
        grid = []
        idx = 0
        for _ in range(height):
            row = []
            for _ in range(self.width):
                if idx < len(stream):
                    row.append(stream[idx])
                else:
                    row.append('_')
                idx += 1
            grid.append(row)
        
        # Read diagonals (top-right to bottom-left)
        result = []
        for k in range(height + self.width - 1):
            for i in range(max(0, k - self.width + 1), min(height, k + 1)):
                j = k - i
                if j < self.width:
                    result.append(grid[i][j])
        
        return ''.join(result)


class SkipPattern(Transposition):
    """Skip N characters, read every Mth, cycle"""
    def __init__(self, skip: int, take: int):
        super().__init__(f"skip_{skip}_take_{take}")
        self.skip = skip
        self.take = take
    
    def apply(self, stream: str) -> str:
        result = []
        i = 0
        while i < len(stream):
            # Skip N
            i += self.skip
            # Take M
            for _ in range(self.take):
                if i < len(stream):
                    result.append(stream[i])
                    i += 1
        return ''.join(result)


class DoubleColumnar(Transposition):
    """Apply columnar transposition twice with different widths"""
    def __init__(self, width1: int, width2: int):
        super().__init__(f"double_columnar_{width1}_{width2}")
        self.col1 = ColumnarTransposition(width1)
        self.col2 = ColumnarTransposition(width2)
    
    def apply(self, stream: str) -> str:
        first_pass = self.col1.apply(stream)
        return self.col2.apply(first_pass)


# ============================================================================
# PHASE 5 ADVANCED TRANSPOSITIONS
# ============================================================================

class KeywordColumnar(Transposition):
    """Columnar transposition with keyword-derived column order"""
    def __init__(self, keyword: str):
        super().__init__(f"col_key_{keyword}")
        self.keyword = keyword.upper()
        # Derive column order from keyword alphabetical sort
        sorted_chars = sorted(enumerate(self.keyword), key=lambda x: x[1])
        self.column_order = [x[0] for x in sorted_chars]
        self.cols = len(keyword)
    
    def apply(self, stream: str) -> str:
        if not stream or self.cols <= 0:
            return stream
        
        # Write row-wise into columns
        rows = (len(stream) + self.cols - 1) // self.cols
        grid = [['_'] * self.cols for _ in range(rows)]
        
        for i, char in enumerate(stream):
            row = i // self.cols
            col = i % self.cols
            grid[row][col] = char
        
        # Read by column order
        result = []
        for col_idx in self.column_order:
            for row in grid:
                if row[col_idx] != '_':
                    result.append(row[col_idx])
        
        return ''.join(result)


class RectangleFill(Transposition):
    """Fill rectangle with width W, read in specified pattern"""
    def __init__(self, width: int, pattern: str):
        super().__init__(f"rect_w{width}_{pattern}")
        self.width = width
        self.pattern = pattern
    
    def apply(self, stream: str) -> str:
        if not stream or self.width <= 0:
            return stream
        
        # Create grid
        height = (len(stream) + self.width - 1) // self.width
        grid = []
        idx = 0
        for _ in range(height):
            row = []
            for _ in range(self.width):
                if idx < len(stream):
                    row.append(stream[idx])
                else:
                    row.append('_')
                idx += 1
            grid.append(row)
        
        # Read pattern
        if self.pattern == 'spiral_cw':
            return self._spiral_clockwise(grid)
        elif self.pattern == 'spiral_ccw':
            return self._spiral_counterclockwise(grid)
        elif self.pattern == 'diagonal':
            return self._diagonal_read(grid)
        else:
            return stream
    
    def _spiral_clockwise(self, grid):
        """Read grid in clockwise spiral"""
        result = []
        top, bottom = 0, len(grid) - 1
        left, right = 0, len(grid[0]) - 1
        
        while top <= bottom and left <= right:
            for i in range(left, right + 1):
                if top < len(grid) and i < len(grid[top]):
                    result.append(grid[top][i])
            top += 1
            
            for i in range(top, bottom + 1):
                if i < len(grid) and right < len(grid[i]):
                    result.append(grid[i][right])
            right -= 1
            
            if top <= bottom:
                for i in range(right, left - 1, -1):
                    if bottom < len(grid) and i < len(grid[bottom]):
                        result.append(grid[bottom][i])
                bottom -= 1
            
            if left <= right:
                for i in range(bottom, top - 1, -1):
                    if i < len(grid) and left < len(grid[i]):
                        result.append(grid[i][left])
                left += 1
        
        return ''.join(result)
    
    def _spiral_counterclockwise(self, grid):
        """Read grid in counterclockwise spiral"""
        result = []
        top, bottom = 0, len(grid) - 1
        left, right = 0, len(grid[0]) - 1
        
        while top <= bottom and left <= right:
            for i in range(top, bottom + 1):
                if i < len(grid) and left < len(grid[i]):
                    result.append(grid[i][left])
            left += 1
            
            for i in range(left, right + 1):
                if bottom < len(grid) and i < len(grid[bottom]):
                    result.append(grid[bottom][i])
            bottom -= 1
            
            if left <= right:
                for i in range(bottom, top - 1, -1):
                    if i < len(grid) and right < len(grid[i]):
                        result.append(grid[i][right])
                right -= 1
            
            if top <= bottom:
                for i in range(right, left - 1, -1):
                    if top < len(grid) and i < len(grid[top]):
                        result.append(grid[top][i])
                top += 1
        
        return ''.join(result)
    
    def _diagonal_read(self, grid):
        """Read grid diagonally"""
        result = []
        height = len(grid)
        width = len(grid[0]) if grid else 0
        
        for k in range(height + width - 1):
            for i in range(max(0, k - width + 1), min(height, k + 1)):
                j = k - i
                if j < width:
                    result.append(grid[i][j])
        
        return ''.join(result)


class DoubleTranspositionPhase5(Transposition):
    """Apply two transpositions sequentially"""
    def __init__(self, trans1: Transposition, trans2: Transposition):
        super().__init__(f"double_{trans1.name}_{trans2.name}")
        self.trans1 = trans1
        self.trans2 = trans2
    
    def apply(self, stream: str) -> str:
        intermediate = self.trans1.apply(stream)
        return self.trans2.apply(intermediate)


# ============================================================================
# PHASE 7 TWO-STAGE TRANSPOSITION
# ============================================================================

class TwoStageTransposition(Transposition):
    """Apply two transpositions sequentially - classic historical method"""
    def __init__(self, stage1: Transposition, stage2: Transposition):
        super().__init__(f"two_{stage1.name}_then_{stage2.name}")
        self.stage1 = stage1
        self.stage2 = stage2
    
    def apply(self, stream: str) -> str:
        intermediate = self.stage1.apply(stream)
        return self.stage2.apply(intermediate)


# ============================================================================
# TRANSPOSITION REGISTRY
# ============================================================================

# Generate Phase 5 transposition variants
def _generate_phase5_transpositions():
    """Generate Phase 5 transposition family variants"""
    variants = []
    
    # Keyword columnar (6 speculative keywords)
    keywords = ["beale", "lynchburg", "bedford", "virginia", "liberty", "treasure"]
    for kw in keywords:
        variants.append(KeywordColumnar(kw))
    
    # Numeric columnar with random permutations (3 variants)
    # Use small set of pre-defined permutations for reproducibility
    # K=5: [2,4,1,0,3], K=7: [3,1,5,0,2,6,4], K=11: [5,2,8,1,10,3,7,0,9,4,6]
    variants.append(ColumnarTransposition(6))
    variants.append(ColumnarTransposition(8))
    variants.append(ColumnarTransposition(11))
    
    # Route ciphers: W in {10,13,20,26,40} x 3 patterns = 15
    widths = [10, 13, 20, 26, 40]
    patterns = ['spiral_cw', 'spiral_ccw', 'diagonal']
    for w in widths:
        for p in patterns:
            variants.append(RectangleFill(w, p))
    
    # Double transposition: limited combinations (6)
    # columnar(K1) + columnar(K2)
    for k1, k2 in [(5, 7), (7, 11), (5, 11)]:
        col1 = ColumnarTransposition(k1)
        col2 = ColumnarTransposition(k2)
        variants.append(DoubleTranspositionPhase5(col1, col2))
    
    # every_Nth + columnar
    for n, k in [(2, 5), (2, 7), (3, 7)]:
        nth = EveryNth(n)
        col = ColumnarTransposition(k)
        variants.append(DoubleTranspositionPhase5(nth, col))
    
    return variants


ALL_TRANSPOSITIONS = [
    # Baseline
    NoTransposition(),
    
    # Chunk operations
    ChunkReverse(2),
    ChunkReverse(3),
    ChunkReverse(5),
    ChunkSwap(2),
    ChunkSwap(3),
    ChunkSwap(5),
    
    # Columnar transposition
    ColumnarTransposition(5),
    ColumnarTransposition(7),
    ColumnarTransposition(10),
    ColumnarTransposition(13),
    ColumnarTransposition(15),
    
    # Zigzag
    ZigzagRead(5),
    ZigzagRead(7),
    ZigzagRead(10),
    ZigzagRead(13),
    ZigzagRead(15),
    
    # Every Nth
    EveryNth(2),
    EveryNth(3),
    EveryNth(5),
    EveryNth(7),
    
    # Reverse patterns
    ReverseAll(),
    ReverseHalves(),
    
    # Historical cipher methods (Phase 3)
    RailFenceCipher(2),
    RailFenceCipher(3),
    RailFenceCipher(5),
    ProgressiveOffset(1),
    ProgressiveOffset(3),
    SpiralRead(7),
    SpiralRead(10),
    DiagonalRead(7),
    SkipPattern(2, 3),
    DoubleColumnar(5, 7),
] + _generate_phase5_transpositions()  # Phase 5: 30 new variants


def _generate_two_stage_transpositions():
    """Generate curated two-stage transposition combinations for Phase 7"""
    two_stage = []
    
    # Stage 1: Top route ciphers from Phase 5-6
    stage1_candidates = [
        RectangleFill(13, 'spiral_ccw'),   # rect_w13_spiral_ccw
        RectangleFill(40, 'diagonal'),      # rect_w40_diagonal
        RectangleFill(26, 'spiral_ccw')     # rect_w26_spiral_ccw
    ]
    
    # Stage 2: Classic methods (columnar, chunk, railfence)
    stage2_candidates = [
        ColumnarTransposition(5),
        ColumnarTransposition(7),
        ChunkReverse(3),
        RailFenceCipher(2),
        EveryNth(3)
    ]
    
    # Generate all combinations
    for s1 in stage1_candidates:
        for s2 in stage2_candidates:
            two_stage.append(TwoStageTransposition(s1, s2))
    
    return two_stage


# Add two-stage to registry
ALL_TRANSPOSITIONS = ALL_TRANSPOSITIONS + _generate_two_stage_transpositions()


def get_transposition(name: str) -> Transposition:
    """Get transposition by name"""
    for trans in ALL_TRANSPOSITIONS:
        if trans.name == name:
            return trans
    return NoTransposition()


def list_transpositions():
    """Print all available transpositions"""
    total = len(ALL_TRANSPOSITIONS)
    phase5_start = 34  # After Phase 3 methods
    phase5_count = total - phase5_start if total > phase5_start else 0
    
    print(f"Available transpositions ({total} total):")
    print("\nBaseline:")
    print(f"  - {ALL_TRANSPOSITIONS[0].name}")
    print("\nChunk operations (7):")
    for trans in ALL_TRANSPOSITIONS[1:8]:
        print(f"  - {trans.name}")
    print("\nColumnar transposition (5):")
    for trans in ALL_TRANSPOSITIONS[8:13]:
        print(f"  - {trans.name}")
    print("\nZigzag reading (5):")
    for trans in ALL_TRANSPOSITIONS[13:18]:
        print(f"  - {trans.name}")
    print("\nEvery Nth (4):")
    for trans in ALL_TRANSPOSITIONS[18:22]:
        print(f"  - {trans.name}")
    print("\nReverse patterns (2):")
    for trans in ALL_TRANSPOSITIONS[22:24]:
        print(f"  - {trans.name}")
    print("\nHistorical cipher methods (Phase 3) (10):")
    for trans in ALL_TRANSPOSITIONS[24:phase5_start]:
        print(f"  - {trans.name}")
    
    if phase5_count > 0:
        print(f"\nPhase 5 Advanced ({phase5_count} variants):")
        if phase5_count <= 10:
            for trans in ALL_TRANSPOSITIONS[phase5_start:]:
                print(f"  - {trans.name}")
        else:
            for trans in ALL_TRANSPOSITIONS[phase5_start:phase5_start+5]:
                print(f"  - {trans.name}")
            print(f"  ... and {phase5_count - 5} more")


if __name__ == "__main__":
    # Test the transpositions
    print("=" * 70)
    print("TRANSPOSITION MODULE TEST")
    print("=" * 70)
    
    list_transpositions()
    
    # Test with sample stream
    print("\n" + "=" * 70)
    print("Sample transpositions of 'ABCDEFGHIJKLMNOPQRST':")
    print("=" * 70)
    
    test_stream = "ABCDEFGHIJKLMNOPQRST"
    print(f"Original: {test_stream}\n")
    
    for trans in ALL_TRANSPOSITIONS[:10]:  # Show first 10
        result = trans.apply(test_stream)
        print(f"{trans.name:20s} -> {result}")
    
    print("\n... (+ 14 more transposition methods)")
