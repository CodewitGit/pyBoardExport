from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import pprint

# Fill in with your personal access token and org URL
personal_access_token = 'eplq2ni5seffqdc2sj7ksr3jlat7pk6vbbqldx5ml2re4e3soifa'
organization_url = 'https://dev.azure.com/PyOrg'


def connect(token, org):
    # Create a connection to the org
    credentials = BasicAuthentication('', token)
    return Connection(base_url=org, creds=credentials)


def get_projects():

    connection = connect(personal_access_token, organization_url)
    # Get a client (the "core" client provides access to projects, teams, etc)
    core_client = connection.clients.get_core_client()

    # Get the first page of projects
    get_projects_response = core_client.get_projects()
    index = 0
    while get_projects_response is not None:
        for project in get_projects_response.value:
            pprint.pprint("[" + str(index) + "] " + project.name)
            index += 1
        if get_projects_response.continuation_token is not None and get_projects_response.continuation_token != "":
            # Get the next page of projects
            get_projects_response = core_client.get_projects(continuation_token=get_projects_response.continuation_token)
        else:
            # All projects have been retrieved
            get_projects_response = None


if __name__ == '__main__':
    get_projects()


