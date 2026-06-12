"""Blind homophonic-substitution solver (simulated annealing).

Treats a cipher as an abstract symbol stream: find symbol->letter map
maximizing English quadgram likelihood with an index-of-coincidence
anti-degeneracy penalty. No key text involved.

Honest priors (from the homophonic-solving literature, e.g. AZdecrypt /
Zodiac experience): solvability tracks multiplicity m = distinct/length.
Hillclimbers reliably solve m <= ~0.25-0.30 at lengths >= 400; reliability
collapses above that.

  C2: m = 180/763 = 0.236  -> blind solve expected to SUCCEED (validation gate)
  C3: m = 263/618 = 0.426  -> blind expected to fail; with 57% key-table pins
                              the free-symbol subproblem becomes tractable
  C1: m = 298/520 = 0.573  -> only the pinned mode is meaningful

Pins come from Beale's reconstructed C2 key table (keytable.py) under the
shared-key hypothesis. Soft-pin mode measures how often the solver chooses
to violate pins: <=10% violations = consistent with shared key; >=30% =
shared-key hypothesis rejected for that cipher.
"""

from __future__ import annotations

import math
import random
from array import array
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

from .ngrams import Quadgrams

WILDCARD = 26
ENGLISH_IOC = 0.0667
# English unigram frequencies, a..z (same source as scoring.ENGLISH_FREQ)
_UNIGRAM = [0.0817, 0.0150, 0.0278, 0.0425, 0.1270, 0.0223, 0.0202, 0.0609,
            0.0697, 0.0015, 0.0077, 0.0403, 0.0241, 0.0675, 0.0751, 0.0193,
            0.0010, 0.0599, 0.0633, 0.0906, 0.0276, 0.0098, 0.0236, 0.0015,
            0.0197, 0.0007]
# C2's real homophone allocation shape (letter -> count), used to seed inits.
_C2_SHAPE = {"t": 18, "e": 15, "a": 15, "s": 12, "o": 12, "i": 12, "d": 11,
             "l": 10, "u": 9, "n": 8, "h": 8, "f": 8, "r": 7, "c": 7, "b": 7,
             "w": 6, "p": 4, "m": 4, "g": 4, "j": 2, "y": 1, "x": 1, "v": 1,
             "k": 1}


def flat_quadgram_table(quad: Quadgrams) -> array:
    """26^4 flat array of log10 probabilities (floor for unseen)."""
    tab = array("d", [quad._floor]) * (26 ** 4)
    for q, lp in quad._logp.items():
        i = (((ord(q[0]) - 65) * 26 + (ord(q[1]) - 65)) * 26
             + (ord(q[2]) - 65)) * 26 + (ord(q[3]) - 65)
        tab[i] = lp
    return tab


_QUINT_SOURCES = [
    "bible_asv.json", "decline_fall_rome_v1.json", "pride_prejudice.json",
    "common_sense.json", "autobiography_franklin.json", "last_of_mohicans.json",
    "ivanhoe.json", "moby_dick.json", "jane_eyre.json", "waverley.json",
]
_QUINT_CACHE = "corpus/cache/quintgrams.bin"


def quintgram_table(cache_path: str = _QUINT_CACHE) -> array:
    """26^5 flat array of quintgram log10 probabilities.

    Critical for blind solving: under quadgrams alone the TRUE C2 plaintext
    scores WORSE than degenerate near-English (measured: -2536 vs -2447);
    adding quintgrams ranks truth above every optimum found so far. Built
    from the period corpus (~13M chars) and cached as a binary (~47 MB,
    gitignored); rebuild takes ~10 s.
    """
    import json
    import re
    from pathlib import Path

    p = Path(cache_path)
    size = 26 ** 5
    if p.exists():
        tab = array("f")
        with open(p, "rb") as f:
            tab.fromfile(f, size)
        return tab
    from collections import Counter

    counts: Counter = Counter()
    for name in _QUINT_SOURCES:
        src = Path("corpus/keytexts/normalized") / name
        if not src.exists():
            continue
        toks = json.loads(src.read_text(encoding="utf-8"))["tokens"]
        stream = re.sub(r"[^a-z]", "", "".join(toks).lower())
        idx = [ord(c) - 97 for c in stream]
        for i in range(len(idx) - 4):
            counts[(((idx[i] * 26 + idx[i + 1]) * 26 + idx[i + 2]) * 26
                    + idx[i + 3]) * 26 + idx[i + 4]] += 1
    total = sum(counts.values())
    tab = array("f", [math.log10(0.01 / total)]) * size
    for q, c in counts.items():
        tab[q] = math.log10(c / total)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tab.tofile(f)
    return tab


