"""Implementation of Azure DevOps WorkItems
"""
import math
import numpy
from azure.devops.v6_0.work_item_tracking.models import Wiql
from utils import *


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
                Where [System.Tags] Contains "Prog Deliverable L1" or [System.Tags] Contains "Prog Deliverable L2"
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


# Wiql Filter String
def wiql_query_with_filter(context, top_n=None, program_only=None, fields_array=None, as_of_date=None,
                           filter_string=None):

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
        if filter_string is None:
            filter_string = ""
        else:
            filter_string = " where " + filter_string

        query = """
                select [System.Id]
                from WorkItems
                """ + filter_string + " order by [System.ChangedDate] desc"""
    else:
        if filter_string is None:
            filter_string = ""
        else:
            filter_string = " and " + filter_string

        query = """
                select [System.Id]
                from WorkItems
                Where ([System.Tags] Contains "Prog Deliverable L1" or [System.Tags] Contains "Prog Deliverable L2")
                  """ + filter_string + """ order by [System.ChangedDate] desc"""

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
        work_items = wiql_query_with_filter(context, program_only=True, fields_array=fields_array, as_of_date=as_of_date)
    else:
        work_items = wiql_query_with_filter(context, top_n, program_only=True, fields_array=fields_array, as_of_date=as_of_date)

    df = convert_work_item_to_dataframe(work_items)
    #write_df_to_csv(data_frame=df, output_file_name=extract_file)
    return df


# Using WIQL
def get_program_work_item_data_frame(context, work_item_id, fields_array=None, as_of_date=None):
    logger.debug("Getting Workitem for %s", work_item_id)
    if as_of_date is not None:
        as_of_date = datetime.datetime.strptime(str(as_of_date), '%Y-%m-%d %H:%M:%S')

        work_items = wiql_query_with_filter(context, program_only=True, fields_array=fields_array,
                                            as_of_date=as_of_date, filter_string="[System.Id] = " + str(work_item_id))

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


def get_work_item_percent_as_of(context, df_work_items, current_week, as_of_week, test_run):
    """
    :param context: Pass the current Context
    :param df_work_items: Work Item for which the red, white and actual completion percentage need to be calculated
    :param current_week: This Week starting (Monday)
    :param as_of_week: As of Week date to get Historic Completion Percentage
    :param test_run: Boolean
    :return: List of Red, Green and Actual (White) percentage of completion
    """
    df_intr = []

    prev_white_pct = 0
    white_pct = 0

    if weeks_between(datetime.datetime.strptime(str(as_of_week), '%Y-%m-%d %H:%M:%S').date(), datetime.datetime.strptime(str(current_week), '%Y-%m-%d %H:%M:%S').date()) <= 0:
        as_of_week_starting = current_week
        future_week = True
    else:
        as_of_week_starting = as_of_week
        future_week = False

    # For each Work Item with Program Deliverable Tag
    for wi_index, wi_row in df_work_items.iterrows():
        # Set previous white_pct to 0.

        current_wi_id = wi_row['System.Id']
        logger.debug("Processing Work Item %s", current_wi_id)

        # Calculate GREEN Progress %
        green_pct = calc_pct_completion(wi_row['Custom.GreenStartDate'], wi_row['Custom.GreenEndDate'],
                                        as_of_week_starting)

        # Calculate RED Progress %
        red_pct = calc_pct_completion(wi_row['Custom.RedStartDate'], wi_row['Custom.RedEndDate'], as_of_week_starting)

        id = current_wi_id
        id = str(id) + ',' + str(id + 1)

        # if context.future_actuals_are_None and current_week
        if context.future_actuals_are_None and future_week:
            white_pct = float(numpy.nan)

        elif prev_white_pct < 100:
            # Get White Progress % from the WorkItem as of given Week Starting Date
            df_wi_tmp = get_work_items_as_of(context, as_of_date=as_of_week_starting, desired_id_range=id,
                                             fields=context.fields_array)

            # Parse and retrieve the ProgressPercentageComplete
            for it in df_wi_tmp:
                try:
                    white_pct = int(it.fields["Custom.ProgressPercentageComplete"])

                except KeyError as e:
                    # Key Error occurs when the Key not found in the object
                    # When the field was not updated as of the given date, the value should be set to 0
                    white_pct = 0

        else:
            white_pct = 100

        try:
            white_pct = round(white_pct)
        except ValueError:
            white_pct = float(numpy.nan)
        prev_white_pct = white_pct

        # WARNING : Any alteration in the below statement would need further changes at the Dataframe column definition
        df_intr.append([current_wi_id, as_of_week_starting.date(),
                        round(green_pct), round(red_pct), white_pct])

        # If Text Exit in 5 iterations
        if test_run and wi_index > 5:
            break

    return df_intr
