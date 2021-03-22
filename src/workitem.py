"""Implementation of Azure DevOps WorkItems
"""
import datetime
from azure.devops.v6_0.work_item_tracking.models import Wiql
from utils import *
import csv
import ast
import pandas as pd
logger = logging.getLogger(__name__)


def print_work_item(work_item):
    emit(
        "{0} {1}: {2}".format(
            work_item.fields["System.WorkItemType"],
            work_item.id,
            work_item.fields["System.Title"],
        )
    )


def get_work_items(context, desired_id_range=None):
    if desired_id_range is None:
        desired_ids = range(1, 51)
    else:
        desired_ids = desired_id_range.split(',')

    wit_client = context.connection.clients.get_work_item_tracking_client()
    work_items = wit_client.get_work_items(ids=desired_ids, error_policy="omit")

    for id_, work_item in zip(desired_ids, work_items):
        if work_item:
            print_work_item(work_item)
        else:
            emit("(work item {0} omitted by server)".format(id_))

    return work_items


def get_work_items_as_of(context, as_of_date=None):
    wit_client = context.connection.clients.get_work_item_tracking_client()

    if as_of_date is not None:
        as_of_date = datetime.datetime.strftime(as_of_date, '%Y-%m-%dT%H:%M:%S')
    else:
        as_of_date = datetime.datetime.now()

    work_items = wit_client.get_work_items(
        as_of=as_of_date, error_policy="omit"
    )
    return work_items


def wiql_query(context, top_n=None, program_only=None, fields_array=None, as_of_date=None):

    if as_of_date is not None:
        as_of_date = datetime.datetime.strptime(str(as_of_date), '%Y-%m-%d %H:%M:%S')

    if fields_array is None:
        fields_array = ["System.WorkItemType",
                        "System.Title",
                        "System.State",
                        "System.AreaPath",
                        "System.IterationPath",
                        "Custom.GreenStartDate",
                        "Custom.RedStartDate",
                        "Custom.GreenEndDate",
                        "Custom.RedEndDate",
                        "Custom.DeliverableType",
                        "Custom.ProgressPercentageComplete",
                        "System.BoardColumn",
                        "System.ChangedDate",
                        "System.State",
                        "System.Tags"]

    wit_client = context.connection.clients.get_work_item_tracking_client()
    if not program_only:
        query = """
                select [System.Id]
                from WorkItems
                order by [System.ChangedDate] desc"""

    else:

        query = """
                select [System.Id]
                from WorkItems
                Where [System.Tags] Contains "Prog Deliverable L1"
                order by [System.ChangedDate] desc"""

    wiql = Wiql(query)

    # We limit number of results is top_n is supplied
    if top_n is None:
        wiql_results = wit_client.query_by_wiql(wiql).work_items
    else:
        wiql_results = wit_client.query_by_wiql(wiql, top=top_n).work_items
    emit("Extract Count: {0}".format(len(wiql_results)))

    if wiql_results:
        # WIQL query gives a WorkItemReference with ID only
        # => we get the corresponding WorkItem from id
        work_items = (
            wit_client.get_work_item(int(res.id), fields=fields_array, as_of=as_of_date) for res in wiql_results
        )

        return work_items
    else:
        return []


# Using WIQL
def get_program_work_items_data_frame(context, top_n=None, fields_array=None, as_of_date=None):

    if as_of_date is not None:
        as_of_date = datetime.datetime.strptime(str(as_of_date), '%Y-%m-%d %H:%M:%S')

    if top_n is None:
        work_items = wiql_query(context, program_only=True, fields_array=fields_array, as_of_date=as_of_date)
    else:
        work_items = wiql_query(context, top_n, program_only=True, fields_array=fields_array, as_of_date=as_of_date)

    df = convert_work_item_to_dataframe(work_items)
    #write_df_to_csv(data_frame=df, output_file_name=extract_file)
    return df


# Uses WI Tracking Client
def get_work_items_as_of(context, desired_id_range, as_of_date=None, fields=None):

    rng = desired_id_range.split(',')

    if fields is None:
        fields = ["id", "System.Tags", "System.Title", "System.TeamProject"]

    if desired_id_range:
        desired_id_range = range(int(rng[0]), int(rng[1]))
    if as_of_date is not None:
        as_of_date = datetime.datetime.strptime(str(as_of_date), '%Y-%m-%d %H:%M:%S')
    else:
        as_of_date = datetime.datetime.now()

    wit_client = context.connection.clients.get_work_item_tracking_client()
    work_items = wit_client.get_work_items(ids=desired_id_range, error_policy="omit", as_of=as_of_date, fields=fields)

    return work_items

