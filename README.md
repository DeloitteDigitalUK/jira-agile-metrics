# JIRA Agile Metrics

TODO

## Installation

TODO


## Configuration

Write a YAML configuration file like so, calling it e.g. `config.yaml`::

    # How to connect to JIRA?
    Connection:
        Domain: https://myserver.atlassian.net
        Username: myusername # If missing, you will be prompted at runtime
        Password: secret     # If missing, you will be prompted at runtime
        Jira:                #List of key / value pairs that will be passed as options to jira as per https://jira.readthedocs.io/en/master/api.html#jira

    # What to search for?
    Criteria:
        Project: ABC # JIRA project key to search
        Issue types: # Which issue types to include
            - Story
            - Defect
        Valid resolutions: # Which resolution statuses to include (unresolved is always included)
            - Done
            - Closed
        JQL: labels != "Spike" # Additional filter as raw JQL, optional

    # Describe the workflow. Each step can be mapped to either a single JIRA
    # status, or a list of statuses that will be treated as equivalent
    Workflow:
        Open: Open
        Analysis IP: Analysis in Progress
        Analysis Done: Analysis Done
        Development IP: Development in Progress
        Development Done: Development Done
        Test IP: Test in Progress
        Test Done: Test Done
        Done:
            - Closed
            - Done

    # Map field names to additional attributes to extract
    Attributes:
        Components: Component/s
        Priority: Priority
        Release: Fix version/s

If you are unfamiliar with YAML, remember that:

* Comments start with `#`
* Sections are defined with a name followed by a colon, and then an indented
  block underneath. `Connection`, `Criteria`, `Workflow` and `Attributes` area
  all sections in the example above.
* Indentation has to use spaces, not tabs!
* Single values can be set using `Key: value` pairs. For example,
  `Project: ABC` above sets the key `Project` to the value `ABC`.
* Lists of values can be set by indenting a new block and placing a `-` in front
  of each list value. In the example above, the `Issue types` list contains
  the values `Story` and `Defect`.

The sections for `Connection`, `Criteria` and `Workflow` are required.

Under `Conection`, only `Domain` is required. If not specified, the script will
prompt for both or either of username and password when run.

Under `Criteria`, all fields are technically optional, but you should specify
at least some of them to avoid an unbounded query. `Issue types` and
`Valid resolutions` can be set to either single values or lists.

Under `Workflow`, at least two steps are required. Specify the steps in order.
You may either specify a single workflow value or a list (as shown for `Done`
above), in which case multiple JIRA statuses will be collapsed into a single
state for analytics purposes.

The file, and values for things like workflow statuses and attributes, are case
insensitive.

When specifying attributes, use the *name* of the field (as rendered on screen
in JIRA), not its id (as you might do in JQL), so e.g. use `Component/s` not
`components`.

The attributes `Type` (issue type), `Status` and `Resolution` are always
included.

When specifying fields like `Component/s` or `Fix version/s` that may have
lists of values, only the first value set will be used.

### Multiple queries

If it is difficult to construct a single set of criteria that returns all
required issues, multiple `Criteria` sections can be wrapped into a `Queries`
block, like so::

    Queries:
        Attribute: Team
        Criteria:
            - Value: Team 1
              Project: ABC
              Issue types:
                  - Story
                  - Bug
              Valid resolutions:
                  - Done
                  - Closed
              JQL: Component = "Team 1"

            - Value: Team 2
              Project: ABC
              Issue types:
                  - Story
                  - Bug
              Valid resolutions:
                  - Done
                  - Closed
              JQL: Component = "Team 2"

In this example, the `Component` field in JIRA is being used to signify the team
delivering the work, but may also be used for other things. Two JIRA queries
will be run, corresponding to the two `Criteria` blocks.

In addition, a new column called `Team` will be added to the output, as
specified by the `Attribute` field under `Queries`. For all items returned by
the first query, the value will be `Team 1` as per the `Value` field, and for
all items returned by the second query, it will be `Team 2`.

