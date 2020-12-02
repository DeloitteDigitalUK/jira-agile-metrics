import pytest
import datetime
from pandas import DataFrame

from ..conftest import (
    FauxJIRA as JIRA,
    FauxIssue as Issue,
    FauxChange as Change,
    FauxFieldValue as Value,
)

from ..querymanager import QueryManager
from .cycletime import CycleTimeCalculator
from .ageingwip import AgeingWIPChartCalculator

from ..utils import extend_dict


@pytest.fixture
def settings(minimal_settings):
    return extend_dict(
        minimal_settings,
        {
            "ageing_wip_chart": "ageingwip.png"
            # without a file to write the calculator will stop
        },
    )


@pytest.fixture
def jira_with_skipped_columns(minimal_fields):
    return JIRA(
        fields=minimal_fields,
        issues=[
            Issue(
                "A-13",
                summary="No Gaps",
                issuetype=Value("Story", "story"),
                status=Value("Build", "build"),
                resolution=None,
                resolutiondate=None,
                created="2018-01-01 08:15:00",
                changes=[
                    Change(
                        "2018-01-02 08:15:00",
                        [
                            (
                                "status",
                                "Backlog",
                                "Next",
                            )
                        ],
                    ),
                    Change(
                        "2018-01-03 08:15:00",
                        [
                            (
                                "status",
                                "Next",
                                "Build",
                            )
                        ],
                    ),
                ],
            ),
            Issue(
                "A-14",
                summary="Gaps",
                issuetype=Value("Story", "story"),
                status=Value("Build", "build"),
                resolution=None,
                resolutiondate=None,
                created="2018-01-01 08:15:00",
                changes=[
                    Change(
                        "2018-01-02 08:15:00",
                        [
                            (
                                "status",
                                "Backlog",
                                "Build",
                            )
                        ],
                    ),  # skipping column Committed
                ],
            ),
            Issue(
                "A-15",
                summary="Gaps and withdrawn",
                issuetype=Value("Story", "story"),
                status=Value("Done", "done"),
                resolution=Value("Withdrawn", "withdrawn"),
                resolutiondate="2018-01-02 08:15:00",
                created="2018-01-01 08:15:00",
                changes=[
                    Change(
                        "2018-01-02 08:15:00",
                        [
                            (
                                "status",
                                "Backlog",
                                "Done",
                            ),
                            ("resolution", None, "Withdrawn"),
                        ],
                    ),  # skipping columns Committed, Build and Test
                ],
            ),
            Issue(
                "A-16",
                summary="Gap in first committed step",
                issuetype=Value("Story", "story"),
                status=Value("Build", "Build"),
                resolution=None,
                resolutiondate=None,
                created="2018-01-01 08:15:00",
                changes=[
                    Change(
                        "2018-01-03 08:15:00",
                        [
                            (
                                "status",
                                "Backlog",
                                "Build",
                            )
                        ],
                    ),  # skipping column Committed
                ],
            ),
        ],
    )


@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager


@pytest.fixture
def results(large_cycle_time_results):
    return extend_dict(large_cycle_time_results, {})


@pytest.fixture
def today():
    return datetime.date(2018, 1, 10)


@pytest.fixture
def now(today):
    return datetime.datetime.combine(today, datetime.time(8, 30, 00))


def test_empty(query_manager, settings, minimal_cycle_time_columns, today):
    results = {
        CycleTimeCalculator: DataFrame(
            [], columns=minimal_cycle_time_columns, index=[]
        )
    }

    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)
    assert list(data.columns) == [
        "key",
        "summary",
        "status",
        "age",
        "Committed",
        "Build",
        "Test",
    ]
    assert len(data.index) == 0


def test_columns(query_manager, settings, results, today):
    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)

    assert list(data.columns) == [
        "key",
        "summary",
        "status",
        "age",
        "Committed",
        "Build",
        "Test",
    ]


def test_calculate_ageing_wip(query_manager, settings, results, today):
    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)

    assert data[["key", "status", "age"]].to_dict("records") == [
        {"key": "A-4", "status": "Committed", "age": 8.0},
        {"key": "A-5", "status": "Committed", "age": 7.0},
        {"key": "A-6", "status": "Committed", "age": 7.0},
        {"key": "A-7", "status": "Build", "age": 8.0},
        {"key": "A-8", "status": "Build", "age": 8.0},
        {"key": "A-9", "status": "Build", "age": 8.0},
        {"key": "A-10", "status": "Test", "age": 8.0},
        {"key": "A-11", "status": "Test", "age": 8.0},
        {"key": "A-12", "status": "Test", "age": 8.0},
    ]


def test_calculate_ageing_wip_with_different_done_column(
    query_manager, settings, results, today
):
    settings.update(
        {
            "done_column": "Test",
        }
    )

    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)

    assert data[["key", "status", "age"]].to_dict("records") == [
        {"key": "A-4", "status": "Committed", "age": 8.0},
        {"key": "A-5", "status": "Committed", "age": 7.0},
        {"key": "A-6", "status": "Committed", "age": 7.0},
        {"key": "A-7", "status": "Build", "age": 8.0},
        {"key": "A-8", "status": "Build", "age": 8.0},
        {"key": "A-9", "status": "Build", "age": 8.0},
    ]


def test_calculate_ageing_wip_with_skipped_columns(
    jira_with_skipped_columns, settings, today, now
):
    query_manager = QueryManager(jira_with_skipped_columns, settings)
    results = {}
    cycle_time_calc = CycleTimeCalculator(query_manager, settings, results)
    results[CycleTimeCalculator] = cycle_time_calc.run(now=now)
    ageing_wip_calc = AgeingWIPChartCalculator(
        query_manager, settings, results
    )
    data = ageing_wip_calc.run(today=today)

    assert data[["key", "status", "age"]].to_dict("records") == [
        {"key": "A-13", "status": "Build", "age": 8.0},
        {"key": "A-14", "status": "Build", "age": 8.0},
        {"key": "A-16", "status": "Build", "age": 7.0},
    ]
