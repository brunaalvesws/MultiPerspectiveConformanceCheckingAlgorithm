#!/usr/bin/env python3
"""
Script para substituir ocorrências de string em arquivo XES.
Encontra 2054 ocorrências e substitui "value="r"" por "value="u""
"""

import os

# Caminho do arquivo
file_path = "ExperimentLogsAndModels/SyntheticDataAccessLogThousandCasesAccessViolations10.xes"

# Strings para buscar e substituir
search_string = '''value="Gestao" />
			<string key="concept:operation" value="r"'''

replace_string = '''value="Gestao" />
			<string key="concept:operation" value="u"'''

print(f"Processando arquivo: {file_path}")
print(f"Buscando por: {repr(search_string)}")
print(f"Substituindo por: {repr(replace_string)}")

try:
    # Ler o arquivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Contar ocorrências
    count = content.count(search_string)
    print(f"\nOcorrências encontradas: {count}")
    
    if count > 0:
        # Fazer a substituição apenas das 2054 primeiras ocorrências
        max_substitutions = 5
        new_content = content.replace(search_string, replace_string, max_substitutions)
        
        # Salvar o arquivo modificado
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✓ Arquivo modificado com sucesso!")
        print(f"✓ {max_substitutions} substituições realizadas (de {count} encontradas)")
    else:
        print("✗ Nenhuma ocorrência encontrada")
        print("\nVerificando se a string existe (com variações)...")
        if 'value="Gestao"' in content:
            print("  - Encontrada: value=\"Gestao\"")
        if 'concept:operation' in content:
            print("  - Encontrada: concept:operation")
        if 'value="r"' in content:
            print("  - Encontrada: value=\"r\"")
            
except FileNotFoundError:
    print(f"✗ Erro: Arquivo não encontrado em {file_path}")
except Exception as e:
    print(f"✗ Erro ao processar arquivo: {e}")
