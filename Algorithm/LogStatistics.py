from pm4py.statistics.attributes.log import get as attributes_get

def activities_distribution(log):
    return attributes_get.get_attribute_values(log.get_log(), "concept:name")


def total_number_of_violations(violations):
     return sum(len(lista) for lista in violations.values())
 

def success_rate(num_eventos, violations):
    return (num_eventos - violations) * 100 / num_eventos