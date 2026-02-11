# -*- coding: utf-8 -*-
from Declare4Py.ProcessModels.DeclareModel import DeclareModel
import pm4py


def check_letters(cell, model, access, activity):
    """Checks which letters (c, r, u, d) are present in the cell, distinguishing between uppercase and lowercase."""

    letters = ['c', 'r', 'u', 'd']

    if activity == 'Tool':
        return model

    cell = str(cell)
    for letter in letters:
        uppercase_present = letter.upper() in cell

        if uppercase_present:
            if f'{access} {letter}\n' not in model:
                model += 'activity ' + f'{access} {letter}\n'
            model += f'Precedence[{access} {letter}, {activity} complete] | |same concept:instance and same concept:resource |\n'
            model += f'Response[{activity} begin, {access} {letter}] | |same concept:instance and same concept:resource |\n'

        if letter not in cell and not uppercase_present:
            if f'{access} {letter}\n' not in model:
                model += 'activity ' + f'{access} {letter}\n'
            model += f'NotPrecedence[{access} {letter}, {activity} complete] | |same concept:instance and same concept:resource |\n'
            model += f'NotResponse[{activity} begin, {access} {letter}] | |same concept:instance and same concept:resource |\n'


    return model

def convert_model_to_rules(access_model, process_model):
    declare_model_activities = process_model.activities

    new_model = ''

    for act in declare_model_activities:
            new_model += 'activity ' + act + ' begin' + '\n'
            new_model += 'activity ' + act + ' complete' +'\n'

    for col in access_model.columns:
        for index, value in access_model[col].items():
            new_model = check_letters(value, new_model, access_model.iloc[index,0], col)

    declare_model = DeclareModel().parse_from_string(new_model)
    return declare_model

def convert_logs(process_log, access_log):
    '''
    Merges process and access logs into a single log format suitable for conformance checking with Declare4Py.
    '''
    process_log_df = pm4py.convert_to_dataframe(process_log.get_log())
    process_log_df = process_log_df.sort_values(['case:concept:name', 'concept:instance'])
    for index, row in process_log_df.iterrows():
        process_log_df.at[index, 'concept:name'] = row['concept:name'] + ' ' + row['lifecycle:transition']
    process_log_df.drop('lifecycle:transition', axis=1, inplace=True)

    for index, row in access_log.iterrows():
        process_log_df.loc[len(process_log_df)] = [(row['concept:tool'] + ' ' + row['concept:operation'].lower()),row['time:timestamp'], row['concept:resource'], row['concept:instance'], len(process_log_df), row['@@case_index'], row['case:concept:name']]
    process_log_df = process_log_df.sort_values(['case:concept:name', 'concept:instance','time:timestamp'])
    return pm4py.convert_to_event_log(process_log_df)