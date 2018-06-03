# To-do

## New reports

### Defect concentration

- Query for tickets (JQL)
- Priority (field name)
- Type (field name)
- Environment (field name)
- Store: created date, closed date, priority, type, environment
- Stacked bar chart: For each month, number of tickets open, grouped by environment found
- Stacked bar chart: For each month, number of tickets open, grouped by type
- Stacked bar chart: For each month, number of tickets open, grouped by priority

Sketch of the grouping algorithm:

```python

bugs = pd.DataFrame([
    {'key': 'ABC-1', 'priority': 'high', 'start': pd.Timestamp(2018, 1, 1), 'end': pd.Timestamp(2018,3,20)},
    {'key': 'ABC-2', 'priority': 'med',  'start': pd.Timestamp(2018, 1, 2), 'end': pd.Timestamp(2018,1,20)},
    {'key': 'ABC-3', 'priority': 'high', 'start': pd.Timestamp(2018, 2, 3), 'end': pd.Timestamp(2018,3,20)},
    {'key': 'ABC-4', 'priority': 'med',  'start': pd.Timestamp(2018, 1, 4), 'end': pd.Timestamp(2018,3,20)},
    {'key': 'ABC-5', 'priority': 'high', 'start': pd.Timestamp(2018, 2, 5), 'end': pd.Timestamp(2018,2,20)},
    {'key': 'ABC-6', 'priority': 'med',  'start': pd.Timestamp(2018, 3, 6), 'end': pd.Timestamp(2018,3,20)}
], columns=['key', 'priority', 'start', 'end'])

def strip_day(timestamp):
    return pd.Timestamp(timestamp.year, timestamp.month, 1)

statuses = ['low', 'med', 'high']

monthly_bugs = pd.concat([
    pd.DataFrame(index=pd.date_range(strip_day(b.start), strip_day(b.end), freq='MS'), data=[[b.key]], columns=[b.priority])
    for b in bugs.itertuples()
]).resample('MS').count()


monthly_bugs  = monthly_bugs[[s for s in statuses if s in monthly_bugs.columns]]

fig, ax = plt.subplots()
monthly_bugs.plot(ax=ax, kind='bar', stacked=True)
ax.set_xticklabels([d.strftime('%B %Y') for d in monthly_bugs.index])
```

### Technical debt

- Query for tickets (JQL)
- Impact/priority (field name)
- Store: created date, closed date (if any), age (from created to today/closed)
- Stacked bar chart: For each of the last X months, number of open items, grouped by priority
- Stacked bar chart: For each impact level, number of open items, grouped by age bracket

### Waste

- Query for tickets (JQL)
- Store: last non-resolved state, most recent state
- Stacked bar chart: For each of the last X months, how many stories withdrawn, grouped by status

### Blocked time

Note: this is harder to do, and maybe we will never get the data close to right

- Find tickets in cycle time data
- Record entry and exit to the "flagged" status, plus reason (free text?), as "blocking event"
- Store: Ticket, blocking event, reason, start date, end date (if resolved)
- Stacked bar chart: For each month, how many days total on blocking events, grouped by status
