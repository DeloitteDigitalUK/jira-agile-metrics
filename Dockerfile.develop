FROM python:3

#
# Docker image for building the app and running tests. Can be used in lieu of
# a virtualenv with all dependencies install to make development easier.
#
# To build this image, run:
#
#  $ docker build -t jira-agile-metrics-dev -f Dockerfile.develop .
#
# To run tests, map the source code directory to /app and run pytest:
#
#  $ docker run -it --rm -v $PWD:/app jira-agile-metrics-dev pytest /app
# 
# To run the app itself, map the source code directory /app and an output
# file directory /data:
#
#  $ docker run -it --rm -v $PWD:/app -v $PWD/output:/data jira-agile-metrics-dev jira-agile-metrics --help
#
# To run the test server, use port 5000 and map it locally:
#
# $ docker run -it --rm -p 5000:5000 -v $PWD:/app --env FLASK_DEBUG=1 jira-agile-metrics-dev jira-agile-metrics --server 0.0.0.0:5000
#
# It is not necessary to rebuild the image each time the source code changes,
# but if you change the `requirements.txt` file of install dependencies, you
# do need to re-run `docker build` as per above.
#
# NOTE: If you bind-mount the source code to `/app` and switch between using
# the Docker image and local builds, you may confuse the Python bytecode caching
# mechanism. This can result in problems including `ImportMismatchErrors`.
# 
# To clear the cache, run:
#
#  $ find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print
#
# This will remove `__pycache__` and `.pyc` files.
#

# Install requirments first to make future rebuilds faster
RUN pip install pytest
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY . /app
RUN pip install -e /app

# And allow the host to mount the latest source code on top of it
VOLUME /app

# Outputs will be written to the /data volume 
WORKDIR /data
VOLUME /data

# Expose port 5000 for the development server
EXPOSE 5000

# Run with a headless matplotlib backend
ENV MPLBACKEND="agg"
