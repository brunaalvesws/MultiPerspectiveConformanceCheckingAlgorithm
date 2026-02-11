from FormatMapping import format_violations
from Declare4Py.D4PyEventLog import D4PyEventLog
import pm4py
from Declare4Py.ProcessMiningTasks.ConformanceChecking.MPDeclareAnalyzer import MPDeclareAnalyzer
from Declare4Py.ProcessMiningTasks.ConformanceChecking.MPDeclareResultsBrowser import MPDeclareResultsBrowser

def check_process_conformance(process_model, process_log):
    '''
    Checks process conformance between the log and the DECLARE model using the Declare4Py library.
    Accepts a process log (EventLog) and a process model (DeclareModel).
    '''

    basic_checker = MPDeclareAnalyzer(log=process_log, declare_model=process_model, consider_vacuity=False, track_violations="concept:instance")
    conf_check_res: MPDeclareResultsBrowser = basic_checker.run()
    violations = format_violations(conf_check_res.get_metric(metric="events_violated"))
    return violations

def check_access_conformance(process_model, log):
    '''
    Checks access conformance between the log and the joint DECLARE model using Declare4Py.
    Accepts a joint access and activity log (EventLog) and a joint process model (DeclareModel).
    '''
    event_log = D4PyEventLog(case_name="case:concept:name", log=log)

    basic_checker = MPDeclareAnalyzer(log=event_log, declare_model=process_model, consider_vacuity=False, track_violations='concept:instance')
    conf_check_res: MPDeclareResultsBrowser = basic_checker.run()
    violations = format_violations(conf_check_res.get_metric(metric="events_violated"))
    size = sum(len(trace) for trace in event_log.get_log())
    return violations, size

def check_resource_conformance(process_log, access_log, resource_model):
    '''
    Checks conformance between the access log, process log, and the resource model.
    Accepts the resource model (DataFrame), process log (EventLog object), and access log (DataFrame).
    '''

    process_log_df = pm4py.convert_to_dataframe(process_log.get_log())
    process_log_df = process_log_df.sort_values(['case:concept:name', 'concept:instance'])
    processed_process_log = process_log_df[process_log_df["lifecycle:transition"] == "begin"]

    violations = {}
    violations["IllegalTeamAccess"] = []
    violations["IllegalResourceAccess"] = []
    violations["IllegalTeamActivity"] = []

    for index, row in resource_model.iterrows():
        case_id = row['case:concept:name']
        resources = row['concept:resources'].split(", ")
        activities = processed_process_log[processed_process_log['case:concept:name'] == case_id]
        accesses = access_log[access_log['case:concept:name'] == case_id]

        for i, activity in activities.iterrows():
            activity_resource = activity['concept:resource']
            if activity_resource not in resources:
                violations["IllegalTeamActivity"].append([activity['concept:name'], case_id, activity_resource, activity['concept:instance']])

            activity_access = accesses[accesses['concept:instance']== activity['concept:instance']]
            for j, acc in activity_access.iterrows():
                if activity_resource != acc['concept:resource']:
                    violations["IllegalResourceAccess"].append([acc['concept:tool'], activity['concept:name'], case_id, acc['concept:resource'], activity_resource, acc['concept:instance']])
                if acc['concept:resource'] not in resources:
                    violations["IllegalTeamAccess"].append([acc['concept:tool'], activity['concept:name'], case_id, acc['concept:resource'], acc['concept:instance']])

    return violations


def check_activity_conformance(process_log, access_log, allowed_activities_set):
    '''
    Identifies activities that are not in the allowed set (Unexpected Activities) and checks for specific access violations within those contexts.
    Accepts a process log (EventLog object), access log (DataFrame), and a set of allowed activities.
    '''

    process_log_df = pm4py.convert_to_dataframe(process_log.get_log())
    processed_process_log = process_log_df[process_log_df["lifecycle:transition"] == "begin"].drop_duplicates(subset=['concept:name'])


    activity_conformance = {}
    activity_conformance["UnexpectedActivity"] = []
    activity_conformance["UnexpectedDataAccess"] = []

    for index, activity in processed_process_log.iterrows():
        activity_name = activity['concept:name']
        if activity_name not in allowed_activities_set:
            case_id = activity['case:concept:name']
            instance = activity['concept:instance']
            activity_resource = activity.get('concept:resource', 'MissingResource')
            accesses = access_log[access_log['case:concept:name'] == case_id]
            activity_accesses = accesses[accesses['concept:instance'] == activity['concept:instance']]
            activity_conformance['UnexpectedActivity'].append([activity_name, case_id, instance, activity_resource])
            for j, acc in activity_accesses.iterrows():
                activity_conformance['UnexpectedDataAccess'].append([acc['concept:tool'], case_id, instance, acc['concept:resource'], activity_name])


    return activity_conformance
            
