# To-do

- Add time slicer (last X months) to various charts.

## Tests

- Debt calculator (including if priority is None)

## Docs

- Debt
- Waste
- Defects

## New reports

### Waste

- Query for tickets (JQL)
- Store: last non-resolved state, most recent state
- Stacked bar chart: For each of the last X months, how many stories withdrawn, grouped by status

### Defect concentration

- Query for tickets (JQL)
- Priority (field name)
- Type (field name)
- Environment (field name)
- Store: created date, closed date, priority, type, environment
- Stacked bar chart: For each month, number of tickets open, grouped by environment found
- Stacked bar chart: For each month, number of tickets open, grouped by type
- Stacked bar chart: For each month, number of tickets open, grouped by priority

### Blocked time

Note: this is harder to do, and maybe we will never get the data close to right

- Find tickets in cycle time data
- Record entry and exit to the "flagged" status, plus reason (free text?), as "blocking event"
- Store: Ticket, blocking event, reason, start date, end date (if resolved)
- Stacked bar chart: For each month, how many days total on blocking events, grouped by status
