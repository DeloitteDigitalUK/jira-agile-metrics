FROM python:3

LABEL version="0.6"
LABEL description="Produce charts and data files of Agile metrics extracted \
from JIRA."

# Install requirments first to make future rebuilds faster
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Outputs will be written to the /data volume 
WORKDIR /data
VOLUME /data

# Install app and binary
COPY . /app
RUN pip install --no-cache-dir /app

# Run with a headless matplotlib backend
ENV MPLBACKEND="agg"

ENTRYPOINT ["jira-agile-metrics"]
