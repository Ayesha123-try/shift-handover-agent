"""Read-only access to the plant data. Nothing in this module writes files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SYNTHETIC = DATA / "synthetic"
RAW = DATA / "raw"
SOPS = DATA / "sops"
REPORTS = ROOT / "reports"
DRAFTS = ROOT / "drafts" / "work_orders"
LOGS = ROOT / "logs"

SHIFT_ORDER = {"early": 0, "late": 1, "night": 2}


@lru_cache
def config() -> dict:
    return json.loads((ROOT / "config" / "plant_assumptions.json").read_text(encoding="utf-8"))


@lru_cache
def production_log() -> pd.DataFrame:
    return pd.read_csv(SYNTHETIC / "production_log.csv")


@lru_cache
def downtime_events() -> pd.DataFrame:
    return pd.read_csv(SYNTHETIC / "downtime_events.csv", keep_default_na=False)


@lru_cache
def work_orders() -> pd.DataFrame:
    df = pd.read_csv(SYNTHETIC / "work_orders.csv", keep_default_na=False)
    df["repair_min"] = df["repair_min"].astype(float)
    return df


@lru_cache
def shift_notes() -> pd.DataFrame:
    return pd.read_csv(SYNTHETIC / "shift_notes.csv", keep_default_na=False)


@lru_cache
def rul_predictions() -> pd.DataFrame:
    return pd.read_csv(SYNTHETIC / "rul_predictions.csv")


@lru_cache
def ai4i() -> tuple[pd.DataFrame, str]:
    """Return the AI4I data and a label saying where it came from.

    Put the real public file at data/raw/ai4i2020.csv to use it. Otherwise a
    synthetic stand-in with the same columns and failure rules is used.
    """
    real = RAW / "ai4i2020.csv"
    if real.exists():
        return pd.read_csv(real), "AI4I 2020 Predictive Maintenance Dataset (UCI, public)"
    return (
        pd.read_csv(SYNTHETIC / "ai4i_sample.csv"),
        "SYNTHETIC stand-in in the AI4I 2020 schema (add data/raw/ai4i2020.csv for the real data)",
    )


def in_window(df: pd.DataFrame, start_date: str | None, end_date: str | None, col: str = "shift_date") -> pd.DataFrame:
    """Filter rows whose date column is within [start_date, end_date] (ISO strings, inclusive)."""
    if start_date:
        df = df[df[col] >= start_date]
    if end_date:
        df = df[df[col] <= end_date]
    return df


def for_line(df: pd.DataFrame, line: str | None) -> pd.DataFrame:
    if line and line.upper() != "ALL":
        df = df[df["line"] == line.upper()]
    return df