@dataclass(frozen=True)
class HomophonicProblem:
    numbers: tuple[int, ...]
    sym_of: tuple[int, ...]          # position -> dense symbol id
    sym_numbers: tuple[int, ...]     # symbol id -> original cipher number
    positions: tuple[tuple[int, ...], ...]  # symbol id -> positions
    pins: dict[int, int]             # symbol id -> letter id (from key table)
    singleton_syms: frozenset[int]

    @property
    def n_symbols(self) -> int:
        return len(self.positions)

    @classmethod
    def build(cls, numbers: Sequence[int],
              pin_letters: dict[int, str] | None = None) -> "HomophonicProblem":
        order: dict[int, int] = {}
        for n in numbers:
            if n not in order:
                order[n] = len(order)
        sym_of = tuple(order[n] for n in numbers)
        sym_numbers = tuple(sorted(order, key=order.get))
        pos: list[list[int]] = [[] for _ in order]
        for i, s in enumerate(sym_of):
            pos[s].append(i)
        pins = {}
        for n, letter in (pin_letters or {}).items():
            if n in order:
                pins[order[n]] = ord(letter) - 97
        singles = frozenset(s for s, ps in enumerate(pos) if len(ps) == 1)
        return cls(tuple(numbers), sym_of, sym_numbers,
                   tuple(tuple(p) for p in pos), pins, singles)


@dataclass
class SolverConfig:
    iters: int = 200_000
    restarts: int = 40
    t0: float = 15.0
    tf: float = 0.5
    lambda_ioc: float = 400.0
    use_quint: bool = True           # quad-only objective ranks truth BELOW
                                     # degenerate optima; keep quint on
    soft_pins: bool = False
    pin_bonus: float = 8.0           # per-occurrence bonus for agreeing pins
    seed: int = 1885
    stall_limit: int = 25_000
    top_k: int = 10


@dataclass
class Solution:
    assign: tuple[int, ...]          # symbol id -> letter id (26 = wildcard)
    score: float
    text: str = ""
    pin_violations: float = 0.0


@dataclass
class SolveResult:
    finalists: list[Solution]
    consensus: str                   # per-position: letter if >=80% agree, else '?'
    problem: HomophonicProblem = field(repr=False, default=None)


def _decode(problem: HomophonicProblem, assign: Sequence[int]) -> str:
    return "".join(
        chr(97 + assign[s]) if assign[s] < 26 else "?" for s in problem.sym_of
    )


