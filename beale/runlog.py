"""Run logging + preregistration enforcement.

Every solver invocation against a REAL cipher must carry a preregistered
criteria record (what would count as signal, decided before the run).
Synthetic-target runs are unrestricted. Logs land in runs/ as JSON.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

RUNS_DIR = Path("runs")

REAL_TARGETS = {"c1", "c2", "c3"}


class PreregistrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Criteria:
    """Preregistered success criteria for a real-cipher run."""

    solver: str
    target: str
    statements: tuple[str, ...]  # human-readable, decided before the run

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()
        ).hexdigest()[:12]


@dataclass
class RunRecord:
    solver: str
    target: str
    params: dict
    seed: int | None = None
    criteria: dict | None = None
    results: dict = field(default_factory=dict)
    started: float = field(default_factory=time.time)

    def finish(self, **results) -> Path:
        self.results.update(results)
        RUNS_DIR.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime(self.started))
        h = hashlib.sha256(
            json.dumps(self.params, sort_keys=True, default=str).encode()
        ).hexdigest()[:8]
        path = RUNS_DIR / f"{stamp}_{self.solver}_{h}.json"
        payload = asdict(self)
        payload["elapsed_s"] = round(time.time() - self.started, 2)
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path


def start_run(
    solver: str, target: str, params: dict,
    seed: int | None = None, criteria: Criteria | None = None,
) -> RunRecord:
    if target.lower() in REAL_TARGETS and criteria is None:
        raise PreregistrationError(
            f"run of {solver!r} against real cipher {target!r} requires "
            "preregistered Criteria (decide what counts as signal first)"
        )
    return RunRecord(
        solver=solver, target=target, params=params, seed=seed,
        criteria=asdict(criteria) | {"digest": criteria.digest()} if criteria else None,
    )
