import datetime
import os.path

import numpy as np
import pandas as pd
import seaborn as sns


class StatusTypes:
    backlog = "backlog"
    accepted = "accepted"
    complete = "complete"


def extend_dict(source_dict, dict_to_add):
    extended_dict = source_dict.copy()
    extended_dict.update(dict_to_add)
    return extended_dict


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


def to_days_since_epoch(date):
    return (date - datetime.date(1970, 1, 1)).days


def set_chart_context(context):
    sns.set_context(context)


def set_chart_style(style="whitegrid", despine=True):
    sns.set_style(style)
    if despine:
        sns.despine()


def breakdown_by_month(df, start_column, end_column, key_column, value_column, output_columns=None, aggfunc="count"):
    """If `df` is a DataFrame of items that are valid/active between the
    timestamps stored in `start_column` and `end_column`, and where each item
    is uniquely identified by `key_column` and has a categorical value in
    `value_column`, return a new DataFrame counting the number of items in
    each month broken down by each unique value in `value_column`. To restrict
    (and order) the value columns, pass a list of valid values as `output_columns`.
    """

    def build_df(row):
        start_date = getattr(row, start_column)
        end_date = getattr(row, end_column)
        key = getattr(row, key_column)
        value = getattr(row, value_column)

        if end_date is pd.NaT:
            end_date = pd.Timestamp.today()

        first_month = start_date.normalize().to_period("M").to_timestamp("D", "S")
        last_month = end_date.normalize().to_period("M").to_timestamp("D", "S")

        index = pd.date_range(first_month, last_month, freq="MS")

        return pd.DataFrame(index=index, data=[[key]], columns=[value])

    breakdown = pd.concat([build_df(row) for row in df.itertuples()], sort=True).resample("MS").agg(aggfunc)

    if output_columns:
        breakdown = breakdown[[s for s in output_columns if s in breakdown.columns]]

    return breakdown


def breakdown_by_month_sum_days(df, start_column, end_column, value_column, output_columns=None, aggfunc="sum"):
    """If `df` is a DataFrame of items that are valid/active between the
    timestamps stored in `start_column` and `end_column`, and where each has a
    categorical value in `value_column`, return a new DataFrame summing the
    overlapping days of items in each month broken down by each unique value in
    `value_column`. To restrict (and order) the value columns, pass a list of
    valid values as `output_columns`.
    """

    def build_df(row):
        start_date = getattr(row, start_column)
        end_date = getattr(row, end_column)
        value = getattr(row, value_column)

        if end_date is pd.NaT:
            end_date = pd.Timestamp.today()

        days_range = pd.date_range(start_date, end_date, freq="D")
        first_month = start_date.normalize().to_period("M").to_timestamp("D", "S")
        last_month = end_date.normalize().to_period("M").to_timestamp("D", "S")

        index = pd.date_range(first_month, last_month, freq="MS")

        return pd.DataFrame(
            index=index,
            data=[
                [
                    len(
                        pd.date_range(month_start, month_start + pd.tseries.offsets.MonthEnd(1), freq="D").intersection(
                            days_range
                        )
                    )
                ]
                for month_start in index
            ],
            columns=[value],
        )

    breakdown = pd.concat([build_df(row) for row in df.itertuples()], sort=True).resample("MS").agg(aggfunc)

    if output_columns:
        breakdown = breakdown[[s for s in output_columns if s in breakdown.columns]]

    return breakdown


def to_bin(value, edges):
    """Pass a list of numbers in `edges` and return which of them `value` falls
    between. If < the first item, return (0, <first>). If > last item, return
    (<last>, None).
    """

    previous = 0
    for edge in edges:
        if previous <= value <= edge:
            return (previous, edge)
        previous = edge
    return (previous, None)