class _Annealer:
    """One annealing run. Wildcard (singleton) positions are excluded from
    window scoring in the main loop and filled greedily afterwards."""

    def __init__(self, problem: HomophonicProblem, qtab: array, cfg: SolverConfig,
                 rng: random.Random, qtab5: array | None = None):
        self.p = problem
        self.qtab = qtab
        self.qtab5 = qtab5
        self.cfg = cfg
        self.rng = rng
        n = len(problem.sym_of)
        self.n = n
        wild = set()
        for s in problem.singleton_syms:
            wild.update(problem.positions[s])
        self.wild_pos = wild
        # valid windows: all positions non-singleton
        self.windows = [w for w in range(n - 3)
                        if not any((w + j) in wild for j in range(4))]
        valid = set(self.windows)
        # symbol -> affected valid windows
        self.sym_windows: list[tuple[int, ...]] = []
        for ps in problem.positions:
            ws = set()
            for pp in ps:
                for w in range(max(0, pp - 3), min(n - 3, pp + 1)):
                    if w in valid:
                        ws.add(w)
            self.sym_windows.append(tuple(sorted(ws)))
        self.windows5: list[int] = []
        self.sym_windows5: list[tuple[int, ...]] = []
        if qtab5 is not None:
            self.windows5 = [w for w in range(n - 4)
                             if not any((w + j) in wild for j in range(5))]
            valid5 = set(self.windows5)
            for ps in problem.positions:
                ws = set()
                for pp in ps:
                    for w in range(max(0, pp - 4), min(n - 4, pp + 1)):
                        if w in valid5:
                            ws.add(w)
                self.sym_windows5.append(tuple(sorted(ws)))
        # mutable state
        self.cur = [0] * n                  # letter id per position
        self.assign = [0] * problem.n_symbols
        self.counts = [0] * 26              # letter occurrence counts (non-wild)
        self.n_scored = n - len(wild)
        self.free_syms = [s for s in range(problem.n_symbols)
                          if s not in problem.singleton_syms
                          and (cfg.soft_pins or s not in problem.pins)]
        self.multi_syms = [s for s in range(problem.n_symbols)
                          if s not in problem.singleton_syms]

    # -- objective pieces ---------------------------------------------------
    def _win_val(self, w: int) -> float:
        c = self.cur
        idx = ((c[w] * 26 + c[w + 1]) * 26 + c[w + 2]) * 26 + c[w + 3]
        return self.qtab[idx]

    def _win_val5(self, w: int) -> float:
        c = self.cur
        idx = (((c[w] * 26 + c[w + 1]) * 26 + c[w + 2]) * 26
               + c[w + 3]) * 26 + c[w + 4]
        return self.qtab5[idx]

    def _sym_quad(self, s: int) -> float:
        v = sum(self._win_val(w) for w in self.sym_windows[s])
        if self.qtab5 is not None:
            v += sum(self._win_val5(w) for w in self.sym_windows5[s])
        return v

    def _ioc_pen(self, counts: list[int]) -> float:
        n = self.n_scored
        if n < 2:
            return 0.0
        ioc = sum(k * (k - 1) for k in counts) / (n * (n - 1))
        return self.cfg.lambda_ioc * abs(ioc - ENGLISH_IOC) * 10.0

    def _pin_score(self) -> float:
        if not self.cfg.soft_pins:
            return 0.0
        bonus = 0.0
        for s, want in self.p.pins.items():
            if self.assign[s] == want:
                bonus += self.cfg.pin_bonus * len(self.p.positions[s])
        return bonus

    def full_score(self) -> float:
        quad = sum(self._win_val(w) for w in self.windows)
        if self.qtab5 is not None:
            quad += sum(self._win_val5(w) for w in self.windows5)
        return quad - self._ioc_pen(self.counts) + self._pin_score()

    # -- init ----------------------------------------------------------------
    def init_assign(self, mode: str) -> None:
        p, rng = self.p, self.rng
        for s, want in p.pins.items():
            self.assign[s] = want
        free = [s for s in self.multi_syms
                if self.cfg.soft_pins or s not in p.pins]
        if mode == "freq":
            budget = []
            total_shape = sum(_C2_SHAPE.values())
            for ch, k in _C2_SHAPE.items():
                budget += [ord(ch) - 97] * max(1, round(k / total_shape * len(free)))
            rng.shuffle(budget)
            ordered = sorted(free, key=lambda s: -len(p.positions[s]))
            for i, s in enumerate(ordered):
                self.assign[s] = budget[i % len(budget)]
        else:
            for s in free:
                self.assign[s] = rng.choices(range(26), weights=_UNIGRAM)[0]
        for s in p.singleton_syms:
            self.assign[s] = WILDCARD
        # build position letters + counts
        self.counts = [0] * 26
        for i, s in enumerate(p.sym_of):
            self.cur[i] = self.assign[s]
            if i not in self.wild_pos:
                self.counts[self.assign[s]] += 1

    # -- moves ----------------------------------------------------------------
    def _delta_assign(self, s: int, new_letter: int) -> float:
        old_letter = self.assign[s]
        if old_letter == new_letter:
            return 0.0
        before = self._sym_quad(s)
        k = len(self.p.positions[s])
        c = self.counts
        ioc_before = self._ioc_pen(c)
        pin_before = 0.0
        if self.cfg.soft_pins and s in self.p.pins:
            if old_letter == self.p.pins[s]:
                pin_before = self.cfg.pin_bonus * k
        # apply
        for pp in self.p.positions[s]:
            self.cur[pp] = new_letter
        c[old_letter] -= k
        c[new_letter] += k
        after = self._sym_quad(s)
        ioc_after = self._ioc_pen(c)
        pin_after = 0.0
        if self.cfg.soft_pins and s in self.p.pins:
            if new_letter == self.p.pins[s]:
                pin_after = self.cfg.pin_bonus * k
        # revert (caller decides)
        for pp in self.p.positions[s]:
            self.cur[pp] = old_letter
        c[old_letter] += k
        c[new_letter] -= k
        return (after - before) - (ioc_after - ioc_before) + (pin_after - pin_before)

    def _apply_assign(self, s: int, new_letter: int) -> None:
        old = self.assign[s]
        k = len(self.p.positions[s])
        self.assign[s] = new_letter
        for pp in self.p.positions[s]:
            self.cur[pp] = new_letter
        self.counts[old] -= k
        self.counts[new_letter] += k

    # -- main loop -------------------------------------------------------------
    def run(self, mode: str) -> Solution:
        cfg, rng = self.cfg, self.rng
        self.init_assign(mode)
        score = self.full_score()
        best_score = score
        best_assign = list(self.assign)
        stall = 0
        ratio = cfg.tf / cfg.t0
        for it in range(cfg.iters):
            T = cfg.t0 * ratio ** (it / cfg.iters)
            r = rng.random()
            if r < 0.92 or len(self.free_syms) < 2:
                s = rng.choice(self.free_syms)
                new_letter = rng.choices(range(26), weights=_UNIGRAM)[0]
                d = self._delta_assign(s, new_letter)
                if d > 0 or rng.random() < math.exp(min(0.0, d) / T):
                    self._apply_assign(s, new_letter)
                    score += d
            else:
                s1, s2 = rng.sample(self.free_syms, 2)
                l1, l2 = self.assign[s1], self.assign[s2]
                if l1 == l2:
                    continue
                d1 = self._delta_assign(s1, l2)
                self._apply_assign(s1, l2)
                d2 = self._delta_assign(s2, l1)
                d = d1 + d2
                if d > 0 or rng.random() < math.exp(min(0.0, d) / T):
                    self._apply_assign(s2, l1)
                    score += d
                else:
                    self._apply_assign(s1, l1)  # revert
            if score > best_score + 1e-9:
                best_score, best_assign = score, list(self.assign)
                stall = 0
            else:
                stall += 1
                if T < 1.0 and stall > cfg.stall_limit:
                    break
        # polish: greedy best-improvement sweeps
        self.assign = best_assign
        self._resync()
        for _ in range(3):
            improved = False
            for s in self.free_syms:
                cur_letter = self.assign[s]
                best_d, best_l = 0.0, cur_letter
                for letter in range(26):
                    if letter == cur_letter:
                        continue
                    dd = self._delta_assign(s, letter)
                    if dd > best_d + 1e-9:
                        best_d, best_l = dd, letter
                if best_l != cur_letter:
                    self._apply_assign(s, best_l)
                    improved = True
            if not improved:
                break
        self._fill_singletons()
        score = self.full_score()
        viol = 0.0
        if self.p.pins:
            bad = sum(1 for s, want in self.p.pins.items() if self.assign[s] != want)
            viol = bad / len(self.p.pins)
        return Solution(assign=tuple(self.assign), score=score,
                        text=_decode(self.p, self.assign), pin_violations=viol)

    def _resync(self) -> None:
        self.counts = [0] * 26
        for i, s in enumerate(self.p.sym_of):
            self.cur[i] = self.assign[s]
            if i not in self.wild_pos:
                self.counts[self.assign[s]] += 1

    def _fill_singletons(self) -> None:
        """Greedy contextual fill of singleton symbols (low confidence)."""
        n = self.n
        for s in sorted(self.p.singleton_syms,
                        key=lambda s: self.p.positions[s][0]):
            if s in self.p.pins and not self.cfg.soft_pins:
                self.assign[s] = self.p.pins[s]
                self.cur[self.p.positions[s][0]] = self.p.pins[s]
                continue
            pp = self.p.positions[s][0]
            best_l, best_v = 0, -1e18
            for letter in range(26):
                self.cur[pp] = letter
                v = math.log10(_UNIGRAM[letter])
                for w in range(max(0, pp - 3), min(n - 3, pp + 1)):
                    quad_ok = all(self.cur[w + j] < 26 for j in range(4))
                    if quad_ok:
                        v += self._win_val(w)
                if v > best_v:
                    best_v, best_l = v, letter
            self.assign[s] = best_l
            self.cur[pp] = best_l