### Multi-valued fields

Some fields in JIRA can contain multiple values, e.g. `fixVersion`. By default,
the extractor will use the first value in such a field if one is specified in
the `Attributes` block. However, you may want to extract only specific values.

To do so, add a block like the following::

    Attributes:
        Release: Fix version/s

    Known values:
        Release:
            - "R01"
            - "R02"
            - "R03"

The extractor will pick the first "known value" found for the field. If none of
the known values match, the cell will be empty.

Running
-------

To produce the basic cycle time data, run `jira-agile-metrics` passing the name
of the YAML configuration file and the name of the output CSV file::

    $ jira-agile-metrics config.yaml data.csv

This will extract a CSV file called `data.csv` with cycle data based on the
configuration in `config.yaml`, in a format compatible with the
ActionableAgile toolset.

If you prefer Excel files for manual analysis::

    $ jira-agile-metrics --format=xlsx config.yaml data.xlsx

If you prefer JSON::

    $ jira-agile-metrics --format=json config.yaml data.json

The JSON format can be loaded by the Actionable Agile Analytics tool if you
self-host it and the single-page HTML file for the AAA tool and the JSON file
are accessible from the same web server, via a URL parameter::

    http://myserver/analytics.html?url=data.json

You can specify a path or full URL, but due to same-origin request restrictions,
your browser is unlikely to let you load anything not served from the same
domain as the analytics web app itself.

**Note:** When the `--format` is set, it applies to all files written, not
just the main cyle data file (see other options below). It is important to be
consistent with the file extensions. In particular, if you are using the `xlsx`
format you should also make sure all output files use a `.xlsx` extension.

There are lots more options. See::

    $ jira-agile-metrics --help

Use the `-v` option to print more information during the extract process.

Use the `-n` option to limit the number of items fetched from JIRA, based on
the most recently updated issues. This is useful for testing the configuration
without waiting for long downloads::

    $ jira-agile-metrics -v -n 10 config.yaml data.csv

To produce **Cumulative Flow Diagram statistics**, use the `--cfd` option::

    $ jira-agile-metrics --cfd cfd.csv config.yaml data.csv

This will yield a `cfd.csv` file with one row for each date, one column for each
step in the workflow, and a count of the number of issues in that workflow state
on that day. To plot a CFD, chart this data as a (non-stacked) area chart. You
should technically exclude the series in the first column if it represents the
backlog!

To produce **cycle time scatter plot statistics**, use the `--scatterplot` option::

    $ jira-agile-metrics --scatterplot scatterplot.csv config.yaml data.csv

This will yield a `scatterplot.csv` file with one row for each item that was
completed (i.e. it reached the last workflow state), with columns giving the
completion date and the number of days elapsed from the item entering the first
active state (i.e. the second step in the workflow, on the basis that the first
item represents a backlog or intake queue) to the item entering the completed
state. These two columns can be plotted as an X/Y scatter plot. Further columns
contain the dates of entry into each workflow state and the various issue
metadata to allow further filtering.

To be able to easily draw a **histogram** of the cycle time values, use the
`--histogram` option::

    $ jira-agile-metrics --histogram histogram.csv config.yaml data.csv

This will yield a `histogram.csv` file with two columns: bin ranges and the
number of items with cycle times falling within each bin. These can be charted
as a column or bar chart.

To find out the 30th, 50th, 70th, 85th and 95th **percentile cycle time** values,
pass the `--percentiles` option::

    $ jira-agile-metrics --percentiles percentiles.csv config.yaml data.csv

To calculate different percentiles use the `--quantiles` option::

    $ jira-agile-metrics --percentiles percentiles.csv --quantiles=0.3,0.5,0.8 config.yaml data.csv

Note that there should not be spaces between the commas!

