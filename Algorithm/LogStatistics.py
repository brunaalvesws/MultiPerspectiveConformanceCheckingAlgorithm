from pm4py.statistics.attributes.log import get as attributes_get

def activities_distribution(log):
    return attributes_get.get_attribute_values(log.get_log(), "concept:name")


def total_number_of_violations(violations):
    total = 0
    
    for pattern, itens in violations.items():
        for item in itens:
            instance = item.get("instance")
            
            if isinstance(instance, str):
                instance = instance.strip()
                if instance:
                    # separa por vírgula
                    total += len([x for x in instance.split(",") if x.strip()])
                else:
                    total += 1
            else:
                total += 1

    return total

def success_rate(num_eventos, violations):
    return (num_eventos - violations) * 100 / num_eventos