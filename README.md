# MultiPerspectiveConformanceCheckingAlgorithm

Multi Perspective Conformance Checking algorithm using Declare4Py 

---

## 📌 Table of Contents

- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## 📖 About

This algorithm is capable of identifying Process flow, Data access and Privacy violations using Declarative Models and Conformance checking

---

## ✨ Features

- Process Flow conformance checking using Declarative Models and Declare4Py
- Data Access conformance checking using Declarative Models and Declare4Py
- Privacy conformance checking using Pandas and Declarative Models with Declare4Py

---

## 🛠 Tech Stack

- Python 3
- Pandas
- Declare4Py/pm4py

---

## ⚙️ Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/brunaalvesws/MultiPerspectiveConformanceCheckingAlgorithm.git
cd MultiPerspectiveConformanceCheckingAlgorithm
cd Algorithm
```

### 2️⃣ Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

Run the main script:

```bash
python MultiConformanceAlgorithm.py
```

You need to have 5 input files for this script to run, you can use the available ones in the folder ExperimentLogsAndModels for each type of violation or in ModelosLogTeste for only one case with all types of violation, just remember to change the name of the files if using other ones.

---

## 📂 Project Structure

```
MultiPerspectiveConformanceCheckingAlgorithm/
│
├── Algorithm/
│   ├── venv/
│   ├── DevelopmentFiles/   # logs and models used in the development process
│   ├── requirements.txt
│   ├── ConformanceChecking.py
│   ├── ConvertLogs.py
│   ├── FormatMapping.py
│   ├── LogStatistics.py
│   ├── MultiConformanceAlgorithm.py
│   ├── ParseFiles.py
│
├── AlgorithmVersions/       # earlier algorithm notebooks and development versions
├── ConceptualTests/         # pytest tests for correctness and rule validation
├── ExperimentAnalysis/      # scripts and outputs for experiment result analysis
├── ExperimentLogsAndModels/ # synthetic logs and Declare models used in experiment
├── ExperimentOfficialData/  # official results of the experiment and script for running
├── InitialModelsLogs/       # initial models and logs used for generating the synthetic ones
├── ModelosLogsTeste/        # test logs and models for validation and demo runs
└── README.md
```

### Experiment and Conceptual Tests

If you want to replicated the experiment for the performance evaluation of this algorithm or execute the automated conceptual tests, read ConceptualTests or ExperimentOfficialData folder's README for more details.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch:

```bash
git checkout -b feature/new-feature
```

3. Commit your changes:

```bash
git commit -m "Add new feature"
```

4. Push to the branch:

```bash
git push origin feature/new-feature
```

5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License.

---

## 👩‍💻 Contact

Bruna Alves  
GitHub: https://github.com/brunaalvesws
Gmail: baws@cin.ufpe.br