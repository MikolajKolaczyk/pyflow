# PyFlow — model workflowu i planowanie grafu

## Opis projektu
PyFlow to biblioteka w Pythonie do definiowania zadań, zależności i planowania kolejności wykonania.

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
- Model Task i Workflow.
- Wykrywanie duplikatów i brakujących zależności.
- Wykrywanie cykli w grafie DAG.
- Sortowanie topologiczne.
- Wyznaczanie warstw wykonania.

## Algorytm i złożoność
Wykorzystywany jest algorytm Kahna. Przy wielu dostępnych zadaniach wybierana jest alfabetycznie pierwsza nazwa.
Złożoność czasowa tej implementacji wynosi O((V + E) log V), a pamięciowa O(V + E), gdzie V to liczba zadań, a E to liczba zależności.

## Struktura projektu
- src/pyflow/models.py — modele zadań i workflow.
- src/pyflow/graph.py — algorytmy grafowe.
- tests/test_models.py — testy modeli.
- tests/test_graph.py — testy grafu.
- pyproject.toml — konfiguracja projektu.
