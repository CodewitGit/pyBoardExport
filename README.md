#Overview

The CensusInsight project helps to extract Workitems from Azure DevOps filtered by tags. 
It also extracts the historic completion percentage (custom field) to plot the graphs as we progress.

* **Tag Filters** - Extract workitems filtered with Project **AND** Tags;
* **Configurable** - Configure fileds to extract, and Project 

It can also calculate **projected and completed percentage** 

---------------------------------

# Setup
1. Install Python 3.6 or Above
2. Checkout the code from Repo
3. Update Configuration File
4. Install all required dependencies

# Usage

```bash
#To run the script

$ python ./runner
```

```bash
#To run the script with Configuration Override

$ python ./runner -c config-file.json
```

# Features
The main repository contains the CensusInsight project source.

## Configuration
The configuration file is a simple JSON file which resides in the /src directory.

**Note** The default config file should be named as "devops-runner-config.json" under ./src directory

```JSON
{
  "project_name": "Census 2023",
  "project_start_date": "2020-11-30",
  "project_end_date": "2023-11-30",
  "url": "https://statisticsnz.visualstudio.com",
  "pat": "<Personal Access Token>",
  "tags": ["Prog Deliverable L1", "Prog Deliverable L2"],
  "test_run": false,
  "test_work_item_id": 20036,
  "future_actuals_are_None": true,
  "fields_array": ["System.Id",
                    "Custom.GreenStartDate",
                    "Custom.RedStartDate",
                    "Custom.GreenEndDate",
                    "Custom.RedEndDate",
                    "Custom.RAGStatus"
                    ]
}
```

## Options
User can override the default config file by using a custom config file in the above mention format.

```bash
#To run the script with Configuration Override

$ python ./runner -c config-file.json
```

## Output
Two csv files are extracted into ./src/out folder from Azure DevOps for the given Project. These files will be overwritten evey time its extracted.
No mechanism is in place to archive and version control the files.

1. WorkItemExtract.csv
2. WorkItemTracking.csv