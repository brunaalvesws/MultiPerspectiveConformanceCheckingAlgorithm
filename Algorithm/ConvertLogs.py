# -*- coding: utf-8 -*-
from Declare4Py.ProcessModels.DeclareModel import DeclareModel
import pm4py


def check_letters(cell, model, access, activity):
    """Checks which letters (c, r, u, d) are present in the cell, distinguishing between uppercase and lowercase."""

    letters = ['c', 'r', 'u', 'd']

    if activity == 'Data Objects':
        return model

    cell = str(cell)
    for letter in letters:
        uppercase_present = letter.upper() in cell

        if uppercase_present:
            if f'{access}\n' not in model:
                model += 'activity ' + f'{access}\n'
            model += f'Precedence[{access}, {activity}] |A.lifecycle:transition is complete |same concept:instance and same concept:resource AND T.concept:operation is {letter} |\n'
            model += f'Response[{activity}, {access}] |A.lifecycle:transition is begin |same concept:instance and same concept:resource AND T.concept:operation is {letter} |\n'

        if not uppercase_present and letter not in cell:
            if f'{access}\n' not in model:
                model += 'activity ' + f'{access}\n'
            model += f'NotPrecedence[{access}, {activity}] |A.lifecycle:transition is complete |same concept:instance AND T.concept:operation is {letter} AND (same concept:resource OR different concept:resource) |\n'
            model += f'NotResponse[{activity}, {access}] |A.lifecycle:transition is begin |same concept:instance AND T.concept:operation is {letter} AND (same concept:resource OR different concept:resource)asz\56t |\n'
            
        if not uppercase_present and letter in cell:
            if f'{access}\n' not in model:
                model += 'activity ' + f'{access}\n'
            model += f'Precedence[{access}, {activity}] |A.lifecycle:transition is complete |same concept:instance and same concept:resource AND T.concept:operation is {letter} |\n'
            model += f'Response[{activity}, {access}] |A.lifecycle:transition is begin |same concept:instance and same concept:resource AND T.concept:operation is {letter} |\n'
            model += f'NotPrecedence[{access}, {activity}] |A.lifecycle:transition is complete |same concept:instance AND T.concept:operation is {letter} AND different concept:resource |\n'
            model += f'NotResponse[{activity}, {access}] |A.lifecycle:transition is begin |same concept:instance AND T.concept:operation is {letter} AND different concept:resource |\n'

    return model

def convert_model_to_rules(access_model, process_model):
    declare_model_activities = process_model.activities

    new_model = ''

    for act in declare_model_activities:
            new_model += 'activity ' + act + '\n'

    for col in access_model.columns:
        for index, value in access_model[col].items():
            new_model = check_letters(value, new_model, access_model.iloc[index,0], col)

    declare_model = DeclareModel().parse_from_string(new_model)
    declare_model.to_file('ModeloConjuntoTeste.decl')
    return declare_model

def convert_logs(process_log, access_log):
    '''
    Merges process and access logs into a single log format suitable for conformance checking with Declare4Py.
    '''
    process_log_df = pm4py.convert_to_dataframe(process_log.get_log())
    process_log_df = process_log_df.sort_values(['case:concept:name', 'concept:instance'])
    process_log_df['concept:operation'] = 'A'

    for index, row in access_log.iterrows():
        process_log_df.loc[len(process_log_df)] = [row['concept:tool'],row['lifecycle:transition'], row['time:timestamp'], row['concept:resource'], row['concept:instance'], len(process_log_df), row['@@case_index'], row['case:concept:name'],row['concept:operation'].lower()]
    process_log_df = process_log_df.sort_values(['case:concept:name', 'concept:instance','time:timestamp'])
    process_log_df.to_csv('LogConjuntoTeste.csv')
    return pm4py.convert_to_event_log(process_log_df)