"""
CSV-backed data source for offline operation.
Provides precomputed cycle-time data for calculators via QueryManager.
"""
from __future__ import annotations

from typing import Optional, Dict
import pandas as pd

from .offline_loader import load_cycle_data_from_file


class CSVDataSource:
    def __init__(self, path: str, settings: Dict):
        self._cycle_df = load_cycle_data_from_file(path, settings)

    def get_precomputed_cycle_data(self) -> Optional[pd.DataFrame]:
        return self._cycle_df
