FROM tiangolo/uwsgi-nginx-flask:python3.6

LABEL version="0.6"
LABEL description="Web server version of jira-agile-metrics"

# Install requirments first to make future rebuilds faster
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Install app and binary
COPY . /app
RUN pip install --no-cache-dir /app

# Configure nginx to run flask; entry point is taken frmo uwsgi.ini
ENV STATIC_PATH=/app/jira_agile_metrics/webapp/static

# Run with a headless matplotlib backend
ENV MPLBACKEND="agg"
