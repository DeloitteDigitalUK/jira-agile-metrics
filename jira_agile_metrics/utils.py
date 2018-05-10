import datetime
import os.path

import numpy as np
import pandas as pd
import seaborn as sns

class StatusTypes:
    backlog = 'backlog'
    accepted = 'accepted'
    complete = 'complete'

def extend_dict(d, e):
    r = d.copy()
    r.update(e)
    return r

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

def to_days_since_epoch(d):
    return (d - datetime.datetime(1970, 1, 1)).days

def set_chart_context(context):
    sns.set_context(context)

def set_chart_style(style="whitegrid", despine=True):
    sns.set_style(style)
    if despine:
        sns.despine()
