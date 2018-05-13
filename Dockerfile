FROM python:3

LABEL version="0.1"
LABEL description="Produce charts and data files of Agile metrics extracted \
from JIRA."

WORKDIR /data
VOLUME /data

COPY . /usr/src/jira-agile-metrics
RUN pip install --no-cache-dir /usr/src/jira-agile-metrics

ENV MPLBACKEND="agg"
ENTRYPOINT ["jira-agile-metrics"]
