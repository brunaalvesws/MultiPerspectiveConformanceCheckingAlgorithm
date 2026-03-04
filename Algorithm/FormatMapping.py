from LogStatistics import total_number_of_violations, success_rate
from collections import defaultdict

import re

def parse_constraint(rule: str):
    pattern = r"\[(.*?),\s*(.*?)\].*?T\.concept:operation\s+is\s+([crudCRUD])"

    match = re.search(pattern, rule)

    if not match:
        raise ValueError(f"Invalid rule: {rule}")

    tool = match.group(1).strip()
    operation = match.group(3).lower()
    activity = match.group(2).strip()

    return activity, tool, operation



def format_violations(df_violations):
    '''
    Formats the violations detected by Declare4Py conformance checking.
    '''
    violations = []
    for index, row in df_violations.iterrows():
        for column in df_violations.columns:
            if row[column] != None:
                violations.append([index, column, list(set([str(n) for n in row[column]]))])
    return violations


def format_violations_access(df_violations):
    '''
    Formats the violations detected by Declare4Py conformance checking for access perspective.
    '''
    violations = {}
    violations['Resource'] = []
    violations['Mandatory'] = []
    violations['Prohibited'] = []

    grouped_columns = defaultdict(list)

    for col in df_violations.columns:
        A,T,O = parse_constraint(col)
        grouped_columns[tuple(sorted([A,T,O]))].append(col)

    optional_resources_rules = {
        chave: cols
        for chave, cols in grouped_columns.items()
        if len(cols) >= 4
    }

    for row_index, row in df_violations.iterrows():

        verified_rules = []

        for columns in optional_resources_rules.values():

            values = row[columns]
            valid_values = values[values.notna()].index.tolist()
            if len(valid_values) >= 4:
                
                lists = [row[col] for col in valid_values[:4]]

                if all(isinstance(l, list) for l in lists):
                    intersection = set(lists[0])

                    for l in lists[1:]:
                        intersection &= set(l)
                        
                    for i in intersection:
                        
                        violations['Resource'].append([
                            row_index,
                            columns[0],
                            i
                        ])
              
            verified_rules.extend(columns) 
            
        for column_name, value in row.items():
            if (value is not None and column_name not in verified_rules):
                if 'Not' in column_name:
                    violations['Prohibited'].append([
                        row_index,
                        column_name,
                        value
                    ])
                else:
                    violations['Mandatory'].append([
                        row_index,
                        column_name,
                        value
                    ])
        
    return violations


def format_inconformances(process_conformance, access_conformance, resource_conformance, activity_conformance):
    '''
    Formats the non-conformances found in each check to print.
    '''
    
    report = ''

    report += 'Process Flow Violations:\n'
    for violation in process_conformance:
        report += f"Trace {violation[0]} violated {violation[1]} at instances {violation[2]}" + '\n'

    report += 'Prohibited Activity Violations:\n'
    for key, violation in activity_conformance.items():

        if key == "UnexpectedActivity":
            for occur in violation:
                report += f'Unexpected activity {occur[0]} in trace {occur[1]} instance {occur[2]} performed by resource {occur[3]}.\n'
        if key == "UnexpectedDataAccess":
            for occur in violation:
                report += f'Unexpected data access during unexpected activity "{occur[4]}" in access to {occur[0]} in trace {occur[1]} instance {occur[2]} performed by resource {occur[3]}.\n'

    report += 'Access Flow Violations:'
    for violation in access_conformance:
        report += f"Trace {violation[0]} violated {violation[1]} at instances {violation[2]}" + '\n'
        
    report += 'Privacy Violations:'
    for key, violation in resource_conformance.items():
        if key == "IllegalTeamActivity":
            for occur in violation:
                report += f'Privacy Violation in activity {occur[0]} in trace {occur[1]} instance {occur[3]}, resource {occur[2]} is not part of the designated team to perform the demand\n'

        if key == "IllegalTeamAccess":
            for occur in violation:
                report += f'Privacy Violation in access to {occur[0]} of activity {occur[1]} in trace {occur[2]} instance {occur[4]}, resource {occur[3]} is not part of the designated team to perform the demand\n'

        if key == "IllegalResourceAccess":
            for occur in violation:
                report += f'Privacy Violation in access to {occur[0]} of activity {occur[1]} in trace {occur[2]} instance {occur[5]}, resource {occur[3]} was not the designated one for the linked activity, but {occur[4]} was\n'

    return report

