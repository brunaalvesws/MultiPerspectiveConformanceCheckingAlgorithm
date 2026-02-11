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
from ConformanceChecking import check_access_conformance, check_activity_conformance, check_process_conformance, check_resource_conformance
from ConvertLogs import convert_logs, convert_model_to_rules
from FormatMapping import non_conformance_patterns_mapping
from ParseFiles import pre_process_data
from LogStatistics import activities_distribution


def MultiperspectiveConformanceAlgorithm(eventPATH=str(Path(__file__).resolve().parent / 'LogSinteticoProcessoOFICIALv4.xes'),
                                         accessPATH=str(Path(__file__).resolve().parent / 'LogSinteticoAcessoOFICIALv4.xes'),
                                         resourcePATH=str(Path(__file__).resolve().parent / 'ModeloRecursosOFICIALv4.csv'),
                                         declarePATH=str(Path(__file__).resolve().parent / 'Modelo_Log_Sintetico_OFICIAL.decl'),
                                         accessmodelPATH=str(Path(__file__).resolve().parent / 'ModeloAcessoOFICIAL.csv')):
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
  process_conformance = check_process_conformance(process_model, process_log)
  activities_stats = activities_distribution(process_log)
  access_conformance, log_size = check_access_conformance(processed_access_model, complete_log)
  resource_conformance = check_resource_conformance(process_log, access_log, resource_model)
  activity_conformance = check_activity_conformance(process_log, access_log, allowed_activities)
  end = time.time()
  duration = end - begin
  return non_conformance_patterns_mapping(process_conformance, 
                                          access_conformance, 
                                          resource_conformance, 
                                          activity_conformance, 
                                          activities_stats, 
                                          log_size, 
                                          duration)

MultiperspectiveConformanceAlgorithm()