
# PyFlow — model workflowu i planowanie grafu

## Opis projektu

PyFlow to biblioteka w Pythonie do definiowania zadań, zależności, planowania kolejności wykonania oraz synchronicznego uruchamiania przepływów danych.

Projekt umożliwia tworzenie workflowów opartych na skierowanym grafie acyklicznym (DAG).

## Wymagania

- Python 3.11 lub nowszy
- Git
- pytest

## Instalacja

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install pytest
```

## Uruchamianie testów

```powershell
python -m pytest -v
```

## Funkcjonalności

### Laboratorium 1 — model workflowu i planowanie grafu

- Model Task i Workflow.
- Wykrywanie duplikatów i brakujących zależności.
- Wykrywanie cykli w grafie DAG.
- Sortowanie topologiczne.
- Wyznaczanie warstw wykonania.

### Laboratorium 2 — synchroniczny silnik wykonawczy

- Synchroniczne wykonywanie zadań w kolejności topologicznej.
- Przekazywanie wyników bezpośrednich zależności.
- Przekazywanie parametrów do funkcji zadań.
- Rejestrowanie statusów PENDING, RUNNING, SUCCEEDED, FAILED i SKIPPED.
- Zapisywanie wyników i czasów wykonania zadań.
- Obsługa błędów z zachowaniem oryginalnego wyjątku.
- Pomijanie zadań zależnych od zadań zakończonych błędem.
- Kontynuowanie niezależnych gałęzi po błędzie.
- Generowanie raportu JSON.
- Generowanie tekstowego raportu czasu wykonania.

## Kontrakt funkcji zadania

Każda funkcja zadania przyjmuje dwa argumenty:

```python
function(inputs, params)
```

- `inputs` — mapowanie nazw bezpośrednich zależności na ich wyniki.
- `params` — parametry konfiguracyjne zadania.

## Silnik wykonawczy

Podstawowe API uruchamiające workflow:

```python
from pyflow import run

result = run(workflow)
```

Wynik wykonania udostępnia:

- `result.outputs` — wyniki poszczególnych zadań.
- `result.task_states` — statusy i czasy wykonania zadań.
- `result.succeeded` — informację o powodzeniu całego workflow.
- `result.duration` — całkowity czas wykonania.
- `result.errors` — informacje o błędach.

### Statusy zadań

| Status | Znaczenie |
|---|---|
| PENDING | Zadanie oczekuje na wykonanie |
| RUNNING | Zadanie jest wykonywane |
| SUCCEEDED | Zadanie zakończyło się powodzeniem |
| FAILED | Zadanie zakończyło się błędem |
| SKIPPED | Zadanie zostało pominięte |

### Polityka obsługi błędów

Projekt wykorzystuje politykę kontynuowania niezależnych gałęzi.

Po błędzie zadanie otrzymuje status FAILED. Zadania zależne od niego otrzymują status SKIPPED. Niezależne zadania są nadal wykonywane.

Silnik zgłasza TaskExecutionError zawierający nazwę zadania i zachowuje oryginalny wyjątek jako przyczynę.

## Przykład end-to-end — CSV do JSON

Projekt zawiera demonstracyjny workflow realizujący następujące operacje:

1. Odczyt danych z pliku CSV.
2. Czyszczenie i walidacja rekordów.
3. Agregacja danych według kategorii.
4. Wygenerowanie raportu JSON.
5. Zapis tekstowego raportu czasu wykonania.

Uruchomienie przykładu:

```powershell
python .\examples\demo_workflow.py
```

Wyniki są zapisywane w katalogu `examples`:

- `report.json` — raport sprzedaży.
- `execution_report.txt` — czasy wykonania zadań i całego workflow.

## Algorytm i złożoność

Wykorzystywany jest algorytm Kahna. Przy wielu dostępnych zadaniach wybierana jest alfabetycznie pierwsza nazwa.

Złożoność czasowa tej implementacji wynosi O((V + E) log V), a pamięciowa O(V + E), gdzie V to liczba zadań, a E to liczba zależności.

## Struktura projektu

```text
pyflow/
├── src/
│   └── pyflow/
│       ├── __init__.py
│       ├── models.py
│       ├── graph.py
│       └── execution.py
├── tests/
│   ├── test_models.py
│   ├── test_graph.py
│   ├── test_execution.py
│   └── test_demo_workflow.py
├── examples/
│   ├── demo_workflow.py
│   ├── report.json
│   ├── execution_report.txt
│   └── data/
│       └── sales.csv
├── README.md
└── pyproject.toml
```

## Git

Zmiany kolejnych laboratoriów są zapisywane w repozytorium Git i publikowane na GitHub.
