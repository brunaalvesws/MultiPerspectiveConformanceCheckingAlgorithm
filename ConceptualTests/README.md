# Testes automatizados

Testes automatizados (pytest) para validar que o algoritmo de análise de
conformidade multi-perspectiva identifica corretamente as violações.

## Estrutura

- `conftest.py` — adiciona `Algorithm/` ao `sys.path`, define os caminhos
  dos arquivos de entrada e cria fixtures de sessão que executam o algoritmo
  uma única vez por combinação de entradas.
- `test_with_violations.py` — usa os arquivos de
  `Algorithm/DevelopmentFiles/` (com violações já mapeadas em
  `violationTestMapping.txt`) e verifica que cada violação esperada é
  detectada e classificada na categoria correta.
- `test_without_violations.py` — usa os logs sintéticos sem erros em
  `ModelosLogsTeste/` (`SyntheticProcessLogTenCasesNoErrors.xes` e
  `SyntheticDataAccessLogTenCasesNoErrorsAcesso.xes`) e verifica que o
  relatório não contém nenhuma violação.

## Como executar

A partir da raiz do repositório, com as dependências do algoritmo
instaladas (ver `Algorithm/requirements.txt`):

```powershell
pip install pytest
pip install -r Algorithm/requirements.txt
pytest Test
```

Os arquivos de relatório que o algoritmo gera como efeito colateral
(`report*Acesso.txt`) são gravados em um diretório temporário criado pelo
pytest, então nada é poluído no workspace.

## Adicionando novos casos de teste

Para testar com novos arquivos de entrada, basta adicionar uma nova
fixture em `conftest.py` reaproveitando `_run_algorithm` e escrever um
novo módulo `test_*.py` com asserções sobre o `report` retornado.
