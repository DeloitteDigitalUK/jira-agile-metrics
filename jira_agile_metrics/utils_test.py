import datetime
import numpy as np
import pandas as pd

from .utils import (
    get_extension,
    to_json_string,
    to_days_since_epoch,
    extend_dict
)

def test_extend_dict():
    assert extend_dict({'one': 1}, {'two': 2}) == {'one': 1, 'two': 2}

def test_get_extension():
    assert get_extension("foo.csv") == ".csv"
    assert get_extension("/path/to/foo.csv") == ".csv"
    assert get_extension("\\path\\to\\foo.csv") == ".csv"
    assert get_extension("foo") == ""
    assert get_extension("foo.CSV") == ".csv"

def test_to_json_string():
    assert to_json_string(1) == "1"
    assert to_json_string("foo") == "foo"
    assert to_json_string(None) == ""
    assert to_json_string(np.NaN) == ""
    assert to_json_string(pd.NaT) == ""
    assert to_json_string(pd.Timestamp(2018, 2, 1)) == "2018-02-01"

def test_to_days_since_epoch():
    assert to_days_since_epoch(datetime.datetime(1970, 1, 1)) == 0
    assert to_days_since_epoch(datetime.datetime(1970, 1, 15)) == 14
