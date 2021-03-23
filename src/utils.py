"""
Utility methods
"""
import datetime
import logging
import json
import re
import ast
from dateutil import rrule
import csv
from pandas import DataFrame
import pandas as pd
from exceptions import AccountStateError
import http_logging
from typing import Union, List
import numpy as np

logger = logging.getLogger(__name__)


def emit(msg, *args):
    print(msg % args)


def find_any_project(context):
    logger.debug('finding any project')

    # if we already contains a looked-up project, return it
    if hasattr(context.runner_cache, 'project'):
        logger.debug('using cached project %s', context.runner_cache.project.name)
        return context.runner_cache.project

    with http_logging.temporarily_disabled():
        core_client = context.connection.clients.get_core_client()
        projects = core_client.get_projects()

    try:
        context.runner_cache.project = projects[0]
        logger.debug('found %s', context.runner_cache.project.name)
        return context.runner_cache.project
    except IndexError:
        raise AccountStateError('Your account doesn''t appear to have any projects available.')


def find_any_repo(context):
    logger.debug('finding any repo')

    # if a repo is cached, use it
    if hasattr(context.runner_cache, 'repo'):
        logger.debug('using cached repo %s', context.runner_cache.repo.name)
        return context.runner_cache.repo

    with http_logging.temporarily_disabled():
        project = find_any_project(context)
        git_client = context.connection.clients.get_git_client()
        repos = git_client.get_repositories(project.id)

    try:
        context.runner_cache.repo = repos[0]
        return context.runner_cache.repo
    except IndexError:
        raise AccountStateError('Project "%s" doesn''t appear to have any repos.' % (project.name,))


def find_any_build_definition(context):
    logger.debug('finding any build definition')

    # if a repo is cached, use it
    if hasattr(context.runner_cache, 'build_definition'):
        logger.debug('using cached definition %s', context.runner_cache.build_definition.name)
        return context.runner_cache.build_definition

    with http_logging.temporarily_disabled():
        project = find_any_project(context)
        build_client = context.connection.clients.get_build_client()
        definitions = build_client.get_definitions(project.id)

    try:
        context.runner_cache.build_definition = definitions[0]
        return context.runner_cache.build_definition
    except IndexError:
        raise AccountStateError('Project "%s" doesn''t appear to have any build definitions.' % (project.name,))


def write_json(json_txt, output_file):
    logger.debug("Writing json file %s", output_file)
    with open(output_file, "w+") as write_file:
        json.dump(json_txt, write_file, indent=4, sort_keys=True)


def clean_json_string(dirty_json):
    json_string = str(dirty_json).replace("  ", ' ')
    json_string = json_string.replace(" '", ' "')
    json_string = json_string.replace("' ", '" ')
    json_string = json_string.replace("{'", '{"')
    json_string = json_string.replace("'}", '"}')
    json_string = json_string.replace(":'", ':"')
    json_string = json_string.replace("':", '":')
    json_string = json_string.replace(",'", ',"')
    json_string = json_string.replace("',", '",')

    json_string = json_string.replace("'", '"')
    json_string = json_string.replace('"""', '""')
    json_string = re.sub("(<[^>]+>)", '""', json_string)
    json_string = json_string.replace('None', '""')
    json_string = json_string.replace("\n", '')
    # json_string = json_string.replace(".", "").replace(" ", "")
    json_string = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_string)
    if json_string is not None:
        return json_string
    else:
        return {}


def json_sanitize(value: Union[str, dict, list], is_value=True) -> Union[str, dict, list]:
    """
    Modified version of https://stackoverflow.com/a/45526935/2635443

    Recursive function that allows to remove any special characters from json, especially unknown control characters
    """
    logger.debug("Sanitizing JSON")

    if isinstance(value, dict):
        value = {json_sanitize(k, False): json_sanitize(v, True) for k, v in value.items()}
    elif isinstance(value, list):
        value = [json_sanitize(v, True) for v in value]
    elif isinstance(value, str):
        if not is_value:
            # Remove dots from value names
            value = re.sub(r"[.]", "", value)
        else:
            # Remove all control characters
            value = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', value)
    return value


def convert_work_item_to_dataframe(work_items):
    logger.debug("Converting Workitems List to Dataframe")

    workitems_df_list: List[DataFrame] = []
    rec_count = 0
    for work_item in work_items:
        field_names = []
        for field in work_item.fields:
            field_names.append(field)

        wi = pd.DataFrame(work_item.fields, index=[rec_count])
        workitems_df_list.append(wi)
        rec_count += 1

        """row = "{0},{1},{2},{3},{4},{5},{6}".format(
            work_item.id,
            work_item.fields["System.TeamProject"],
            work_item.fields["System.WorkItemType"],
            work_item.fields["System.Title"],
            work_item.fields["System.State"],
            work_item.fields["Microsoft.VSTS.Common.Priority"],
            work_item.fields["System.CreatedDate"]
        )
        workitems_df_list.append(pd.DataFrame(list(reader([row]))))
    """

    try:
        workitems_final_df = pd.concat(workitems_df_list)
    except ValueError as e:
        logger.log("No data to convert to Dataframe - Error: ", e)
        print("No data to convert to Dataframe. Review Program Only Wiql query")

    return workitems_final_df


def parse_json(json_file_name):
    list_of_json = []
    with open(json_file_name) as edstats:
        data = json.load(edstats)
        for row in data:
            try:
                row = ast.literal_eval(row)
                row = json.dumps(row)
            except ValueError as e:
                print("Error in JSON: ", e)
                break

            # print(row['fields']['System.Title'])
            if row is not None:
                row = json_sanitize(row)
                row = json.dumps(row)
                list_of_json.append(row)


    return list_of_json


def weeks_between(start_date, end_date):
    x = pd.to_datetime(end_date) - pd.to_datetime(start_date)
    return int(x / np.timedelta64(1, 'W'))




def calc_pct_completion(item_start_date, item_end_date, curr_week_starting):
    if str(item_start_date) != 'nan' and str(item_end_date) != 'nan':
        try:
            start_date = datetime.datetime.strptime(str(item_start_date), '%Y-%m-%dT%H:%M:%SZ').date()
            end_date = datetime.datetime.strptime(str(item_end_date), '%Y-%m-%dT%H:%M:%SZ').date()
            curr_week_starting = datetime.datetime.strptime(str(curr_week_starting), '%Y-%m-%d %H:%M:%S').date()
            tot_weeks_wi = weeks_between(start_date, end_date)
            weeks_passed = weeks_between(start_date, curr_week_starting)
            pct = (weeks_passed / tot_weeks_wi) * 100
            if pct >= 100:
                pct = 100
        except TypeError as e:
            logger.debug("Type Error: Args %s, %s", item_start_date, item_end_date)
            print(item_start_date, item_end_date, curr_week_starting, e)
    else:
        pct = 0

    return pct


def write_df_to_csv(data_frame, output_file_name):
    logger.debug("Writing out csv file %s", output_file_name)
    data_frame.to_csv(output_file_name, sep=',', index=False, mode='w', quoting=csv.QUOTE_ALL, quotechar='"',
                      escapechar="\\")