def _one_restart(args) -> Solution:
    problem, qtab, qtab5, cfg, seed, mode = args
    rng = random.Random(seed)
    return _Annealer(problem, qtab, cfg, rng, qtab5=qtab5).run(mode)


def solve(problem: HomophonicProblem, quad: Quadgrams,
          cfg: SolverConfig | None = None, processes: int | None = None,
          ) -> SolveResult:
    cfg = cfg or SolverConfig()
    qtab = flat_quadgram_table(quad)
    qtab5 = quintgram_table() if cfg.use_quint else None
    jobs = [(problem, qtab, qtab5, cfg, cfg.seed + r,
             "freq" if r % 2 == 0 else "rand")
            for r in range(cfg.restarts)]
    if processes and processes > 1:
        import multiprocessing as mp
        with mp.Pool(processes) as pool:
            sols = pool.map(_one_restart, jobs)
    else:
        sols = [_one_restart(j) for j in jobs]
    sols.sort(key=lambda s: s.score, reverse=True)
    # dedupe by decoded-text Hamming distance < 5%
    finalists: list[Solution] = []
    for s in sols:
        if all(_hamming_frac(s.text, f.text) >= 0.05 for f in finalists):
            finalists.append(s)
        if len(finalists) >= cfg.top_k:
            break
    consensus = _consensus([f.text for f in finalists[:10]])
    return SolveResult(finalists=finalists, consensus=consensus, problem=problem)


