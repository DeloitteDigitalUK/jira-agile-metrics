# To-do

- Add time slicer (last X months) to various charts:
  - CFD (index, days)
  - Burnup (index, days)
  - Forecast (index, days)
  
  - Histogram (`completed_timestamp` > min date)
  - Scatterplot (`completed_date` > min date)
  
  - Net flow (index, periods)
  - Throughput (index, periods)
  - WIP (index, periods)

## Tests

## Docs

- Debt
- Waste
- Defects

## New reports

### Defect concentration

- Query for tickets (JQL)
- Priority (field name)
- Type (field name)
- Environment (field name)
- Window (months)
- Store: created date, closed date, priority, type, environment
- Stacked bar chart: For each month, number of tickets open, grouped by environment found
- Stacked bar chart: For each month, number of tickets open, grouped by type
- Stacked bar chart: For each month, number of tickets open, grouped by priority

### Waste

- Query for tickets (JQL)
- Window (months)
- Store: last non-resolved state, most recent state
- Stacked bar chart: For each of the last X months, how many stories withdrawn, grouped by status

### Blocked time

Note: this is harder to do, and maybe we will never get the data close to right

- Find tickets in cycle time data
- Window (months)
- Record entry and exit to the "flagged" status, plus reason (free text?), as "blocking event"
- Store: Ticket, blocking event, reason, start date, end date (if resolved)
- Stacked bar chart: For each month, how many days total on blocking events, grouped by status
