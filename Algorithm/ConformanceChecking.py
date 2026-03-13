from FormatMapping import format_violations, format_violations_access, parse_constraint
from Declare4Py.D4PyEventLog import D4PyEventLog
import pm4py
from Declare4Py.ProcessMiningTasks.ConformanceChecking.MPDeclareAnalyzer import MPDeclareAnalyzer
from Declare4Py.ProcessMiningTasks.ConformanceChecking.MPDeclareResultsBrowser import MPDeclareResultsBrowser

def check_process_conformance(process_model, process_log, consider_vacuity):
    '''
    Checks process conformance between the log and the DECLARE model using the Declare4Py library.
    Accepts a process log (EventLog) and a process model (DeclareModel).
    '''

    basic_checker = MPDeclareAnalyzer(log=process_log, declare_model=process_model, consider_vacuity=consider_vacuity, track_violations="concept:instance")
    conf_check_res: MPDeclareResultsBrowser = basic_checker.run()
    violations = format_violations(conf_check_res.get_metric(metric="events_violated"))
    return violations

def check_access_conformance(process_model, log):
    '''
    Checks access conformance between the log and the joint DECLARE model using Declare4Py.
    Accepts a joint access and activity log (EventLog) and a joint process model (DeclareModel).
    '''
    event_log = D4PyEventLog(case_name="case:concept:name", log=log)

    basic_checker = MPDeclareAnalyzer(log=event_log, declare_model=process_model, consider_vacuity=True, track_violations='concept:instance')
    conf_check_res: MPDeclareResultsBrowser = basic_checker.run()
    violations = format_violations_access(conf_check_res.get_metric(metric="events_violated"))
    size = sum(len(trace) for trace in event_log.get_log())
    return violations, size

def check_resource_activities_conformance(process_log, access_log, allowed_activities_set, resource_model, access_violations):
    '''
    Checks conformance between the access log, process log, and the resource model.
    
    Identifies activities that are not in the allowed set (Unexpected Activities) and checks for specific access violations within those contexts.
    
    Accepts a process log (EventLog object), access log (DataFrame), access violations (DataFrame), set of allowed activities and a Resource Model (DataFrame).
    '''

    process_log_df = pm4py.convert_to_dataframe(process_log.get_log())
    process_log_df = process_log_df.sort_values(['case:concept:name', 'concept:instance'])
    processed_process_log = process_log_df[process_log_df["lifecycle:transition"] == "begin"]

    violations = {}
    violations["IllegalTeamAccess"] = []
    violations["IllegalResourceAccess"] = []
    violations["IllegalTeamActivity"] = []
    activity_conformance = {}
    activity_conformance["UnexpectedActivity"] = []
    activity_conformance["UnexpectedDataAccess"] = []
    mandatory_access = access_violations['Mandatory']
    prohibited_access = access_violations['Prohibited']
    optional_access = access_violations['Resource']
    
    optional_data = [(item[0], parse_constraint(item[1])) for item in optional_access]

    for _, row in resource_model.iterrows():
        case_name = row['case:concept:name']
        resources = row['concept:resources'].split(", ")
        activities = processed_process_log[processed_process_log['case:concept:name'] == case_name]
        accesses = access_log[access_log['case:concept:name'] == case_name]

        for _, activity in activities.iterrows():
            unexpected = False
            activity_resource = activity['concept:resource']
            activity_name = activity['concept:name']
            
            if activity_resource not in resources:
                violations["IllegalTeamActivity"].append([activity_name, activity['@@case_index'], activity_resource, activity['concept:instance']])
                
            if activity_name not in allowed_activities_set:
                unexpected = True
                activity_conformance['UnexpectedActivity'].append([activity_name, activity['@@case_index'], activity['concept:instance'], activity_resource])
                
            instance_in_mandatory = [item for item in mandatory_access if activity['concept:instance'] in item[2] and item[0] == activity['@@case_index']]
            activity_access = accesses[accesses['concept:instance']== activity['concept:instance']]
            for _, acc in activity_access.iterrows():
                if unexpected:
                    activity_conformance['UnexpectedDataAccess'].append([acc['concept:name'], acc['concept:operation'], activity['@@case_index'], acc['concept:instance'], acc['concept:resource'], activity_name])

                verified_violations = []
                for violation in instance_in_mandatory:
                    _, tool, op = parse_constraint(violation[1])
                    elements = [tool, op]
                    if acc['concept:name'] in elements and acc['concept:operation'].lower() in elements:
                        verified_violations.append(instance_in_mandatory.index(violation))
                        if 'Precedence' in violation[1]:
                            violation.extend([acc['concept:resource'], activity_resource])
                            access_violations['Resource'].append(violation)
                            access_violations['Mandatory'].remove(violation)
                        else:
                            access_violations['Mandatory'].remove(violation)
                instance_in_mandatory = [i for i in instance_in_mandatory if instance_in_mandatory.index(i) not in verified_violations]
                            
                instance_in_prohibited = [item for item in prohibited_access if activity['concept:instance'] in item[2] and item[0] == activity['@@case_index'] and 'Precedence' in item[1] and acc['concept:name'] in parse_constraint(item[1])[1] and acc['concept:operation'].lower() in parse_constraint(item[1])[2]]
                
                for violation in instance_in_prohibited:
                    if acc['concept:resource'] != activity_resource:
                        violation.extend([acc['concept:resource'], activity_resource])
                        access_violations['Resource'].append(violation)
                        
                optional_indexes = [i for i, t in enumerate(optional_data) if set(t[1]) == set((acc['concept:name'], acc['concept:operation'].lower(), activity_name)) and t[0] == activity['@@case_index']]

                for i in optional_indexes:
                    access_violations['Resource'][i].extend([acc['concept:resource'], activity_resource])
                
                if acc['concept:resource'] not in resources:
                    violations["IllegalTeamAccess"].append([acc['concept:name'], activity_name, activity['@@case_index'], acc['concept:resource'], acc['concept:instance'], acc['concept:operation']])
    return violations, activity_conformance, access_violations