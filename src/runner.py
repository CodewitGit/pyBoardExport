"""
Azure DevOps Python API - Work Item Extractor.
"""

import logging
import os
import pathlib
import sys
from types import SimpleNamespace
from azure.devops.credentials import BasicAuthentication
from azure.devops.connection import Connection
from workitem import *
from config import Config
from utils import *

__TASK__ = "work-item-extractor"
__VERSION__ = "1.0.0"
__CONFIG_FILE__ = "azure-devops-extract-PROD-config.json"
__OUT_FILE__ = "WorkItemExtract.json"

# Create Logs folder is no Exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Create output folder
if not os.path.exists("out"):
    os.makedirs("out")

# Default Logging DEBUG mode
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S', filename='logs/run.log', filemode='w')


def init():
    conf = Config(filename='src/' + __CONFIG_FILE__).config
    context = SimpleNamespace()
    context.runner_cache = SimpleNamespace()

    # setup the connection
    context.connection = Connection(
        base_url=conf['url'],
        creds=BasicAuthentication('PAT', conf['pat']),
        user_agent=__TASK__ + '/' + __VERSION__)
    return context


def extract_work_items(context):

    work_items = wiql_query(context)
    parsed_json =[]
    for wi in work_items:
        parsed_json.append(parse_json(wi))

    write_json(parsed_json, output_file="out/" + __OUT_FILE__)



def main(output_path=None):
    context = init()

    # if the user asked for logging:
    # - add a hook for logging the http request
    # - create the root directory
    if output_path:
        # monkey-patch the get_client method to attach our hook
        _get_client = context.connection.get_client

    extract_work_items(context)

if __name__ == '__main__':
    main()
