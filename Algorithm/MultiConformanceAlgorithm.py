# -*- coding: utf-8 -*-
"""
Passo a passo:
1. Receber os logs e modelos como na v1
2. Converter o log de atividades para o novo formato, trocando a coluna lifecycle por start e end no nome da atividade
3. Converter o log de acesso para o mesmo formato do log de atividades, colocando a operação no nome
4. Adaptar o modelo declare para que todas as operações obrigatórias e proibidas do modelo de acesso virem regras declare

**Mudei o nome da atividade pra não ter traço e tentei usar Precendence e Response pra andar com a coisa, mas travei naquela questão do id da atividade, porque preciso saber de qual atividade é o acesso**

"""

from pathlib import Path
import time
from ConformanceChecking import check_access_conformance, check_process_conformance, check_resource_activities_conformance
from ConvertLogs import convert_logs, convert_model_to_rules
from FormatMapping import non_conformance_patterns_mapping
from ParseFiles import pre_process_data
from LogStatistics import activities_distribution


def MultiperspectiveConformanceAlgorithm(eventPATH='../ModelosLogsTeste/SyntheticProcessLog.xes',
                                         accessPATH='../ModelosLogsTeste/SyntheticDataAccessLog.xes',
                                         resourcePATH='../ModelosLogsTeste/OrganizationalModel.csv',
                                         declarePATH='../ModelosLogsTeste/ProcessModel.decl',
                                         accessmodelPATH='../ModelosLogsTeste/DataAccessRestrictionModel.csv',
                                         consider_vacuity=True, cases=1):
  '''
  The algorithm accepts: a process log, a data access log, a resource model, a process DECLARE model, and a data access model.
  '''
  begin = time.time()
  process_log, access_log, resource_model, process_model, access_model, allowed_activities = pre_process_data(eventPATH, 
                                                                                                              accessPATH, 
                                                                                                              resourcePATH, 
                                                                                                              declarePATH, 
                                                                                                              accessmodelPATH)
  processed_access_model = convert_model_to_rules(access_model, process_model)
  complete_log = convert_logs(process_log, access_log)
  process_conformance,plog_size = check_process_conformance(process_model, process_log, consider_vacuity)
  activities_stats = activities_distribution(process_log)
  access_conformance, alog_size = check_access_conformance(processed_access_model, complete_log)
  resource_conformance, activity_conformance, access_violations = check_resource_activities_conformance(process_log, access_log, allowed_activities, resource_model, access_conformance)
  log_size = plog_size + alog_size
  return non_conformance_patterns_mapping(process_conformance, 
                                          access_violations, 
                                          resource_conformance, 
                                          activity_conformance, 
                                          activities_stats, 
                                          log_size, begin, cases)
for i in range(20):
    MultiperspectiveConformanceAlgorithm('../ModelosLogsTeste/SyntheticProcessLogTenCasesNoErrors.xes',
                                            '../ModelosLogsTeste/SyntheticDataAccessLogTenCasesNoErrorsAcesso.xes',
                                            '../ModelosLogsTeste/OrganizationalModelTenCases.csv',
                                            '../ModelosLogsTeste/ProcessModel.decl',
                                            '../ModelosLogsTeste/DataAccessRestrictionModel.csv', True, 10)
    MultiperspectiveConformanceAlgorithm('../ModelosLogsTeste/SyntheticProcessLogHundredCases.xes',
                                            '../ModelosLogsTeste/SyntheticDataAccessLogHundredCasesAcesso.xes',
                                            '../ModelosLogsTeste/OrganizationalModelHundredCases.csv',
                                            '../ModelosLogsTeste/ProcessModel.decl',
                                            '../ModelosLogsTeste/DataAccessRestrictionModel.csv', True, 100)
    MultiperspectiveConformanceAlgorithm('../ModelosLogsTeste/SyntheticProcessLogThousandCases.xes',
                                            '../ModelosLogsTeste/SyntheticDataAccessLogThousandCasesAcesso.xes',
                                            '../ModelosLogsTeste/OrganizationalModelThousandCases.csv',
                                            '../ModelosLogsTeste/ProcessModel.decl',
                                            '../ModelosLogsTeste/DataAccessRestrictionModel.csv', True, 1000)