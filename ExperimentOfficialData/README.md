# ExperimentOfficialData

This folder contains the official experiment output reports and the
main experiment execution script `runExperiment.py`.

## Purpose

`runExperiment.py` performs the performance evaluation protocol described
in the project documentation:

- a pilot study to estimate runtime variability and sample size
- a full experiment across the defined scenario matrix

## How to run

From the `ExperimentOfficialData/` directory or the repository root:

```bash
python ExperimentOfficialData/runExperiment.py
```

The script supports the following options:

- `--pilot` : run only the pilot study
- `--cases <n>` : run only the scenarios for a specific case size
- `--label <label>` : run only the scenarios for a specific scenario label

Example:

```bash
python ExperimentOfficialData/runExperiment.py --pilot
python ExperimentOfficialData/runExperiment.py --cases 100
python ExperimentOfficialData/runExperiment.py --label Acesso30
```

## Output

Results are written to report files in this folder, with names like:

- `report1SemViolacao.txt`
- `report100Acesso30.txt`
- `report1000Recurso10.txt`

Each line in a report file contains one measured run.

## Notes

- Warm-up runs are discarded before measured data is recorded.
- The pilot study uses the worst-case scenario to estimate sample size.
- Existing report files will be appended if the experiment is resumed.
- After the experiment execution, you can run the python file analyzeResults.py from ExperimentAnalysis folder to run statistical analysis
