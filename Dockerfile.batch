FROM python:3

LABEL version="0.6"
LABEL description="Produce charts and data files of Agile metrics extracted \
from JIRA in a batch."

# Install requirments first to make future rebuilds faster
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Config will be read from /config
VOLUME /config

# Outputs will be written to the /data volume 
WORKDIR /data
VOLUME /data

# Install app and binary
COPY . /app
RUN pip install --no-cache-dir /app

# Run with a headless matplotlib backend
ENV MPLBACKEND="agg"

# Add entry point, which runs `jira-agile-metrics` for each config file
ADD docker-scripts/batch-entrypoint.sh /batch-entrypoint.sh
RUN chmod +x /batch-entrypoint.sh

ENTRYPOINT ["/batch-entrypoint.sh"]