def non_conformance_patterns_mapping(process_violations, access_violations, resource_violations, unexpected_activities, activities_stats, log_size, duration):
    patterns = {}
    patterns['Prohibited activity'] = [] #1.5, 2.5, 3.5, 4.5, 5.5, 6.5
    patterns['Unexpected activity'] = [] #7.7
    patterns['Illegal activity'] = [] #Any process log event performed by someone outside the designated team
    patterns['Ignored mandatory activity'] = [] #2.2, 4.2, 6.2
    patterns['Prohibited data access'] = [] #5.1, 5.3, 5.5
    patterns['Unexpected data access'] = [] #7.7
    patterns['Illegal data access'] = [] #Any data log access performed by someone outside the team or not assigned to the corresponding activity
    patterns['Ignored mandatory data access'] = [] #2.1, 2.3, 2.5
    
    for act in unexpected_activities['UnexpectedActivity']:
        patterns['Unexpected activity'].append({'name': act[0], 'case_id': act[1], 'instance': act[2], 'resource': act[3]})
        
    for acc in unexpected_activities['UnexpectedDataAccess']:
        patterns['Unexpected data access'].append({'tool': acc[0], 'operation': acc[1], 'case_id': acc[2], 'instance': acc[3], 'resource': acc[4], 'activity': acc[5]})
        
    for act in resource_violations['IllegalTeamActivity']:
        patterns['Illegal activity'].append({'name': act[0], 'case_id': act[1], 'resource': act[2], 'instance': act[3]})
        
    for acc in resource_violations['IllegalTeamAccess']:
        patterns['Illegal data access'].append({'tool': acc[0], 'activity': acc[1], 'case_id': acc[2], 'instance': acc[4], 'resource': acc[3], 'operation': acc[5]})
    
    for violation in access_violations['Resource']:
        activity, tool, operation = parse_constraint(violation[1])
        patterns['Illegal data access'].append({'case_id': violation[0], 'tool': tool, 'activity': activity, 'operation': operation, 'instance': violation[2], 'resource': violation[3], 'designated_resource': violation[4]})
    
    for violation in access_violations['Mandatory']:
        if 'Precedence' in violation[1]:
            activity, tool, operation = parse_constraint(violation[1])
            patterns['Ignored mandatory data access'].append({'case_id': violation[0], 'tool': tool, 'activity': activity, 'operation': operation, 'instance': violation[2]})
    
    for violation in access_violations['Prohibited']:
        if "Precedence" in violation[1]:
            activity, tool, operation = parse_constraint(violation[1])
            patterns['Prohibited data access'].append({'case_id': violation[0], 'tool': tool, 'activity': activity, 'operation': operation, 'instance': violation[2]})
    
    #O Declare4Py não tem implementações das regras Succesion (e suas variantes) e CoExistence (e suas variantes)
    for violation in process_violations:
        if any(regra in violation[1] for regra in ["Precedence", "Absense", "Not Succession", "Not Chain Succession", "Not CoExistence", "Not Response", "Not Responded Existence", "Not Chain Response", "Exclusive Choice", "Exactly"]): 
            # Aqui, a ocorrência em si já é o problema se algo não ocorreu junto
            patterns['Prohibited activity'].append({'case_id': violation[0], 'rule': violation[1], 'instance': ", ".join(violation[2])})
        elif any(regra in violation[1] for regra in ["Existence", "Response", "Init", "End", "Chain Response", "Succession", "CoExistence", "Choice"]):
            # Essas regras criam uma expectativa futura ou passada obrigatória.
            patterns['Ignored mandatory activity'].append({'case_id': violation[0], 'rule': violation[1], 'instance': ", ".join(violation[2])})
        else:
            raise Exception("This rule is not supported")
        
    report = {}
    num_violations = total_number_of_violations(patterns)
    report['overview'] = {
        'successRate': success_rate(log_size, num_violations),
        'averageDuration': duration,
        'violationCount': num_violations
    }
    report['activityDistribution'] = activities_stats
    report['violations'] = patterns
    print(report)    
    return report