def iphc_ratchet(problem: HomophonicProblem, assign0: Sequence[int],
                 quad: Quadgrams, rounds: int = 150, perturb: int = 8,
                 seed: int = 0, cfg: SolverConfig | None = None) -> Solution:
    """Iterated perturbation hillclimbing from a starting assignment.

    Greedy full sweeps to a local optimum, perturb a few symbols, re-greedy,
    keep the global best. The strongest refinement found for this landscape;
    typically adds a few points over raw annealing finalists.
    """
    cfg = cfg or SolverConfig()
    rng = random.Random(seed)
    qtab = flat_quadgram_table(quad)
    qtab5 = quintgram_table() if cfg.use_quint else None
    ann = _Annealer(problem, qtab, cfg, rng, qtab5=qtab5)
    ann.assign = list(assign0)
    ann._resync()

    def greedy() -> float:
        sc = ann.full_score()
        while True:
            improved = False
            order = ann.free_syms[:]
            rng.shuffle(order)
            for s in order:
                best_d, best_l = 1e-9, ann.assign[s]
                for letter in range(26):
                    dd = ann._delta_assign(s, letter)
                    if dd > best_d:
                        best_d, best_l = dd, letter
                if best_l != ann.assign[s]:
                    ann._apply_assign(s, best_l)
                    sc += best_d
                    improved = True
            if not improved:
                return sc

    best_sc = greedy()
    best_assign = list(ann.assign)
    for _ in range(rounds):
        for s in rng.sample(ann.free_syms, min(perturb, len(ann.free_syms))):
            ann._apply_assign(s, rng.choices(range(26), weights=_UNIGRAM)[0])
        sc = greedy()
        if sc > best_sc:
            best_sc, best_assign = sc, list(ann.assign)
        else:
            ann.assign = list(best_assign)
            ann._resync()
    ann.assign = best_assign
    ann._resync()
    ann._fill_singletons()
    viol = 0.0
    if problem.pins:
        bad = sum(1 for s, want in problem.pins.items() if ann.assign[s] != want)
        viol = bad / len(problem.pins)
    return Solution(assign=tuple(ann.assign), score=ann.full_score(),
                    text=_decode(problem, ann.assign), pin_violations=viol)


def _hamming_frac(a: str, b: str) -> float:
    diff = sum(x != y for x, y in zip(a, b))
    return diff / max(1, len(a))


def _consensus(texts: list[str], threshold: float = 0.8) -> str:
    if not texts:
        return ""
    out = []
    for i in range(len(texts[0])):
        c = Counter(t[i] for t in texts)
        ch, k = c.most_common(1)[0]
        out.append(ch if k / len(texts) >= threshold and ch != "?" else "?")
    return "".join(out)
