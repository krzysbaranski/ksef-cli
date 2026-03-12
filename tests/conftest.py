"""Pytest configuration and fixtures for KSeF CLI tests"""

from datetime import date

import pytest

from ksef_cli.models import Adres, DodatkowyOpis, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury


@pytest.fixture
def adres_pl():
    """Sample Polish address"""
    return Adres(kod_kraju="PL", adres_l1="ul. Testowa 123", adres_l2="00-001 Warszawa")


@pytest.fixture
def adres_pl_simple():
    """Simple Polish address without second line"""
    return Adres(kod_kraju="PL", adres_l1="ul. Prosta 1")


@pytest.fixture
def sprzedawca(adres_pl):
    """Sample seller entity"""
    return Podmiot(nip="5260250274", nazwa="Moja Firma Sp. z o.o.", adres=adres_pl)


@pytest.fixture
def nabywca(adres_pl_simple):
    """Sample buyer entity"""
    return Podmiot(nip="9492107026", nazwa="Klient Sp. z o.o.", adres=adres_pl_simple)


@pytest.fixture
def pozycja_faktury():
    """Single invoice line item"""
    return PozycjaFaktury(
        nr=1,
        nazwa="Usługa testowa",
        jm="szt",
        ilosc=1.0,
        cena_netto=100.00,
        wartosc_netto=100.00,
        stawka_vat=23,
    )


@pytest.fixture
def pozycje_faktury():
    """Multiple invoice line items"""
    return [
        PozycjaFaktury(
            nr=1,
            nazwa="Usługa programistyczna",
            jm="godz",
            ilosc=10.0,
            cena_netto=150.00,
            wartosc_netto=1500.00,
            stawka_vat=23,
        ),
        PozycjaFaktury(
            nr=2,
            nazwa="Konsultacje IT",
            jm="godz",
            ilosc=5.0,
            cena_netto=200.00,
            wartosc_netto=1000.00,
            stawka_vat=23,
        ),
    ]


@pytest.fixture
def faktura(pozycje_faktury):
    """Sample invoice"""
    return Faktura(
        numer="FV/2026/01/001",
        data_wystawienia=date(2026, 2, 1),
        miejsce_wystawienia="Warszawa",
        data_sprzedazy=date(2026, 2, 1),
        waluta="PLN",
        pozycje=pozycje_faktury,
        forma_platnosci="6",
    )


@pytest.fixture
def faktura_ksef(sprzedawca, nabywca, faktura):
    """Complete KSeF invoice"""
    return FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)


@pytest.fixture
def dodatkowy_opis():
    """Sample additional description"""
    return DodatkowyOpis(klucz="Uwagi", wartosc="Termin płatności: 14 dni")


@pytest.fixture
def sample_invoice_json():
    """Sample invoice JSON data"""
    return {
        "sprzedawca": {
            "nip": "5260250274",
            "nazwa": "Moja Firma Sp. z o.o.",
            "adres": {
                "kod_kraju": "PL",
                "adres_l1": "ul. Przykładowa 123",
                "adres_l2": "00-001 Warszawa",
            },
        },
        "nabywca": {
            "nip": "9492107026",
            "nazwa": "Klient Sp. z o.o.",
            "adres": {"kod_kraju": "PL", "adres_l1": "ul. Testowa 456"},
        },
        "faktura": {
            "numer": "FV/2026/01/001",
            "data_wystawienia": "2026-02-01",
            "miejsce_wystawienia": "Warszawa",
            "data_sprzedazy": "2026-02-01",
            "waluta": "PLN",
            "pozycje": [
                {
                    "nr": 1,
                    "nazwa": "Usługa testowa",
                    "jm": "szt",
                    "ilosc": 1,
                    "cena_netto": 100.00,
                    "wartosc_netto": 100.00,
                    "stawka_vat": 23,
                }
            ],
            "forma_platnosci": "6",
        },
    }
