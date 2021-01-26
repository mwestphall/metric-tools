#!/usr/bin/env python3

import argparse
import re
import sys

from datetime import datetime
from jira import JIRA


def dump(obj):
    for attr in dir(obj):
        print("obj.%s = %r" % (attr, getattr(obj, attr)))


def print_help(stream=sys.stderr):
    help_msg = """Usage: {0} -startdate YYYY-MM-DD -enddate YYYY-MM-DD
"""
    stream.write(help_msg.format(sys.argv[0]))


def parse_args():

    # The only syntax that is acceptable is:
    # <this> -startdate YYYY-MM-DD -enddate YYYY-MM-DD

    if len(sys.argv) not in [5, 6, 7, 8]:
        print_help()
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("-startdate", help="Start date")
    parser.add_argument("-enddate", help="End date")
    parser.add_argument("-detailed", help="Show detailed results", action="store_true")
    parser.add_argument("-hoursoff", help="Hours off by developers during this time period (vacation, sick days, etc.")
    args = parser.parse_args()

    start_datetime = args.startdate
    end_datetime = args.enddate
    hours_off = 0

    # Validate input
    if not re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', start_datetime):
        print("Error: -startdate argument must take YYYY-MM-DD format")
        sys.exit(1)
    if not re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', end_datetime):
        print("Error: -enddate argument must take YYYY-MM-DD format")
        sys.exit(1)
    try:
        start_datetime = datetime.strptime(start_datetime + " 00:00:01", "%Y-%m-%d %H:%M:%S")
    except:
        print(f"Error: Start date {start_datetime} is not a valid date")
        sys.exit(1)
    try:
        end_datetime = datetime.strptime(end_datetime + " 23:59:59", "%Y-%m-%d %H:%M:%S")
    except:
        print(f"Error: End date {end_datetime} is not a valid date")
        sys.exit(1)
    if args.hoursoff is not None:
        try:
            hours_off = int(args.hoursoff)
        except:
            print(f"Error: -hoursoff must supply an integer number of developer hours off")
            sys.exit(1)

    return {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "detailed": args.detailed,
        "hours_off": hours_off
    }


def main():

    # Parse arguments. Assume any error handling happens in parse_args()
    try:
        args = parse_args()
    except Exception as err:
        print(f"Failed to parse arguments: {err}", file=sys.stderr)

    start_datetime = args["start_datetime"]
    end_datetime = args["end_datetime"]
    detailed = args["detailed"]
    hours_off = args["hours_off"]

    # Connect to Jira
    options = {"server": "https://opensciencegrid.atlassian.net"}
    jira = JIRA(options)

    # Lookup all the members of the htcondor-developers Jira group
    #for member in jira.group_members("htcondor-developers"):
    #    print(member)
    # This requires authentication, which we don't want to embed in publicly available code
    # For now, let's just hardcode the list.
    # These names must match exactly the Jira account names.
    developer_hours = {
        "Mark Coatsworth": 0,
        "Jaime Frey": 0,
        "John (TJ) Knoeller": 0,
        "Todd L Miller": 0,
        "Zach Miller": 0,
        "Jason Patton": 0,
        "Todd Tannenbaum": 0,
        "Greg Thain": 0,
        "Tim Theisen": 0
    }

    # Iterate over all Improvement issues
    issues = jira.search_issues("project = HTCONDOR AND type = Improvement", maxResults=False)
    for issue in issues:
        issue_worklog = jira.worklogs(issue)
        display_issue_header = True
        for work_item in issue_worklog:
            work_datetime = work_item.started[0:work_item.started.rfind("-")]
            work_datetime = datetime.strptime(work_datetime, "%Y-%m-%dT%H:%M:%S.%f")
            #print(f"\tWork logged: Author = {work_item.author.displayName}, Time spent = {round(work_item.timeSpentSeconds/3600, 2)} hr(s), Started = {work_item.started}")  # Debug
            if work_datetime > start_datetime and work_datetime < end_datetime:
                if display_issue_header is True and detailed is True:
                    print(f"{issue.key}: {issue.fields.summary}")
                    display_issue_header = False # Only display the issue header once
                if detailed is True:
                    started = work_item.started[0:work_item.started.rfind("-")]
                    started_datetime = datetime.strptime(started, "%Y-%m-%dT%H:%M:%S.%f")
                    print(f"\t{work_item.author.displayName} worklog, Time spent: {round(work_item.timeSpentSeconds/3600, 2)} hr(s), Started: {started_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                try:
                    developer_hours[work_item.author.displayName] += round(work_item.timeSpentSeconds/3600, 2)
                except:
                    print(f"\t\tError: could not add work logged for f{work_item.author.displayName}")

        issue_subtasks = issue.fields.subtasks
        for subtask in issue_subtasks:
            subtask_worklog = jira.worklogs(subtask)
            display_subtask_header = True
            for work_item in subtask_worklog:
                work_datetime = work_item.started[0:work_item.started.rfind("-")]
                work_datetime = datetime.strptime(work_datetime, "%Y-%m-%dT%H:%M:%S.%f")
                #print(f"\t\tWork logged: Author = {work_item.author.displayName}, Time spent = {round(work_item.timeSpentSeconds/3600, 2)} hr(s), Started = {work_item.started}")  # Debug
                if work_datetime > start_datetime and work_datetime < end_datetime:
                    if display_subtask_header is True and detailed is True:
                        print(f"\tSubtask {subtask.key}: {subtask.fields.summary}")
                        display_subtask_header = False
                    if detailed is True:
                        started = work_item.started[0:work_item.started.rfind("-")]
                        started_datetime = datetime.strptime(started, "%Y-%m-%dT%H:%M:%S.%f")
                        print(f"\t\t{work_item.author.displayName} worklog, Time spent: {round(work_item.timeSpentSeconds/3600, 2)} hr(s), Started: {started_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                    try:
                        developer_hours[work_item.author.displayName] += round(work_item.timeSpentSeconds/3600, 2)
                    except:
                        print(f"\t\tError: could not add work logged for f{work_item.author.displayName}")

    # All done! Output results
    total_hours_logged = 0
    print(f"\nBetween {start_datetime.strftime('%Y-%m-%d')} and {end_datetime.strftime('%Y-%m-%d')}:\n")
    for developer in developer_hours:
        print(f"{developer} logged {round(developer_hours[developer], 2)} hours")
        total_hours_logged += developer_hours[developer]

    total_developer_hours_worked = len(developer_hours)*(((end_datetime - start_datetime).days + 1) * 8) - hours_off
    print(f"\nTotal hours logged to HTCONDOR Improvement issues: {total_hours_logged}")
    print(f"Total developer hours worked (assuming 8-hour work days, minus time off): {total_developer_hours_worked}")
    print(f"Percent effort logged to Improvement issues: {round(total_hours_logged*100/total_developer_hours_worked, 2)}%\n")


if __name__ == "__main__":
    main()