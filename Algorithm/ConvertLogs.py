# -*- coding: utf-8 -*-
from Declare4Py.ProcessModels.DeclareModel import DeclareModel
import pm4py
import pandas as pd

'''
 About this implementation:
 The Multi-perspective conformance checking algorithm paper/thesis states about the Between rule, a new DECLARE template
 to enhance the idea of an activity that must occur after another and before a second one, so, between them. 
 A formal definition was given but the rule was not implemented yet, since Declare4Py has no support for ternary rules.
 As future work, is expected that this contribution will be done on Declare4Py or at least use the library as a solid basis.
 Until them, Response and Precedence rules were used together to model the idea of Between. Since this context uses
 activities with begin and complete time, we can be sure that the begin's event of an activity is always happening before the 
 complete's event of the activity, and so we can say that Response[activity(begin), access] and Precendence[access, activity(complete)]
 work for expressing Between's definition.
'''

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
            model += f'NotResponse[{activity}, {access}] |A.lifecycle:transition is begin |same concept:instance AND T.concept:operation is {letter} AND (same concept:resource OR different concept:resource) |\n'
            
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
    
    access_log['concept:operation'] = access_log['concept:operation'].str.lower()

    df_merged = pd.concat([process_log_df, access_log], ignore_index=True)
    
    df_merged = df_merged.sort_values(['case:concept:name', 'concept:instance','time:timestamp'])
    df_merged.to_csv('LogConjuntoTeste.csv')
    return pm4py.convert_to_event_log(df_merged)