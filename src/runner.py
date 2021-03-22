# --------------------------------------------------------------------------------------------
# @Description  :   Simple DevOps Project - Work Items Extractor
# @Author       :   Kannan Ramamoorthy
# @Last updated :   22 Mar 2021
# --------------------------------------------------------------------------------------------

"""
@ Azure DevOps Python API - Work Item Extractor.
@ Usage:
    Update src/devops-runner-config.json
        - project url
        - azure devops 'Personal Auth Token'
        - project name
        - project start date
        - project end date

    Updated src/runner.py
        - Update Configs as required
            __TASK__ = "work-item-extractor"
            __VERSION__ = "1.0.0"
            __CONFIG_FILE__ = "devops-runner-config-test.json"
            __OUT_FILE__ = "out/WorkItemTracking.csv"
            __DUMP_FILE__ = "out/WorkItemExtract.csv"
        - fields_array -> Add/updated the fields to be extracts
        - df_tmp.columns -> list of columns for dataframe after %completion calculation
        - df_intr.append -> list of columns for dataframe after %completion calculation
        - Update all Custom fields as necessary

"""

import os
from types import SimpleNamespace
from azure.devops.credentials import BasicAuthentication
from azure.devops.connection import Connection
from workitem import *
from config import Config
from utils import *
import time

__TASK__ = "work-item-extractor"
__VERSION__ = "1.0.0"
__CONFIG_FILE__ = "devops-runner-config-test.json"
__OUT_FILE__ = "out/WorkItemTracking.csv"
__DUMP_FILE__ = "out/WorkItemExtract.csv"

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
    conf = Config(filename=__CONFIG_FILE__).config
    context = SimpleNamespace()
    context.runner_cache = SimpleNamespace()

    # setup the connection
    context.connection = Connection(
        base_url=conf['url'],
        creds=BasicAuthentication('PAT', conf['pat']),
        user_agent=__TASK__ + '/' + __VERSION__)
    context.project_name = conf['project_name']
    context.project_start_date = conf['project_start_date']
    context.project_end_date = conf['project_end_date']
    return context


def main(output_path=None, test_run=True):
    context = init()

    if test_run:
        top_count = 5
    else:
        top_count = None

    if output_path:
        # monkey-patch the get_client method to attach our hook
        _get_client = context.connection.get_client

    # List fields to Extract Initially
    fields_array = ["System.Id",
                    "Custom.GreenStartDate",
                    "Custom.RedStartDate",
                    "Custom.GreenEndDate",
                    "Custom.RedEndDate",
                    "Custom.DeliverableType",
                    "Custom.ProgressPercentageComplete",
                    "System.WorkItemType",
                    "System.Title",
                    "System.State",
                    "System.AreaPath",
                    "System.IterationPath",
                    "System.BoardColumn",
                    "System.ChangedDate",
                    "Custom.Phase",
                    "Custom.DeliverableType",
                    "Custom.RAGStatus",
                    "System.Tags"]

    # Get list of Mondays from beginning of Project
    num_of_project_weeks = weeks_between(context.project_start_date, context.project_end_date)
    num_of_past_weeks = weeks_between(context.project_start_date, datetime.date.today())
    list_range = pd.date_range(context.project_start_date, periods=num_of_project_weeks, freq="W-MON")
    df_all_weeks = pd.DataFrame({'week_starting': list_range})
    current_week = datetime.datetime.strptime(str(list_range[num_of_past_weeks - 1]), '%Y-%m-%d %H:%M:%S')

    # Get all Program Work items
    df_work_items = get_program_work_items_data_frame(context, fields_array=fields_array, as_of_date=current_week,
                                                      top_n=top_count)

    # Write the extract dump to csv file
    write_df_to_csv(df_work_items, __DUMP_FILE__)

    df_intr = []
    # Add Column for each week
    for index, row in df_all_weeks.iterrows():
        # Column name as Week Name
        loop_week_starting = datetime.datetime.strptime(str(row['week_starting']), '%Y-%m-%d %H:%M:%S')

        # Set previous white_pct to 0.
        prev_white_pct = 0
        white_pct = 0
        # For each Work Item
        for wi_index, wi_row in df_work_items.iterrows():
            current_wi_id = wi_row['System.Id']

            # Calculate Green Progress %
            green_pct = get_pct_completion(wi_row['Custom.GreenStartDate'], wi_row['Custom.GreenEndDate'],
                                           loop_week_starting)

            # Calculate Red Progress %
            red_pct = get_pct_completion(wi_row['Custom.RedStartDate'], wi_row['Custom.RedEndDate'], loop_week_starting)

            # Get White Progress % from the WorkItem as of given Week Starting Date
            as_of_week_starting = loop_week_starting

            if loop_week_starting > current_week:
                as_of_week_starting = loop_week_starting

            id = current_wi_id
            id = str(id) + ',' + str(id + 1)

            if prev_white_pct < 100:
                df_wi_tmp = get_work_items_as_of(context, as_of_date=as_of_week_starting, desired_id_range=id,
                                                 fields=fields_array)

                for it in df_wi_tmp:
                    try:
                        white_pct = it.fields["Custom.ProgressPercentageComplete"]

                    except KeyError:
                        white_pct = 0

            else:
                white_pct = 100

            prev_white_pct = white_pct

            # Note: Any alteration in the below statement would need further changes at the Dataframe column definition
            df_intr.append([current_wi_id, loop_week_starting.date(),
                            round(green_pct), round(red_pct), round(white_pct), wi_row['Custom.Phase'],
                            wi_row['Custom.RAGStatus'], wi_row['System.State'], wi_row['Custom.DeliverableType']])

        # If Text Exit in 5 iterations
        if test_run and index > 5:
            break

    # Convert to Dataframe
    df_tmp = pd.DataFrame(df_intr)
    df_tmp.columns = ['id', 'week_starting', 'green_pct', 'red_pct', 'white_pct', 'phase', 'RAGStatus',
                      'State', 'DeliverableType']

    df_tmp.sort_values(['id', 'week_starting'])

    # Write Data frame result to CSV
    write_df_to_csv(df_tmp, output_file_name=__OUT_FILE__)

    if test_run:
        print(df_tmp)


if __name__ == '__main__':
    # Program Started
    start = time.time()

    print("Initiated at ", datetime.datetime.now())

    # Execute Extracting Process
    main(test_run=True)
    #main(test_run=False)

    # Execution Complete
    print("Extract Completed")
    end = time.time()
    hours, rem = divmod(end - start, 3600)
    minutes, seconds = divmod(rem, 60)
    print("Time taken: {:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))
