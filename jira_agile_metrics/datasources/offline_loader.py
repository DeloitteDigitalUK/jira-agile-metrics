"""
Offline data loader to build a Cycle Time DataFrame from exported files
(cycletime.csv, .json, or .xlsx) without querying JIRA.

This prepares the minimal columns required by downstream calculators and
AI context generation:
- key, url, summary, issue_type, status, resolution
- cycle step columns (from settings["cycle"]) as datetime64
- committed_column, done_column
- completed_timestamp (datetime64)
- cycle_time (timedelta64)
- blocked_days (int) if available
- impediments (object: list) optional
"""

from __future__ import annotations

import json
import logging
import os
import warnings
from typing import Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

HEADER_RENAME = {
    "ID": "key",
    "Link": "url",
    "Name": "summary",
    "Type": "issue_type",
    "Status": "status",
    "Resolution": "resolution",
    "Blocked Days": "blocked_days",
}


def _parse_dates_robust(date_series: pd.Series) -> pd.Series:
    """
    Robust date parsing that handles multiple formats:
    - ISO format (YYYY-MM-DD) - tool-generated CSV files
    - DD/MM/YYYY format - European/UK format
    - MM/DD/YYYY format - US format

    Uses format detection and fallback parsing to maximize compatibility.
    """
    if date_series.isna().all():
        return pd.to_datetime(date_series, errors="coerce")

    # Replace empty strings with NaN for consistent handling
    date_series = date_series.replace("", np.nan)

    # Get non-null values for testing
    non_null_series = date_series.dropna()
    if len(non_null_series) == 0:
        return pd.to_datetime(date_series, errors="coerce")

    # Helper function to check if parsing was successful
    def _parsing_success_rate(result: pd.Series) -> float:
        non_null_input = len(non_null_series)
        valid_parsed = len(result.dropna())
        return valid_parsed / non_null_input if non_null_input > 0 else 0

    # Try ISO format first (tool default output: YYYY-MM-DD)
    try:
        result = pd.to_datetime(date_series, format="%Y-%m-%d", errors="coerce")
        if _parsing_success_rate(result) > 0.8:  # 80% success threshold
            logger.debug("Parsed dates using ISO format (YYYY-MM-DD)")
            return result
    except (ValueError, TypeError):
        pass

    # Try DD/MM/YYYY format (European/UK)
    try:
        result = pd.to_datetime(date_series, format="%d/%m/%Y", errors="coerce")
        if _parsing_success_rate(result) > 0.8:
            logger.debug("Parsed dates using DD/MM/YYYY format")
            return result
    except (ValueError, TypeError):
        pass

    # Try MM/DD/YYYY format (US)
    try:
        result = pd.to_datetime(date_series, format="%m/%d/%Y", errors="coerce")
        if _parsing_success_rate(result) > 0.8:
            logger.debug("Parsed dates using MM/DD/YYYY format")
            return result
    except (ValueError, TypeError):
        pass

    # Try default pandas parsing (handles many formats automatically)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            result = pd.to_datetime(date_series, errors="coerce")
        if _parsing_success_rate(result) > 0.5:  # Lower threshold for default parsing
            logger.debug("Parsed dates using pandas default parsing")
            return result
    except (ValueError, TypeError):
        pass

    # Final fallback with dayfirst=True for ambiguous cases
    logger.warning("Using fallback date parsing with dayfirst=True")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.to_datetime(date_series, errors="coerce", dayfirst=True)


def _read_cycle_file(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".json":
        # CycleTimeCalculator.write() writes a JSON array of rows including header row
        values = json.load(open(path, "r"))
        if not values:
            return pd.DataFrame()
        header = values[0]
        rows = values[1:]
        return pd.DataFrame(rows, columns=header)
    if ext in (".xlsx", ".xls"):
        # Expect a single sheet when exported by our tool
        return pd.read_excel(path)
    raise ValueError(f"Unsupported cycle data file type: {ext}")


def load_cycle_data_from_file(path: str, settings: Dict) -> pd.DataFrame:
    """
    Load exported cycle time data and transform it to match the in-memory
    structure produced by `CycleTimeCalculator.run()`.
    """
    df = _read_cycle_file(path)
    if df.empty:
        return df

    # Rename headers to internal column names
    df = df.rename(columns=HEADER_RENAME)

    # Identify cycle stage names from settings
    cycle_names: List[str] = [s["name"] for s in settings["cycle"]]
    committed = settings["committed_column"]
    done = settings["done_column"]

    # Ensure all expected columns exist (some may be missing in older exports)
    base_cols = [
        "key",
        "url",
        "summary",
        "issue_type",
        "status",
        "resolution",
    ]
    for col in base_cols:
        if col not in df.columns:
            df[col] = None

    # Parse date columns for each cycle step with format detection
    for col in cycle_names:
        if col in df.columns:
            df[col] = _parse_dates_robust(df[col])
        else:
            df[col] = pd.NaT

    # Ensure blocked_days exists as integer
    if "blocked_days" not in df.columns:
        df["blocked_days"] = 0
    df["blocked_days"] = pd.to_numeric(df["blocked_days"], errors="coerce").fillna(0).astype(int)

    # Add impediments column placeholder (list) for compatibility
    if "impediments" not in df.columns:
        df["impediments"] = [[] for _ in range(len(df))]

    # Compute completed_timestamp and cycle_time if possible
    df["completed_timestamp"] = _parse_dates_robust(df[done])
    if committed in df.columns and done in df.columns:
        df["cycle_time"] = df[done] - df[committed]
    else:
        df["cycle_time"] = pd.NaT

    # Column order to mirror calculate_cycle_times() output
    # [key, url, issue_type, summary, status, resolution]
    # + attributes (keep any extras, preserving original order if present)
    # + query_attribute (if configured)
    # + [cycle_time, completed_timestamp, blocked_days, impediments]
    # + cycle_names

    # Determine configured attributes/query_attribute to preserve
    attribute_names = sorted(settings.get("attributes", {}).keys())
    query_attr = settings.get("query_attribute")

    ordered_cols: List[str] = (
        ["key", "url", "issue_type", "summary", "status", "resolution"]
        + [c for c in attribute_names if c in df.columns]
        + ([query_attr] if query_attr and query_attr in df.columns else [])
        + ["cycle_time", "completed_timestamp", "blocked_days", "impediments"]
        + cycle_names
    )

    # Add any remaining columns to avoid data loss
    remaining = [c for c in df.columns if c not in ordered_cols]
    df = df[ordered_cols + remaining]

    return df
