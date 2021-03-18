"""
Work Item Tracking
"""
import datetime
from azure.devops.v5_1.work_item_tracking.models import Wiql
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


def get_work_items(context):
    wit_client = context.connection.clients.get_work_item_tracking_client()

    desired_ids = range(1, 51)
    work_items = wit_client.get_work_items(ids=desired_ids, error_policy="omit")

    for id_, work_item in zip(desired_ids, work_items):
        if work_item:
            print_work_item(work_item)
        else:
            emit("(work item {0} omitted by server)".format(id_))

    return work_items


def get_work_items_as_of(context):
    wit_client = context.connection.clients.get_work_item_tracking_client()

    desired_ids = range(1, 51)
    as_of_date = datetime.datetime.now() + datetime.timedelta(days=-7)
    work_items = wit_client.get_work_items(
        ids=desired_ids, as_of=as_of_date, error_policy="omit"
    )

    for id_, work_item in zip(desired_ids, work_items):
        if work_item:
            print_work_item(work_item)
        else:
            emit("(work item {0} omitted by server)".format(id_))

    return work_items


def wiql_query(context):
    wit_client = context.connection.clients.get_work_item_tracking_client()
    wiql = Wiql(
        query="""
            select [System.Id],
                [System.WorkItemType],
                [System.Title],
                [System.State],
                [System.AreaPath],
                [System.IterationPath],
                [System.Tags]
            from WorkItems
            order by [System.ChangedDate] desc"""
    )
    # where[System.WorkItemType] = 'Test Case'

    # We limit number of results to 30 on purpose
    wiql_results = wit_client.query_by_wiql(wiql, top=30).work_items
    # emit("Results: {0}".format(len(wiql_results)))

    if wiql_results:
        # WIQL query gives a WorkItemReference with ID only
        # => we get the corresponding WorkItem from id
        work_items = (
            wit_client.get_work_item(int(res.id)) for res in wiql_results
        )

        # for work_item in work_items:
        #    print_work_item(work_item)
        return work_items
    else:
        return []


def work_item_field_as_of(context, desired_id, desired_field_name, as_of_date):
    dt_object = datetime.datetime.strftime(as_of_date, '%Y-%m-%dT%H:%M:%S.%f')
    as_of_date = dt_object
    wit_client = context.connection.clients.get_work_item_tracking_client()
    work_items = wit_client.get_work_items(ids=desired_id, error_policy="omit", as_of=as_of_date)

    for item in work_items:
        json_str = json.dumps(parse_json(item))
        json_obj = json.loads(json_str)
        field_value = json_obj['fields'][desired_field_name]

    """    
    wiql = Wiql(
        query="select " + field_name + "from WorkItems "
              + "Where [System.Id] ==" + azure_id \
              + " order by [System.ChangedDate] desc"
    )
    wiql_results = wit_client.query_by_wiql(wiql).work_items
    """
    #print(json_obj['fields']['System.AreaPath'])
    return field_value
