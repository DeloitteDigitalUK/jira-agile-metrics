import logging
import contextlib
import io
import os
import os.path
import shutil
import tempfile
import base64
import zipfile
import jinja2

from flask import Flask, render_template, request
from jira import JIRA

from ..config import config_to_options, CALCULATORS, ConfigError
from ..querymanager import QueryManager
from ..calculator import run_calculators

template_folder = os.path.join(os.path.dirname(__file__), "templates")
static_folder = os.path.join(os.path.dirname(__file__), "static")

app = Flask('jira-agile-metrics',
    template_folder=template_folder,
    static_folder=static_folder
)

app.jinja_loader = jinja2.PackageLoader('jira_agile_metrics.webapp', 'templates')

logger = logging.getLogger(__name__)

@app.route("/")
def index():
    return render_template('index.html', max_results=request.args.get('max_results', ""))

@app.route("/run", methods=['POST'])
def run():
    config = request.files['config']
    
    data = ""
    has_error = False
    log_buffer = io.StringIO()

    with capture_log(log_buffer, logging.DEBUG, "%(levelname)s: %(message)s"):
        
        # We swallow exceptions here because we want to show them in the output
        # log on the result page.
        try:
            options = config_to_options(config.read())
            override_options(options['connection'], request.form)
        
            # We allow a `max_results` query string parameter for faster debugging
            if request.form.get('max_results'):
                try:
                    options['settings']['max_results'] = int(request.form.get('max_results'))
                except ValueError:
                    options['settings']['max_results'] = None

            jira = get_jira_client(options['connection'])
            query_manager = QueryManager(jira, options['settings'])
            zip_data = get_archive(CALCULATORS, query_manager, options['settings'])
            data = base64.b64encode(zip_data).decode('ascii')
        except Exception as e:
            logger.error("%s", e)
            has_error = True

    return render_template('results.html',
        data=data,
        has_error=has_error,
        log=log_buffer.getvalue()
    )

# Helpers

@contextlib.contextmanager
def capture_log(buffer, level, formatter=None):
    """Temporarily write log output to the StringIO `buffer` with log level
    threshold `level`, before returning logging to normal.
    """
    root_logger = logging.getLogger()
    
    old_level = root_logger.getEffectiveLevel()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(buffer)

    if formatter:
        formatter = logging.Formatter(formatter)
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    yield

    root_logger.removeHandler(handler)
    root_logger.setLevel(old_level)

    handler.flush()
    buffer.flush()

def override_options(options, form):
    """Override options from the configuration files with form data where
    applicable.
    """
    for key in options.keys():
        if key in form and form[key] != "":
            options[key] = form[key]

def get_jira_client(connection):
    """Create a JIRA client with the given connection options
    """

    url = connection['domain']
    username = connection['username']
    password = connection['password']
    jira_client_options = connection['jira_client_options']

    jira_options = {'server': url}
    jira_options.update(jira_client_options)

    try:
        return JIRA(jira_options, basic_auth=(username, password))
    except Exception as e:
        if e.status_code == 401:
            raise ConfigError("JIRA authentication failed. Check URL and credentials, and ensure the account is not locked.") from None
        else:
            raise

def get_archive(calculators, query_manager, settings):
    """Run all calculators and write outputs to a temporary directory.
    Create a zip archive of all the files written, and return it as a bytes
    array. Remove the temporary directory on completion.
    """
    zip_data = b''

    cwd = os.getcwd()
    temp_path = tempfile.mkdtemp()

    try:
        os.chdir(temp_path)
        run_calculators(calculators, query_manager, settings)

        with zipfile.ZipFile('metrics.zip', 'w', zipfile.ZIP_STORED) as z:
            for root, dirs, files in os.walk(temp_path):
                for file_name in files:
                    if file_name != 'metrics.zip':
                        z.write(os.path.join(root, file_name), os.path.join('metrics', file_name))
        with open('metrics.zip', 'rb') as metrics_zip:
            zip_data = metrics_zip.read()

    finally:
        os.chdir(cwd)
        shutil.rmtree(temp_path)
    
    return zip_data
