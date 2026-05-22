import random

def gerar_dataset(qtd_cases=1000, arquivo_saida="OrganizationalModelTenThousandCases.csv"):
    # possíveis valores
    teams = [f"e{i}" for i in range(1, 10)]        # e1 até e9
    resources = [f"re{i}" for i in range(1, 21)]  # re1 até re20

    with open(arquivo_saida, "w", encoding="utf-8") as f:
        # cabeçalho
        f.write("case:concept:name;concept:team;concept:resources\n")

        for i in range(qtd_cases):
            case_name = f"case_{i}"
            team = random.choice(teams)

            # escolhe quantidade aleatória de recursos (2 a 5)
            qtd_resources = random.randint(2, 5)
            selected_resources = random.sample(resources, qtd_resources)

            # formata como "re1, re2, re3"
            resources_str = ", ".join(selected_resources)

            linha = f"{case_name};{team};{resources_str}\n"
            f.write(linha)

    print(f"Arquivo '{arquivo_saida}' gerado com {qtd_cases} cases.")


# executar
gerar_dataset(10000)