import datetime
import os.path

import numpy as np
import pandas as pd
import seaborn as sns

def to_json_string(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if value in (None, np.NaN, pd.NaT):
        return ""

    try:
        return str(value)
    except TypeError:
        return value

def get_extension(filename):
    return os.path.splitext(filename)[1].lower()

def to_datetime(date):
    """Turn a date into a datetime at midnight.
    """
    return datetime.datetime.combine(date, datetime.datetime.min.time())

def to_days_since_epoch(d):
    return (d - datetime.datetime(1970, 1, 1)).days

def set_chart_context(context="talk"):
    sns.set_context(context)

def set_chart_style(style="darkgrid"):
    sns.set_style(style)
