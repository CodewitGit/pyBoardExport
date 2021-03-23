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
from tqdm import *

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

    # Setup the connection
    context.connection = Connection(
        base_url=conf['url'],
        creds=BasicAuthentication('PAT', conf['pat']),
        user_agent=__TASK__ + '/' + __VERSION__)
    context.project_name = conf['project_name']
    context.project_start_date = conf['project_start_date']
    context.project_end_date = conf['project_end_date']
    context.url = conf['url']
    context.test_run = conf['test_run']
    context.test_work_item_id = conf['test_work_item_id']
    context.future_actuals_are_None = conf['future_actuals_are_None']
    context.fields_array = conf['fields_array']

    return context


def main(output_path=None):
    context = init()
    test_run = context.test_run
    test_work_item_id = context.test_work_item_id

    if test_run:
        top_count = 5
    else:
        top_count = None

    if output_path:
        # monkey-patch the get_client method to attach our hook
        _get_client = context.connection.get_client

    # Log Config
    logger.info("--------CONFIG--------------")
    logger.info("Project     : %s", context.project_name)
    logger.info("Start Date  : %s", context.project_start_date)
    logger.info("Start Date  : %s", context.project_end_date)
    logger.info("url         : %s", context.url)
    logger.info("Test Run    : %s", context.test_run)
    logger.info("Test Work Item    : %s", test_work_item_id)
    logger.info("Set future actual percent None: %s", context.future_actuals_are_None)
    logger.info("Field list array : %s", context.fields_array)

    # List fields to Extract Initially
    fields_array = context.fields_array

    # Get list of Mondays from beginning of Project
    today = str(datetime.date.today())

    # If Project End Date has passed already, then Today is set to Project End Date
    if weeks_between(today, context.project_end_date) <= 0:
        today = context.project_end_date

    num_of_project_weeks = weeks_between(context.project_start_date, context.project_end_date)
    num_of_past_weeks = weeks_between(context.project_start_date, today)

    # Get all Week Starting between project start and end date
    list_range = pd.date_range(context.project_start_date, periods=num_of_project_weeks, freq="W-MON")
    df_all_weeks = pd.DataFrame({'week_starting': list_range})
    current_week = datetime.datetime.strptime(str(today), '%Y-%m-%d')

    # Get all Program Deliverable Work items Only
    if test_run:
        print("Test Run with Work item ", test_work_item_id)
        df_work_items = get_program_work_item_data_frame(context, fields_array=fields_array, as_of_date=current_week,
                                                         work_item_id=test_work_item_id)
    else:
        df_work_items = get_program_work_items_data_frame(context, fields_array=fields_array, as_of_date=current_week,
                                                          top_n=top_count)

    work_item_count = len(df_work_items)
    total_weeks = len(df_all_weeks)
    total_iteration = work_item_count * total_weeks
    pbar = tqdm(total=total_iteration)

    current_iteration = 0

    # Write the extract dump to csv file
    write_df_to_csv(df_work_items, __DUMP_FILE__)
    logger.info("Extract Dump Created at %s", __DUMP_FILE__)

    df_intr = []
    # For each week from Start to End of Project
    for index, row in df_all_weeks.iterrows():
        # Column name as Week Name
        loop_week_starting = datetime.datetime.strptime(str(row['week_starting']), '%Y-%m-%d %H:%M:%S')

        # Calculate Percentage for Each Week
        """
        # For each Work Item with Program Deliverable Tag
        for wi_index, wi_row in df_work_items.iterrows():
            # Set previous white_pct to 0.
            prev_white_pct = 0
            white_pct = 0

            current_wi_id = wi_row['System.Id']

            # Calculate Green Progress %
            green_pct = calc_pct_completion(wi_row['Custom.GreenStartDate'], wi_row['Custom.GreenEndDate'],
                                            loop_week_starting)

            # Calculate Red Progress %
            red_pct = calc_pct_completion(wi_row['Custom.RedStartDate'], wi_row['Custom.RedEndDate'], loop_week_starting)

            # Get White Progress % from the WorkItem as of given Week Starting Date
            as_of_week_starting = loop_week_starting

            if loop_week_starting > current_week:
                as_of_week_starting = loop_week_starting

            id = current_wi_id
            id = str(id) + ',' + str(id + 1)

            # Fetch Completion Percentage as of Given date
            if prev_white_pct < 100:
                df_wi_tmp = get_work_items_as_of(context, as_of_date=as_of_week_starting, desired_id_range=id,
                                                 fields=fields_array)

                for it in df_wi_tmp:
                    try:
                        white_pct = int(it.fields["Custom.ProgressPercentageComplete"])
                        print(int(it.fields["Custom.ProgressPercentageComplete"]))

                    except KeyError:
                        white_pct = 0

            else:
                white_pct = 100

            prev_white_pct = white_pct


            # WARNING : Any alteration in the below statement would need further changes at the Dataframe column definition
            df_intr.append([current_wi_id, loop_week_starting.date(),
                            round(green_pct), round(red_pct), round(white_pct)])

        # If Text Exit in 5 iterations
        if test_run and index > 5:
            break
        """
        res = get_work_item_percent_as_of(context, df_work_items=df_work_items, current_week=current_week,
                                          as_of_week=loop_week_starting, test_run=test_run)
        for item in res:
            df_intr.insert(0, item)

        current_iteration += work_item_count
        progress_bar = round((current_iteration / total_iteration) * 100)
        pbar.update(n=work_item_count)
        #print("Progress: ", progress_bar, "%")
    # Convert the result (Historical Progress Percentages) to Dataframe
    df_tmp = pd.DataFrame(df_intr)

    # Match the number of fields as per df_intr dataframe columns
    df_tmp.columns = ['id', 'report_date', 'green_forecast_percent', 'red__forecast_percent', 'actual_percent']

    df_tmp.sort_values(['id', 'report_date'])

    # Write Data frame result to CSV
    write_df_to_csv(df_tmp, output_file_name=__OUT_FILE__)

    if test_run:
        print(df_tmp)


if __name__ == '__main__':
    # Program Started
    start = time.time()
    logger.info("***** Extract Execution Started *****")
    print("Initiated at ", datetime.datetime.now())

    # Execute Extracting Process
    main()

    # Execution Complete
    end = time.time()
    hours, rem = divmod(end - start, 3600)
    minutes, seconds = divmod(rem, 60)
    print("Time taken: {:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))
    logger.info("***** Extract Execution Ended *****")
