
# PyFlow — model workflowu i planowanie grafu

## Opis projektu

PyFlow to biblioteka w Pythonie służąca do definiowania zadań, zarządzania zależnościami, planowania kolejności wykonania oraz synchronicznego i asynchronicznego uruchamiania przepływów danych.

Projekt wykorzystuje skierowany graf acykliczny (DAG). Zadania mogą być wykonywane kolejno lub współbieżnie, z uwzględnieniem zależności, limitu współbieżności, timeoutów i ponawiania prób.

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
- Kopiowanie parametrów z zachowaniem niezależności danych.

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

### Laboratorium 3 — współbieżność, retry i timeout

- Asynchroniczne wykonywanie niezależnych zadań.
- Obsługa funkcji synchronicznych i asynchronicznych.
- Uruchamianie funkcji synchronicznych poza pętlą zdarzeń za pomocą `asyncio.to_thread`.
- Wykonywanie zadań warstwami zgodnie z zależnościami.
- Ograniczanie liczby równocześnie wykonywanych zadań za pomocą semafora.
- Konfigurowalny limit współbieżności.
- Timeout dla pojedynczego zadania.
- Ponawianie nieudanych prób.
- Strategie retry: exponential i fixed.
- Rejestrowanie liczby prób oraz błędów poszczególnych prób.
- Pomijanie zadań zależnych od zadań zakończonych błędem.
- Obsługa anulowania wykonania bez zamieniania anulowania w zwykły błąd zadania.

## Kontrakt funkcji zadania

Każda funkcja zadania przyjmuje dwa argumenty:

```python
function(inputs, params)
```

- `inputs` — mapowanie nazw bezpośrednich zależności na ich wyniki.
- `params` — parametry konfiguracyjne zadania.

Funkcja może być synchroniczna lub asynchroniczna.

## Model zadania

Przykład utworzenia zadania:

```python
from pyflow import Task

task = Task(
    name="download",
    function=my_function,
    dependencies=frozenset(),
    params={},
    retries=3,
    timeout=5.0,
)
```

Parametry:

- `retries` — liczba dodatkowych prób po niepowodzeniu; domyślnie `0`.
- `timeout` — maksymalny czas pojedynczej próby w sekundach; `None` oznacza brak limitu.

## Silnik synchroniczny

Podstawowe API uruchamiające workflow synchronicznie:

```python
from pyflow import run

result = run(workflow)
```

Wynik wykonania udostępnia:

- `result.outputs` — wyniki poszczególnych zadań.
- `result.task_states` — statusy, czasy wykonania i informacje o próbach.
- `result.succeeded` — informację o powodzeniu całego workflow.
- `result.duration` — całkowity czas wykonania.
- `result.errors` — informacje o błędach.

## Silnik asynchroniczny

Workflow można uruchomić asynchronicznie:

```python
import asyncio
from pyflow import async_run

async def main():
    result = await async_run(
        workflow,
        max_concurrency=3,
    )

    print(result.outputs)

asyncio.run(main())
```

Parametry silnika:

- `max_concurrency` — maksymalna liczba równocześnie wykonywanych zadań; domyślnie `5`.
- `base_delay` — podstawowe opóźnienie pomiędzy próbami; domyślnie `0.1` sekundy.
- `retry_policy` — wybrana strategia ponawiania prób.

Zadania należące do tej samej warstwy mogą działać równolegle. Następna warstwa rozpoczyna się dopiero po zakończeniu poprzedniej.

Funkcje synchroniczne są uruchamiane za pomocą `asyncio.to_thread`, dzięki czemu nie blokują pętli zdarzeń.

Anulowanie zadania asynchronicznego propaguje `asyncio.CancelledError` i nie jest traktowane jak zwykły błąd wykonania. Anulowanie oczekiwania na funkcję synchroniczną nie gwarantuje przerwania jej działania w wątku roboczym.

## Strategie ponawiania prób

PyFlow udostępnia klasę `RetryPolicy`.

### Strategia exponential

Opóźnienie rośnie wykładniczo:

```python
from pyflow import RetryPolicy

policy = RetryPolicy("exponential")
```

Wzór:

```text
delay = base_delay * 2**attempt
```

Przykładowo dla `base_delay = 0.1`:

| Próba | Opóźnienie przed kolejną próbą |
|---|---:|
| 1 | 0.1 s |
| 2 | 0.2 s |
| 3 | 0.4 s |

### Strategia fixed

Opóźnienie pozostaje stałe:

```python
policy = RetryPolicy("fixed")
```

Przykładowo dla `base_delay = 0.1` każda kolejna próba jest poprzedzona opóźnieniem `0.1` sekundy.

### Wybór strategii

```python
result = await async_run(
    workflow,
    max_concurrency=3,
    base_delay=0.1,
    retry_policy=RetryPolicy("fixed"),
)
```

Domyślną strategią jest `exponential`.

## Informacje o wykonaniu i próbach

Każde zadanie posiada obiekt `TaskState`, który przechowuje:

- `status` — aktualny lub końcowy status zadania.
- `output` — wynik zadania.
- `started_at` — czas rozpoczęcia.
- `finished_at` — czas zakończenia.
- `duration` — czas wykonania.
- `attempts` — liczba wykonanych prób.
- `error` — końcowy błąd, jeżeli zadanie zakończyło się niepowodzeniem.
- `attempt_errors` — lista błędów z poszczególnych prób.

## Statusy zadań

| Status | Znaczenie |
|---|---|
| PENDING | Zadanie oczekuje na wykonanie |
| RUNNING | Zadanie jest wykonywane |
| SUCCEEDED | Zadanie zakończyło się powodzeniem |
| FAILED | Zadanie zakończyło się błędem |
| SKIPPED | Zadanie zostało pominięte |

## Polityka obsługi błędów

Projekt wykorzystuje politykę kontynuowania niezależnych gałęzi.

Po niepowodzeniu zadanie otrzymuje status `FAILED`. Jeżeli skonfigurowano ponowienia, silnik podejmuje kolejne próby zgodnie z wybraną strategią retry.

Po wyczerpaniu prób zadanie pozostaje w stanie `FAILED`. Zadania zależne od niego otrzymują status `SKIPPED`. Niezależne zadania są nadal wykonywane.

Silnik zgłasza `TaskExecutionError`, który zawiera nazwę zadania, wynik wykonania oraz oryginalny wyjątek jako przyczynę.

Błędy poszczególnych prób są dostępne w `TaskState.attempt_errors`.

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
│   ├── test_demo_workflow.py
│   ├── test_async_execution.py
│   └── test_retry_policy.py
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
