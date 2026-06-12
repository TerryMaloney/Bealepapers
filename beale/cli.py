"""Command-line interface: verify / search / report / fetch."""

from __future__ import annotations

import argparse
import sys

from .corpus import CACHE_DIR
from .data import load_beale
from .diagnostics import randomness_report
from .engine import DecodeConfig, decode
from .keytext import from_doi
from .ngrams import Quadgrams
from .oracle import verify_cipher2


def cmd_verify(args) -> int:
    data = load_beale(args.input)
    report = verify_cipher2(data)
    print(f"Cipher 2 oracle: {report.matches}/{report.total} = {report.exact_pct:.1%}"
          f"  (out-of-range: {report.n_oor})")
    print(f"decoded opening: {report.decoded[:60]}")
    if report.mismatches[:10]:
        print("first mismatches (pos, got, want):",
              ", ".join(f"{p}:{g}->{w}" for p, g, w in report.mismatches[:10]))
    print("PASS" if report.passed else "FAIL (threshold 90%)")
    return 0 if report.passed else 1


def cmd_search(args) -> int:
    from .search import run_search

    data = load_beale(args.input)
    keytexts = None
    if args.web:
        from .fetch import fetch_gutenberg, fetch_stone_doi
        from .search import _default_keytexts

        def with_web():
            try:
                yield fetch_stone_doi()
            except Exception as e:  # network optional; report and continue
                print(f"[web] stone DOI fetch failed: {e}", file=sys.stderr)
            for gid in args.gutenberg:
                try:
                    yield fetch_gutenberg(gid)
                except Exception as e:
                    print(f"[web] gutenberg {gid} fetch failed: {e}", file=sys.stderr)
            yield from _default_keytexts(data)

        keytexts = with_web()

    ciphers = tuple(c.strip() for c in args.ciphers.split(","))
    results = run_search(data, ciphers=ciphers, keytexts=keytexts)
    _print_ranked(results[: args.top])
    print(f"\n{len(results)} new candidates scored; checkpoint: {CACHE_DIR / 'search_ckpt.jsonl'}")
    return 0


def cmd_report(args) -> int:
    data = load_beale(args.input)
    quad = Quadgrams.load()
    numbers = data.cipher_for(args.cipher)
    key = from_doi(data)  # report is against the DOI by default
    rep = randomness_report(numbers, key.tokens, quad)
    res = decode(numbers, key.tokens, DecodeConfig())
    print(f"{args.cipher} vs {key.id}: quadgram={rep.quadgram:.3f} "
          f"z={rep.quadgram_z:+.2f} ioc={rep.ioc:.4f} "
          f"incremental={rep.incremental_fraction:.3f} oor={res.n_oor}/{res.n_total}")
    for r in rep.alphabetical_runs:
        print(f"  alphabetical run at {r.start}: {r.text!r}")
    print(f"verdict: {rep.verdict}")
    print(f"decode preview: {rep.decoded[:120]}")
    return 0


def cmd_rank(args) -> int:
    from .search import load_ranked

    _print_ranked(load_ranked(cipher=args.cipher, top=args.top))
    return 0


def _print_ranked(cands) -> None:
    print(f"{'cipher':6s} {'quadgram':>9s} {'ioc':>7s} {'dict':>5s} {'extr':5s} key / preview")
    for c in cands:
        print(f"{c.cipher:6s} {c.quadgram:9.3f} {c.ioc:7.4f} {c.dict_coverage:5.2f} "
              f"{c.extraction:5s} {c.key_id}")
        print(f"{'':36s}{c.preview[:80]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="beale", description=__doc__)
    ap.add_argument("--input", default="beale_papers.txt")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("verify", help="run the Cipher 2 oracle (exit 1 on regression)")

    p = sub.add_parser("search", help="sweep key texts over unsolved ciphers")
    p.add_argument("--ciphers", default="C1,C3")
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--web", action="store_true", help="also fetch web key texts")
    p.add_argument("--gutenberg", type=int, nargs="*", default=[])

    p = sub.add_parser("report", help="diagnostics for a cipher against the DOI")
    p.add_argument("--cipher", default="C1", choices=["C1", "C2", "C3"])

    p = sub.add_parser("rank", help="show ranked candidates from the checkpoint")
    p.add_argument("--cipher", default=None)
    p.add_argument("--top", type=int, default=25)

    args = ap.parse_args(argv)
    return {"verify": cmd_verify, "search": cmd_search,
            "report": cmd_report, "rank": cmd_rank}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