To find out the **daily throughput** for the last 60 days, use the
`--throughput` option::

    $ jira-agile-metrics --throughput throughput.csv config.yaml data.csv

To use a different time window, e.g. the last 90 days::

    $ jira-agile-metrics --throughput throughput.csv --throughput-window=90 config.yaml data.csv

The various options can be used in combination, and it is technically OK to
skip the second positional (`data.csv`) parameter (in which case the file will
not be written).

There are various options available to allow you to draw **charts**, for example::

    $ jira-agile-metrics --charts-scatterplot=scatterplot.png config.yaml data.csv

The available charts are:

* `--charts-scatterplot` to draw a **scatterplot** of cycle times, with percentile lines
* `--charts-histogram` to draw a **histogram** of cycle times, with percentile lines
* `--charts-cfd` to draw a **Cumulative Flow Diagram**
* `--charts-throughput` to draw a daily **throughput bar chart**
* `--charts-burnup` to draw a simple **burn-up** chart (completed item count vs. time)
* `--charts-burnup-forecast` to draw a **burn-up chart with a Monte Carlo simulation**
  showing paths towards a completion target. The completion target will by default
  be the number of items in the backlog, but can be set explicitly with the
  `--charts-burnup-forecast-target` options. The simluation by default uses
  100 trials. The number of trials can be set with the
  `--charts-burnup-forecast-trials` option. You can set a deadline marker with the
  `--charts-burnup-forecast-deadline` option, which should be set to a date. If
  you also set `--charts-burnup-forecast-deadline-confidence` to a fraction (e.g.
  `0.85`) it will be used to find a confidence interval in the simulation to which
  the deadline will be compared.
* `--charts-wip` to draw a **WIP boxplot** showing min, max, median and mean WIP
  by week. By default, this will show the last 5 or 6 weeks' of data (depending
  on the weekday). You can change this with the `--charts-wip-window` parameter,
  set to a number of weeks.
* `--charts-ageing-wip` to draw an **ageing WIP chart**: a scatter plot of current
  cycle time against state in the cycle, i.e. how items are trending towards completion.
* `--charts-net-flow` to show a bar chart of the **weekly net flow**:
  departures - arrivals. By default, this will show the last 5 or 6 weeks' of
  data (depending on the weekday). You can change this with the
  `--charts-net-flow-window` parameter, set to a number of weeks.

Also note: all the `--charts-*` options have a corresponding `--charts-*-title`
option that can be used to set a title for the chart.

Finally, to limit the date range of the data shown in the charts, you can use the
options `--charts-from` and `--charts-to` to specify a starting and/or ending 
date (inclusive). Both are optional.

## Troubleshooting

* If Excel complains about a `SYLK` format error, ignore it. Click OK. See
  https://support.microsoft.com/en-us/kb/215591.
* JIRA error messages may be printed out as HTML in the console. The error is
  in there somewhere, but may be difficult to see. Most likely, this is either
  an authentication failure (incorrect username/password or blocked account),
  or an error in the `Criteria` section resulting in invalid JQL.
* If you aren't getting the issues you expected to see, use the `-v` option to
  see the JQL being sent to JIRA. Paste this into the JIRA issue filter search
  box ("Advanced mode") to see how JIRA evaluates it.
* Old workflow states can still be part of an issue's history after a workflow
  has been modified. Use the `-v` option to find out about workflow states that
  haven't been mapped.
* Excel sometimes picks funny formats for data in CSV files. Just set them to
  whatever makes sense.
* If you are on a Mac and you get an error about Python not being installed as
  a framework, try to create a file `~/.matplotlib/matplotlibrc` with the
  following contents::

    backend : Agg
* To install the charting dependencies on a Mac, you probably need to install a
  `gfortran` compiler for `scipy`. Use Homebrew (http://brew.sh) and install the
  `gcc` brew.

## Changelog

0.1 - 
    * Forked from `jira-agile-metrics`

