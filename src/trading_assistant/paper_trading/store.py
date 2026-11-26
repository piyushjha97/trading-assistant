import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, Protocol

from fcntl import LOCK_EX, LOCK_UN, flock
from pydantic import BaseModel, ConfigDict

from trading_assistant.paper_trading.models import PaperTrade, PaperTradePlan


class PaperTradeStore(Protocol):
    def register(self, plan: PaperTradePlan) -> PaperTrade: ...
    def get(self, signal_id: str) -> PaperTrade: ...
    def list(self) -> list[PaperTrade]: ...
    def update(self, signal_id: str, apply: Callable[[PaperTrade], PaperTrade]) -> PaperTrade: ...


class _Journal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    trades: list[PaperTrade]


class JsonPaperTradeStore:
    """Local JSON journal with one document per signal and atomic updates on POSIX."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def register(self, plan: PaperTradePlan) -> PaperTrade:
        with self._locked():
            trades = self._read()
            existing = trades.get(plan.signal_id)
            if existing is not None:
                if existing.plan != plan:
                    raise ValueError("The signal ID already belongs to a different paper plan.")
                return existing
            trade = PaperTrade(plan=plan)
            trades[plan.signal_id] = trade
            self._write(trades)
            return trade

    def get(self, signal_id: str) -> PaperTrade:
        with self._locked():
            return self._read()[signal_id]

    def list(self) -> list[PaperTrade]:
        with self._locked():
            return sorted(
                self._read().values(), key=lambda trade: trade.plan.signal_at, reverse=True,
            )

    def update(self, signal_id: str, apply: Callable[[PaperTrade], PaperTrade]) -> PaperTrade:
        with self._locked():
            trades = self._read()
            trade = trades[signal_id]
            updated = apply(trade)
            if updated.plan != trade.plan:
                raise ValueError("A paper trade's registered plan is immutable.")
            if updated != trade:
                trades[signal_id] = updated
                self._write(trades)
            return updated

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self._path.with_name(f"{self._path.name}.lock")
        with lock_path.open("a") as lock:
            flock(lock, LOCK_EX)
            try:
                yield
            finally:
                flock(lock, LOCK_UN)

    def _read(self) -> dict[str, PaperTrade]:
        try:
            content = self._path.read_bytes()
        except FileNotFoundError:
            return {}
        records = _Journal.model_validate_json(content).trades
        trades = {trade.plan.signal_id: trade for trade in records}
        if len(trades) != len(records):
            raise ValueError("Duplicate signal IDs in the paper-trade journal.")
        return trades

    def _write(self, trades: dict[str, PaperTrade]) -> None:
        journal = _Journal(trades=list(trades.values()))
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self._path.parent, delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            try:
                json.dump(journal.model_dump(mode="json"), handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
                os.replace(temp_path, self._path)
            finally:
                temp_path.unlink(missing_ok=True)
