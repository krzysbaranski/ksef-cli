# KSeF CLI - Generator Faktur

[![CI/CD Pipeline](https://github.com/krzysbaranski/ksef-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/krzysbaranski/ksef-cli/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Aplikacja CLI do generacji faktur w formacie KSeF (Krajowy System e-Faktur) zgodnie ze schematem FA (3) wersja 1-0E.

## Instalacja

```bash
pip install -r requirements.txt
pip install -e .
```

## Użycie

### Generowanie faktury z pliku JSON

```bash
ksef-cli generate -i invoice_data.json -o faktura.xml
```

### Generowanie faktury interaktywnie

```bash
ksef-cli interactive
```

### Walidacja faktury

```bash
ksef-cli validate -f faktura.xml
```

### Wizualizacja faktury XML do PDF

Generowanie wizualizacji PDF z pliku XML faktury KSeF:

```bash
ksef-cli visualize -i faktura.xml -o faktura.pdf
```

Można również połączyć generowanie XML i PDF:

```bash
# Wygeneruj XML
ksef-cli generate -i invoice_data.json -o faktura.xml

# Wygeneruj PDF z XML
ksef-cli visualize -i faktura.xml -o faktura.pdf
```

## Format danych wejściowych (JSON)

```json
{
  "sprzedawca": {
    "nip": "1132347267",
    "nazwa": "test 1",
    "adres": {
      "kod_kraju": "PL",
      "adres_l1": "adres 1",
      "adres_l2": "test"
    }
  },
  "nabywca": {
    "nip": "9492107026",
    "nazwa": "X-Kom test ksef",
    "adres": {
      "kod_kraju": "PL",
      "adres_l1": "test 1ksef"
    }
  },
  "faktura": {
    "numer": "a123",
    "data_wystawienia": "2026-01-30",
    "miejsce_wystawienia": "Warszawa",
    "data_sprzedazy": "2026-01-31",
    "waluta": "PLN",
    "pozycje": [
      {
        "nr": 1,
        "nazwa": "Usasdf",
        "jm": "h",
        "ilosc": 1,
        "cena_netto": 100.00,
        "wartosc_netto": 100.00,
        "stawka_vat": 23
      }
    ],
    "forma_platnosci": "6"
  }
}
```

## Przykłady

Zobacz `examples/example_invoice.json` dla pełnego przykładu.

## Rozwój

### Instalacja dla deweloperów

```bash
# Sklonuj repozytorium
git clone https://github.com/krzysbaranski/ksef-cli.git
cd ksef-cli

# Stwórz wirtualne środowisko
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Zainstaluj zależności deweloperskie
pip install -r requirements-dev.txt
pip install -e .
```

### Uruchamianie testów

```bash
# Uruchom wszystkie testy
pytest

# Uruchom testy z pokryciem kodu
pytest --cov=ksef_cli --cov-report=term-missing

# Uruchom konkretny test
pytest tests/test_models.py
```

### Sprawdzanie jakości kodu

```bash
# Formatowanie kodu
black ksef_cli/ tests/

# Sortowanie importów
isort ksef_cli/ tests/

# Linting
flake8 ksef_cli/ tests/

# Type checking
mypy ksef_cli/ --ignore-missing-imports

# Security scanning
bandit -r ksef_cli/
```

### Standardy kodu

- **Python**: 3.14+
- **Formatowanie**: Black (line length: 100)
- **Linting**: Flake8
- **Type hints**: Wymagane dla wszystkich funkcji publicznych
- **Pokrycie testami**: Minimum 80%
- **Dokumentacja**: Docstringi dla wszystkich klas i funkcji publicznych

## Kontrybuowanie

Zapraszamy do współtworzenia projektu! Zobacz [CONTRIBUTING.md](CONTRIBUTING.md) dla szczegółowych informacji.

## Licencja

MIT License - zobacz plik LICENSE dla szczegółów.

## CI/CD

Projekt używa GitHub Actions do automatycznego:
- Testowania na Python 3.14
- Sprawdzania jakości kodu (Black, Flake8, isort, mypy)
- Skanowania bezpieczeństwa (Bandit, Safety)
- Weryfikacji pokrycia kodu (minimum 80%)

Status pipeline'u można sprawdzić w zakładce [Actions](https://github.com/krzysbaranski/ksef-cli/actions).
```