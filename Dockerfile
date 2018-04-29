FROM python:3-onbuild
MAINTAINER Martin Aspeli <optilude@gmail.com>

WORKDIR /data
VOLUME /data

ENTRYPOINT [ "jira-agile-metrics" ]