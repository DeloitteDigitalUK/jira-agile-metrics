import datetime
import os.path
from typing import List
from typing import Tuple

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

def breakdown_by_month(df, start_column, end_column, key_column, value_column, output_columns=None, aggfunc='count'):
    """If `df` is a DataFrame of items that are valid/active between the
    timestamps stored in `start_column` and `end_column`, and where each item
    is uniquely identified by `key_column` and has a categorical value in
    `value_column`, return a new DataFrame counting the number of items in
    each month broken down by each unique value in `value_column`. To restrict
    (and order) the value columns, pass a list of valid values as `output_columns`.
    """

    def build_df(t):
        start_date = getattr(t, start_column)
        end_date = getattr(t, end_column)
        key = getattr(t, key_column)
        value = getattr(t, value_column)

        if end_date is pd.NaT:
            end_date = pd.Timestamp.today()

        first_month = start_date.normalize().to_period('M').to_timestamp('D', 'S')
        last_month = end_date.normalize().to_period('M').to_timestamp('D', 'S')

        index = pd.date_range(first_month, last_month, freq='MS')

        return pd.DataFrame(
            index=index,
            data=[[key]],
            columns=[value]
        )

    breakdown = pd.concat([build_df(t) for t in df.itertuples()], sort=True).resample('MS').agg(aggfunc)

    if output_columns:
        breakdown = breakdown[[s for s in output_columns if s in breakdown.columns]]

    return breakdown

def breakdown_by_month_sum_days(df, start_column, end_column, value_column, output_columns=None, aggfunc='sum'):
    """If `df` is a DataFrame of items that are valid/active between the
    timestamps stored in `start_column` and `end_column`, and where each has a
    categorical value in `value_column`, return a new DataFrame summing the
    overlapping days of items in each month broken down by each unique value in
    `value_column`. To restrict (and order) the value columns, pass a list of
    valid values as `output_columns`.
    """

    def build_df(t):
        start_date = getattr(t, start_column)
        end_date = getattr(t, end_column)
        value = getattr(t, value_column)

        if end_date is pd.NaT:
            end_date = pd.Timestamp.today()

        days_range = pd.date_range(start_date, end_date, freq='D')
        first_month = start_date.normalize().to_period('M').to_timestamp('D', 'S')
        last_month = end_date.normalize().to_period('M').to_timestamp('D', 'S')

        index = pd.date_range(first_month, last_month, freq='MS')

        return pd.DataFrame(
            index=index,
            data=[[len(pd.date_range(month_start, month_start + pd.tseries.offsets.MonthEnd(1), freq='D').intersection(days_range))] for month_start in index],
            columns=[value]
        )

    breakdown = pd.concat([build_df(t) for t in df.itertuples()], sort=True).resample('MS').agg(aggfunc)

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


class Timespans:
    """Track time span spent in a state.

    Timespans class tracks (enter, exit) timestamps
    for an item. One item can be re-entered multiple times.
    Timespan can be open-ended.

    Because some transitions may be backwards e.g.
    in the case we have state transitions:

    - In development
    - Code review
    - QA
    - QA fixes needed
    - QA (again)
    - QA fixes needed (again)
    - QA (third time)

    Remarks:

    - Spans can have zero duration, but not negative duration
    """

    def __init__(self):
        # List of timespans for an issue state
        # Each item is [datetime, datetime]
        # If the closing datetime is missing the item was never closed
        self.spans = []  #: List[List[datetime)]

    def reset(self):
        """Used by state backwards transition tracking logic."""
        self.spans = []

    def __str__(self):
        """Produce a nice readable format of spans.

        Like 2020-03-27 08:52 - 2020-03-28 20:50, 2020-04-01 13:37 - 2020-04-01 17:02, 2020-04-07 04:28 - 2020-04-10 03:26
        """

        if not self.spans:
            return "[no duration]"

        out = ""
        # https://stackoverflow.com/a/49486415/315168
        elems = list(self.spans)
        while elems:
            s = elems.pop(0)
            out += s[0].strftime("%Y-%m-%d %H:%M")
            out += " - "
            if len(s) == 2:
                # Span has end
                out += s[1].strftime("%Y-%m-%d %H:%M")
            if elems:
                # Not last elements
                out += ", "
        return out

    def enter(self, when: datetime.datetime):
        assert isinstance(when, datetime.datetime)
        # Check we have been closed
        if self.spans:
            last_span = self.spans[-1]
            assert len(last_span) == 2, "The last timespan was not closed"
        self.spans.append([when])

    def leave(self, when: datetime.datetime):
        assert isinstance(when, datetime.datetime)
        assert self.spans, "Cannot exit without starting a span"
        last_span = self.spans[-1]
        assert len(last_span) == 1, "The latest span was already closed"
        assert when >= last_span[0], "Span cannot end sooner it has started"
        last_span.append(when)

    @property
    def filled(self):
        """Does this timespan have any data"""
        return True if self.spans else False

    @property
    def open_ended(self):
        """Have we the last timespan closed or still going on?"""
        if not self.spans:
            return True
        return len(self.spans[-1]) == 1

    @property
    def start(self):
        """When timespans started - first date."""
        assert self.spans
        return self.spans[0][0]

    @property
    def end(self):
        """When timespans ended - last done date."""
        assert self.spans, "No spans"
        last_span = self.spans[-1]
        assert len(last_span) == 2, "Open-ended span"
        return last_span[1]

    @property
    def duration(self) -> datetime.timedelta:
        """Duration of all timespans altogether."""
        return sum([s[1] - s[0] for s in self.spans], datetime.timedelta())







