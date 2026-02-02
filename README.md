# KSeF CLI - Generator Faktur

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
```