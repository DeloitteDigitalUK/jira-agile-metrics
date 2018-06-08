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
    return (d - datetime.date(1970, 1, 1)).days

def set_chart_context(context):
    sns.set_context(context)

def set_chart_style(style="whitegrid", despine=True):
    sns.set_style(style)
    if despine:
        sns.despine()

def breakdown_by_month(df, start_column, end_column, key_column, value_column, output_columns=None):
    """If `df` is a DataFrame of items that are valid/active between the
    timestamps stored in `start_column` and `end_column`, and where each item
    is uniquely identified by `key_column` and has a categorical value in
    `value_column`, return a new DataFrame counting the number of items in
    each month broken down by each unique value in `value_column`. To restrict
    (and order) the value columns, pass a list of valid values as `output_columns`.
    """
    
    def align_date(timestamp):
        if timestamp is pd.NaT:
            timestamp = pd.Timestamp.today()
        edge = timestamp.normalize().to_period('M').to_timestamp('D', 'S')
        return edge
    
    breakdown = pd.concat([
        pd.DataFrame(
            index=pd.date_range(align_date(getattr(t, start_column)), align_date(getattr(t, end_column)), freq='MS'),
            data=[[getattr(t, key_column)]],
            columns=[getattr(t, value_column)]
        ) for t in df.itertuples()
    ]).resample('MS').count()

    if output_columns:
        breakdown = breakdown[[s for s in output_columns if s in breakdown.columns]]
    
    return breakdown

def to_bin(value, edges):
    """Pass a list of numbers in `edges` and return which of them `value` falls
    between. If < the first item, return (0, <first>). If > last item, return
    (<last>, None).
    """

    previous = 0
    for v in edges:
        if previous <= value <= v:
            return (previous, v)
        previous = v
    return (previous, None)
