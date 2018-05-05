FROM python:3-onbuild

WORKDIR /data
VOLUME /data

ENTRYPOINT [ "jira-agile-metrics" ]