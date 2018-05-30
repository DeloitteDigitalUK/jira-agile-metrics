# JIRA Agile Metrics

A tool to extract Agile metrics and charts from JIRA projects.

## Installation

Requires Python 3.6 or later.

Install Python 3 and the `pip` package manager. Then run:

    $ pip install jira-agile-metrics

You can do this globally, but you may want to use a virtual Python environment
(`venv`) instead to keep things self-contained.

See [The Hitchhiker's Guide to Python](http://python-guide.org/en/latest/) for
the full details about how to install Python and venvs.

This should install a binary called `jira-agile-metrics` in the relevant `bin`
directory. You can test it using:

    $ jira-agile-metrics --help

... which should print a help message with a whole slew of options. More on
those below.

### Using Docker

If you prefer, you can use [Docker](http://docker.com) to install and run
`jira-agile-metrics` with all the relevant dependencies in place. After
installing Docker, run:

    $ docker run -it --rm -v $PWD:/data optilude/jira-agile-metrics config.yml

This will run `jira-agile-metrics` with the configuration file `config.yml` from
the current directory, writing outputs also to the current directory. The
argument `-v $PWD:/data` mounts the `/data` volume, where output files will be
written, to the current working directory. You can of course specify a
different bind mount.

## Usage

The basic usage pattern is to run `jira-agile-metrics` with a configuration
file, written in YAML format (see below), which describes:

  - how to connect to a remote JIRA instance;
  - what metrics (spreadsheet-like data files, charts as images) to output;
  - various settings used to calculate those metrics; and
  - a description of the stages of the workflow the relevant JIRA tickets go
    through.

The tool will then connect to JIRA using its web services API, run a query to
the relevant tickets and their history, and calculate the requierd metrics.

The outputs are written to local filesystem files. Data files can be written in
CSV, XLSX or JSON formats (depending on the extension of the desired output
file), whilst charts are written as PNG images.

Most of the options in the configuration file can be overridden using command
line arguments. For a full list, run:

    $ jira-agile-metrics --help

### Server mode

`jira-agile-metrics` comes with a simple web server that can be used to produce
metrics by uploading a configuration file and downloading a ZIP file with data
and charts. To start it, run:

    $ jira-agile-metrics --server 5000

This will start a server on port `5000` (you can also specify a bind host name
or IP address, e.g. `0.0.0.0:5000`). Visit this address in a web browser and
upload a file.

In this mode, all other command line options are ignored.

**Note:** The web server is designed for low-volume usage only, and does not
have a sophisticated security model. It is simply a more accessible front end
to the features of the command line tool. The server will wait, synchronously,
whilst JIRA is queried and charts are produced, which can take a long time.
During this time, the browser will wait, and threads will block.

**Warning:** The web server does not encrypt requests, which means that by
default JIRA credentials are transmitted in plain-text. You are strongly adviced
to configure a reverse proxy (e.g. `nginx`) with SSL enabled in front of it.

#### Using Docker to run the web server

There is a separate Docker image for running the web server, which uses `nginx`
and `uwsgi` for improved performance and stability (but still not SSL, which
would need to be configured with a domain-specific certificate):

    $ docker run -d --rm -p 8080:80 --name jira_metrics optilude/jira-agile-metrics:server

This will run the server in daemon mode and bind it to port `8080` on the local
host. To stop it, run:

    $ docker stop jira_metrics

See the [Docker documentation](https://docs.docker.com) for more details.

### An important note about passwords

The tool uses a simple username/password combination to connect to JIRA. You
need to ensure this user exists in the remote JIRA instance, and has the
required permissions.

There are three ways to provide the credentials for JIRA -- in particular, the
password, which should be kept scret. You should think carefully about which
approach makes most sense for you.

  - The safest option is to not set it in either the configuration file, or as
    a command line option. In this case, you will be prompted to input a
    password (and username, if you didn't set this either) each time the tool
    is run.
  - You can use the `--username` and/or `--password` command line options to set
    credentails when you invoke the `jira-agile-metrics` command. This keeps
    them out of the configuration file, but if you do this in an interactive
    shell that records command history (i.e. virtually all of them), your
    password will likely be stored in plain text in the command history!
  - If you are confident you can keep the configuration file secret, you can
    store them there, under the `Connection` section (see below).

### What issues should you include?

The most common use case is to calculate metrics for a team using a JIRA issue
type called something like `Story`, going through a workflow with stages like
`Backlog`, `Committed`, `Elaboration`, `Build`, `Code review`, `Test`, and `Done`,
and allowing a set of resolutions like `Completed`, `Withdrawn`, and `Duplicate`.

`jira-agile-metrics` lets you use JIRA JQL syntax to specify which issues you
are interested in. See the JIRA documentation for more details (or construct a
search using the JIRA UI and then have JIRA show you the corresponding JQL).

### Creating a configuration file

Here is an example configuration file for a basic example using the workflow
above:

    # How to connect to JIRA. Can also include `Username` and `Password`
    Connection:
        Domain: https://myjira.atlassian.net # your JIRA instance

    # What issues to search for. Uses JQL syntax.
    Query: Project=ABC AND IssueType=Story AND (Resolution IS NULL OR Resolution IN (Completed, Withdrawn))

    # The workflow we want to analyse. By convention, the first stage should be
    # the backlog / initial state, and the final stage should indicate the work
    # is done.
    #
    # We map analytics names to JIRA status names. It's possible to collapse
    # multiple JIRA statuses into a single workflow stage, as with `QA` below.
    Workflow: 
        Backlog: Backlog
        Committed: Committed
        Elaboration: Elaboration
        Build: Build
        QA:
            - Code review
            - Test
        Done: Done
    
    # What outputs to produce. These are all optional. If an option isn't set
    # the relevant metric will not be produced.

    Output:

        # CSV files with raw data for input to other tools or further analysis in a spreadsheet
        # If you use .json or .xslx as the extension, you can get JSON data files or Excel
        # spreadsheets instead

        Cycle time data: cycletime.csv
        CFD data: cfd.csv
        Scatterplot data: scatterplot.csv
        Histogram data: histogram.csv
        Throughput data: throughput.csv
        Percentiles data: percentiles.csv

        # Various charts

        Scatterplot chart: scatterplot.png
        Scatterplot chart title: Cycle time scatter plot
        
        Histogram chart: histogram.png
        Histogram chart title: Cycle time histogram
        
        CFD chart: cfd.png
        CFD chart title: Cumulative Flow Diagram
        
        Throughput chart: throughput.png
        Throughput chart title: Throughput trend
        
        Burnup chart: burnup.png
        Burnup chart title: Burn-up

        Burnup forecast chart: burnup-forecast.png
        Burnup forecast chart title: Burn-up forecast
        Burnup forecast chart trials: 100 # number of Monte Carlo trials to run to estimate completion date

        # Burnup forecast chart throughput window: 60 # Days in the past to use for calculating historical throughput
        # Burnup forecast chart throughput window end: 2018-06-01 # Calculate throughput window to this date (defaults to today)
        # Burnup forecast chart target: 100 # items to complete in total; by default uses the current size of the backlog
        # Burnup forecast chart deadline: 2018-06-01 # deadline date, in ISO format; if not set, no deadline is drawn.
        # Burnup forecast chart deadline confidence: .85 # percentile to use to compare forecast to deadline
        
        WIP chart: wip.png
        WIP chart title: Work in Progress

        Ageing WIP chart: ageing-wip.png
        Ageing WIP chart title: Ageing WIP

        Net flow chart: net-flow.png
        Net flow chart title: Net flow

Hint: If you prefer to manage your queries as saved filters in JIRA, you can
use the special JQL syntax of `filter=123`, where `123` is the filter ID.

If you save this file as e.g. `config.yaml`, you can run:

    $ jira-agile-metrics config.yaml

This should prompt you for a username and password, and then connect to your
JIRA instance, fetch the issues matching the query, calculate metrics, and
write a number of CSV and PNG files to the current working directory (you can
use the `--output-directory` option to write to another directory).

When testing configuration, it is often helpful to fetch just a small number of
issues to speed things up. You can either do this by making your query more
restrictive, or by using the `-n` flag to limit the number of issues fetched:

    $ jira-agile-metrics -n 20 config.yaml

If you want more information about what's going on, use the `-v` flag:

    $ jira-agile-metrics -v config.yaml
 

## Available metrics

`jira-agile-metrics` can produce a number of data files and charts, which can
be enabled in the `Output` section of the configuration file, or with a
corresponding command line option.

**Note:** In the configuration file, you can specify output file *names*, but
not absolute or relative paths. Files will always be written to the current
working directory. This is to prevent unexpeced behaviour and the potential of
overwriting other files when configuration files are moved around or used on
a remote machine. No such restriction applies to output files specified in
command line arguments.

### Cycle time details

Details about each ticket and the date it entered each stage of the workflow.
Both the CSV and JSON versions of this file can be used by the
[Actionable Agile Analytics](http://actionableagile.com/) tool, which offers
powerful, interactive analysis of Agile flow.

In the configuration file:

    Output:
        Cycle time data: cycletime.csv

You can also use `.json` or `.xlsx` formats.

### Cumulative Flow Diagram (CFD)

Raw data for creating a valid Cumulative Flow Diagram, in spreadsheet format,
and/or an image file of the same. The CFD shows the number of work items in
each stage of the flow as a stacked area chart, day by day. This allows us to
visualise WIP, cycle time, and throughput.

In the configuration file:

    Output:
        CFD data: cfd.csv
        CFD chart: cfd.png
        CFD chart title: Cumulative Flow Diagram

You can also use `.json` or `.xlsx` formats for the data file.

### Cycle time scatter plot

Raw data for creating a valid Cycle Time scatter plot graph, and/or an image
file of the same. This chart plots the end-to-end cycle time (excluding time
spent in the backlog) for each work item against its completion date, and
overlays quantiles (e.g. 85% of tickets took 18 days or fewer)

In the configuration file:

    Output:
        Scatterplot data: scatterplot.csv
        Scatterplot chart: scatterplot.png
        Scatterplot chart title: Cycle time scatter plot

You can also use `.json` or `.xlsx` formats for the data file.

By default, the quantiles used are the 50th, 85th and 95th percentile, but you
can specify a different list with the `Quantiles` option under `Output`:

        Quantiles:
            - 0.3
            - 0.5
            - 0.75
            - 0.85
            - 0.95

Note that this option affects all charts that use quantiles.

To get the quantile values (number of day at each quantile) in a data file, use:

        Percentiles data: percentiles.csv

### Cycle time histogram

This is a different view of the cycle time , calculatd and/or plotted as a
histogram.

In the configuration file:

    Output:
        Histogram data: histogram.csv
        Histogram chart: histogram.png
        Histogram chart title: Cycle time histogram

You can also use `.json` or `.xlsx` formats for the data file.

This also respects the `Quantiles` option (see above).

### Throughput data

Weekly throughput, i.e. the number of items completed week by week. The chart
also shows a trend line.

In the configuration file:

    Output:
        Throughput data: throughput.csv
        Throughput chart: throughput.png
        Throughput chart title: Throughput trend

You can also use `.json` or `.xlsx` formats for the data file.

To change the frequency from weekly to something else, use:

        Throughput frequency: 1D

Here, `1D` means daily. The default is `1W-MON`, which means weekly starting on
Mondays.

### WIP box plot

Shows a box plot of WIP, week by week (or some other frequency).

In the configuration file:

        WIP chart: wip.png
        WIP chart title: Work in Progress

To change the frequency from weekly to something else, use:

        WIP chart frequency: 1D

Here, `1D` means daily. The default is `1W-MON`, which means weekly starting on
Mondays.

### Net flow chart

Shows the difference between arrivals and departures week on week. In a
perfectly stable system, the net flow would be 0.

In the configuration file:

        Net flow chart: net-flow.png
        Net flow chart title: Net flow

To change the frequency from weekly to something else, use:

        Net flow chart frequency: 1D

Here, `1D` means daily. The default is `1W-MON`, which means weekly starting on
Mondays.

### Ageing WIP chart

Shows the cycle time to date for each work item, grouped into the stages of
the workflow. This can help identify slow-moving tickets.

In the configuration file:

        Ageing WIP chart: ageing-wip.png
        Ageing WIP chart title: Ageing WIP

### Burn-up chart

A basic Agile burn-up chart, based on a count of items completed and in the
backlog.

In the configuration file:

        Burnup chart: burnup.png
        Burnup chart title: Burn-up

### Burn-up chart with forecast line

A more advanced version of the burn-up chart, which will run a Monte Carlo
simulation based on historical throughput to forecast a completion date for
the scope.

The simulation can be calibrated with a series of options to set:

    - The number of trials to run. Each trial will be drawn as a hypotehtical
      burn-up to completion.
    - The window of time from which to sample historical throughput. This should
      be representative of the near future, and ideally about 6-12 weeks long.
    - The target to aim for, as a number of stories to have completed. Defaults
      to the size of the backlog, but can be set to an assumed figure.
    - A deadline date, which, if set, can be compared to a forecast at a given
      confidence interval.

In the configuration file:

        Burnup forecast chart: burnup-forecast.png
        Burnup forecast chart title: Burn-up forecast
        Burnup forecast chart trials: 100 # number of Monte Carlo trials to run to estimate completion date

        Burnup forecast chart throughput window: 60 # Days in the past to use for calculating historical throughput
        Burnup forecast chart throughput window end: 2018-06-01 # Calculate throughput window to this date (defaults to last day of burnup)
        Burnup forecast chart target: 100 # items to complete in total; by default uses the current size of the backlog
        Burnup forecast chart deadline: 2018-06-01 # deadline date, in ISO format; if not set, no deadline is drawn.
        Burnup forecast chart deadline confidence: .85 # percentile to use to compare forecast to deadline

## More details about the configuration file format

The configuration file is written in YAML format. If you are unfamiliar with
YAML, know that:

* Comments start with `#`
* Sections are defined with a name followed by a colon, and then an indented
  block underneath. `Connection`, `Output`, `Workflow` and `Attributes` area
  all sections in the example above.
* Indentation has to use spaces, not tabs!
* Single values can be set using `Key: value` pairs. For example,
  `Burnup chart: burnup.png` above sets the key `Burnup chart` to the value
  `burnup.png`.
* Lists of values can be set by indenting a new block and placing a `-` in front
  of each list value. In the example above, the `QA` list contains
  the values `Code review` and `Test`.

The sections for `Workflow` is required. Additionally, you must either specfiy a
single `Query`, or a block of `Queries` (see below). Connection details must
be set either in the `Connection` file or as command line arguments.

Under `Workflow`, at least two steps are required. Specify the steps in order.
You may either specify a single workflow value or a list (as shown for `QA`
above), in which case multiple JIRA statuses will be collapsed into a single
state for analytics purposes.

The file, and values for things like workflow statuses and attributes, are case
insensitive.

### Extracting additional attributes

You may want to add additional fields to the cycle time output data. Use an
`Attributes` block to do this:

    Attributes:
        Priority: Priority
        Release: Fix version/s
        Team: Team name

Here, three additional columns will be added: `Priority`, `Release` and `Team`,
corresponding to the JIRA fields `Priority`, `Fix version/s` and `Team name`,
respectively.

When specifying attributes, use the *name* of the field (as rendered on screen
in JIRA), not its id (as you might do in JQL), so e.g. use `Component/s` not
`components`.

The attributes `Type` (issue type), `Status` and `Resolution` are always
included.

### Multi-valued fields

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

### Combining multiple queries

If it is difficult to construct a single set of criteria that returns all
required issues, multiple queries can be added into a `Queries` block, like so:

    Queries:
        Attribute: Team
        Criteria:
            - Value: Team 1
              JQL: (filter=123)

            - Value: Team 2
              JQL: (filter=124)

In this example, two queries will be run, based on the two filters `123` and
`124` (you can use any valid JQL).

In the cycle time output, a new column called `Team` will be added, as specified
by the `Attribute` field under `Queries`. For all items returned by
the first query, the value will be `Team 1` as per the `Value` field, and for
all items returned by the second query, it will be `Team 2`.

## Troubleshooting

* If Excel complains about a `SYLK` format error, ignore it. Click OK. See
  https://support.microsoft.com/en-us/kb/215591.
* JIRA error messages may be printed out as HTML in the console. The error is
  in there somewhere, but may be difficult to see. Most likely, this is either
  an authentication failure (incorrect username/password or blocked account),
  or an error in the `Query` option resulting in invalid JQL.
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
* To install the charting dependencies on a Mac, you might need to install a
  `gfortran` compiler for `scipy`. Use [Homebrew](http://brew.sh) and install the
  `gcc` brew.

## Changelog

### 0.2

* Added `--output-directory` option.

### 0.1

* Forked from `jira-agile-metrics`
