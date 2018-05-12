import os
import os.path
import shutil
import tempfile
import base64
import zipfile

from flask import Flask, render_template, request
from jira import JIRA

from ..config import config_to_options, CALCULATORS
from ..querymanager import QueryManager
from ..calculator import run_calculators

template_folder = os.path.join(os.path.dirname(__file__), "templates")
static_folder = os.path.join(os.path.dirname(__file__), "static")

app = Flask('jira-agile-metrics',
    template_folder=template_folder,
    static_folder=static_folder
)

@app.route("/")
def index():
    return render_template('index.html', max_results=request.args.get('max_results', ""))

@app.route("/run", methods=['POST'])
def run():
    config = request.files['config']
    error = None
    log = ""

    # TODO: Need to catch and log errors and print output from calculators
    # TODO: matplotlib-related crash when plotting more than one thing

    options = config_to_options(config.read())
    override_options(options['connection'], request.form)
    
    options['settings']['verbose'] = True
    if request.form.get('max_results'):
        try:
            options['settings']['max_results'] = int(request.form.get('max_results'))
        except ValueError:
            options['settings']['max_results'] = None

    jira = get_jira_client(options['connection'])
    query_manager = QueryManager(jira, options['settings'])
    data = get_archive(query_manager, options['settings'])

    return render_template('results.html',
        data=base64.b64encode(data).decode('ascii'),
        error=error,
        log=log
    )

# Helpers

def override_options(options, form):
    for key in options.keys():
        if key in form and form[key] != "":
            options[key] = form[key]

def get_jira_client(connection):
    url = connection['domain']
    username = connection['username']
    password = connection['password']
    jira_client_options = connection['jira_client_options']

    jira_options = {'server': url}
    jira_options.update(jira_client_options)

    jira = JIRA(jira_options, basic_auth=(username, password))
    return jira

def get_archive(query_manager, settings):
    zip_data = b''

    cwd = os.getcwd()
    temp_path = tempfile.mkdtemp()

    try:
        os.chdir(temp_path)
        run_calculators(CALCULATORS, query_manager, settings)

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
