# KSeF CLI - Generator Faktur

[![CI/CD Pipeline](https://github.com/krzysbaranski/ksef-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/krzysbaranski/ksef-cli/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Aplikacja CLI do generacji i zarządzania fakturami w formacie KSeF (Krajowy System e-Faktur) zgodnie ze schematem FA (3) wersja 1-0E. Obsługuje tworzenie faktur, pobieranie z API KSeF oraz wizualizację do PDF.

## Instalacja

```bash
pip install -r requirements.txt
pip install -e .
```

## Spis komend

**POBIERANIE Z API KSeF:**
- `list-invoices`    — Pobierz listę faktur z filtrami
- `get-invoice`      — Pobierz konkretną fakturę XML

**GENEROWANIE FAKTUR:**
- `generate`         — Wygeneruj XML z pliku JSON
- `interactive`      — Wygeneruj XML interaktywnie (pytania)

**WALIDACJA I WIZUALIZACJA:**
- `validate`         — Waliduj plik XML KSeF
- `visualize`        — Konwertuj XML na PDF

## Użycie

### Pobieranie listy faktur z KSeF

Pobierz faktury z API KSeF przy użyciu tokenu autoryzacyjnego:

```bash
ksef-cli list-invoices \
  -n 1234567890 \
  -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z"
```

#### Opcje filtrowania

```bash
# Jako nabywca (zamiast sprzedawcy)
ksef-cli list-invoices -n 1234567890 -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --subject-type Subject2

# Filtr po kwocie (brutto)
ksef-cli list-invoices -n 1234567890 -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --amount-type Brutto --amount-from 100 --amount-to 1000

# Filtr po walucie (można podać wiele)
ksef-cli list-invoices -n 1234567890 -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --currency PLN --currency EUR

# Filtr po typie faktury
ksef-cli list-invoices -n 1234567890 -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --invoice-type Vat

# Tylko faktury z załącznikami
ksef-cli list-invoices -n 1234567890 -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --has-attachment

# Zapis do pliku JSON
ksef-cli list-invoices -n 1234567890 -t <token> \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --output faktury.json
```

#### Token KSeF

Token autoryzacyjny generujesz w portalu KSeF:
- **Produkcja**: https://ap.ksef.mf.gov.pl/web/tokens/generate-token
- **Test**: https://api-test.ksef.mf.gov.pl (dla flagi `--test`)

#### Debugowanie

Użyj flagi `--debug` aby zobaczyć szczegóły żądań i odpowiedzi:

```bash
ksef-cli list-invoices -n 1234567890 -t $TOKEN \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --debug
```

### Pobieranie konkretnej faktury z KSeF

Pobierz pełny dokument XML faktury po numerze KSeF:

```bash
ksef-cli get-invoice \
  -n 1234567890 \
  -t <token> \
  -k 123-456-789-10-2026-0000001
```

Zapisz do pliku:

```bash
ksef-cli get-invoice \
  -n 1234567890 \
  -t <token> \
  -k 123-456-789-10-2026-0000001 \
  -o faktura.xml
```

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
    "nip": "5260250274",
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

## Autentykacja KSeF

Komenda `list-invoices` korzysta z **token-based authentication** (API v2 KSeF):

1. Token autoryzacyjny generujesz w portalu KSeF
2. Aplikacja szyfruje token przy użyciu RSA-OAEP (klucz publiczny z API)
3. Wykonuje 6-krokowy proces autentykacji
4. Otrzymuje JWT access token do zapytań o faktury

**Ograniczenia API**:
- 20 żądań na godzinę per token
- Wsparcie dla FA-3 (formularza FA)
- Daty w formacie ISO-8601 z czasem UTC (np. `2026-01-01T00:00:00.000Z`)

**Dokumentacja KSeF**:
- [Dokumentacja API KSeF v2](https://api-test.ksef.mf.gov.pl/docs/v2/index.html)
- [Portal KSeF do generowania tokenów](https://ap.ksef.mf.gov.pl/web/tokens/generate-token)
- [Test environment](https://api-test.ksef.mf.gov.pl)

## Praktyczne workflow'i

### 1. Generowanie faktury, walidacja i wizualizacja

```bash
# 1. Przygotuj dane w pliku JSON
# 2. Wygeneruj XML
ksef-cli generate -i my_invoice.json -o faktura.xml

# 3. Waliduj format
ksef-cli validate -f faktura.xml

# 4. Utwórz PDF do wydruku/wysyłki
ksef-cli visualize -i faktura.xml -o faktura.pdf
```

### 2. Pobieranie faktury z KSeF

```bash
# Pobierz listę faktur z ostatniego miesiąca
ksef-cli list-invoices -n 1234567890 -t $TOKEN \
  --date-from "2026-03-01T00:00:00.000Z" \
  --date-to "2026-03-31T23:59:59.999Z" \
  --output faktury_marzec.json

# Z otrzymanego JSON weź ksefReferenceNumber
# Pobierz konkretną fakturę XML
ksef-cli get-invoice -n 1234567890 -t $TOKEN \
  -k "123-456-789-10-2026-0000001" \
  -o pobrana_faktura.xml

# Wizualizuj pobraną fakturę
ksef-cli visualize -i pobrana_faktura.xml -o pobrana_faktura.pdf
```

### 3. Filtrowanie faktur przed poborem

```bash
# Pobierz tylko faktury VAT powyżej 1000 PLN
ksef-cli list-invoices -n 1234567890 -t $TOKEN \
  --date-from "2026-01-01T00:00:00.000Z" \
  --date-to "2026-12-31T23:59:59.999Z" \
  --subject-type Subject1 \
  --date-type Issue \
  --invoice-type Vat \
  --amount-type Brutto \
  --amount-from 1000 \
  --output high_value_invoices.json
```

### 4. Debugowanie problemów

```bash
# Włącz debug mode dla szczegółowych informacji
ksef-cli get-invoice -n 1234567890 -t $TOKEN \
  -k "123-456-789-10-2026-0000001" \
  --debug

# Debug info pojawia się na stderr (STDERR), 
# dane na stdout (STDOUT), możesz je oddzielić:
ksef-cli get-invoice -n 1234567890 -t $TOKEN \
  -k "123-456-789-10-2026-0000001" \
  --debug \
  -o faktura.xml 2> debug.log
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