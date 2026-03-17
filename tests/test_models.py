"""Tests for Pydantic models in ksef_cli.models"""

from datetime import date

import pytest
from pydantic import ValidationError

from ksef_cli.models import Adres, DodatkowyOpis, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury


class TestAdres:
    """Tests for Adres model"""

    def test_adres_valid(self):
        """Test creating valid address"""
        adres = Adres(kod_kraju="PL", adres_l1="ul. Testowa 123", adres_l2="00-001 Warszawa")
        assert adres.kod_kraju == "PL"
        assert adres.adres_l1 == "ul. Testowa 123"
        assert adres.adres_l2 == "00-001 Warszawa"

    def test_adres_default_kod_kraju(self):
        """Test default country code"""
        adres = Adres(adres_l1="ul. Testowa 123")
        assert adres.kod_kraju == "PL"

    def test_adres_optional_l2(self):
        """Test optional second address line"""
        adres = Adres(kod_kraju="PL", adres_l1="ul. Testowa 123")
        assert adres.adres_l2 is None

    def test_adres_kod_kraju_max_length(self):
        """Test country code max length validation"""
        with pytest.raises(ValidationError):
            Adres(kod_kraju="POL", adres_l1="ul. Testowa 123")


class TestPodmiot:
    """Tests for Podmiot model"""

    def test_podmiot_valid(self, adres_pl):
        """Test creating valid entity"""
        podmiot = Podmiot(nip="5260250274", nazwa="Moja Firma", adres=adres_pl)
        assert podmiot.nip == "5260250274"
        assert podmiot.nazwa == "Moja Firma"
        assert podmiot.adres == adres_pl

    def test_podmiot_nip_too_short(self, adres_pl):
        """Test NIP validation - too short"""
        with pytest.raises(ValidationError):
            Podmiot(nip="123", nazwa="Test", adres=adres_pl)

    def test_podmiot_nip_too_long(self, adres_pl):
        """Test NIP validation - too long"""
        with pytest.raises(ValidationError):
            Podmiot(nip="12345678901", nazwa="Test", adres=adres_pl)

    def test_podmiot_nip_exactly_10_digits(self, adres_pl):
        """Test NIP with exactly 10 digits"""
        podmiot = Podmiot(nip="1234567890", nazwa="Test", adres=adres_pl)
        assert podmiot.nip == "1234567890"


class TestPozycjaFaktury:
    """Tests for PozycjaFaktury model"""

    def test_pozycja_valid(self):
        """Test creating valid invoice line"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=2.0,
            cena_netto=100.00,
            wartosc_netto=200.00,
            stawka_vat=23,
        )
        assert pozycja.nr == 1
        assert pozycja.wartosc_netto == 200.00

    def test_oblicz_vat_23_percent(self):
        """Test VAT calculation with 23% rate"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23,
        )
        vat = pozycja.oblicz_vat()
        assert vat == 23.00

    def test_oblicz_vat_8_percent(self):
        """Test VAT calculation with 8% rate"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Książka",
            jm="szt",
            ilosc=1.0,
            cena_netto=50.00,
            wartosc_netto=50.00,
            stawka_vat=8,
        )
        vat = pozycja.oblicz_vat()
        assert vat == 4.00

    def test_oblicz_vat_5_percent(self):
        """Test VAT calculation with 5% rate"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Żywność",
            jm="kg",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=5,
        )
        vat = pozycja.oblicz_vat()
        assert vat == 5.00

    def test_oblicz_vat_0_percent(self):
        """Test VAT calculation with 0% rate"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Export",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=0,
        )
        vat = pozycja.oblicz_vat()
        assert vat == 0.00

    def test_oblicz_vat_rounding(self):
        """Test VAT calculation rounding"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=3.0,
            cena_netto=33.33,
            wartosc_netto=99.99,
            stawka_vat=23,
        )
        vat = pozycja.oblicz_vat()
        assert vat == 23.00  # 99.99 * 0.23 = 22.9977 -> rounds to 23.00

    def test_oblicz_vat_cached(self):
        """Test that VAT calculation is cached"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23,
            kwota_vat=25.00,  # Pre-set value
        )
        vat = pozycja.oblicz_vat()
        assert vat == 25.00  # Should return pre-set value


class TestDodatkowyOpis:
    """Tests for DodatkowyOpis model"""

    def test_dodatkowy_opis_valid(self):
        """Test creating valid additional description"""
        opis = DodatkowyOpis(klucz="Uwagi", wartosc="Termin płatności: 14 dni")
        assert opis.klucz == "Uwagi"
        assert opis.wartosc == "Termin płatności: 14 dni"


class TestFaktura:
    """Tests for Faktura model"""

    def test_faktura_valid(self, pozycje_faktury):
        """Test creating valid invoice"""
        faktura = Faktura(
            numer="FV/2026/01/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            waluta="PLN",
            pozycje=pozycje_faktury,
        )
        assert faktura.numer == "FV/2026/01/001"
        assert len(faktura.pozycje) == 2

    def test_faktura_default_waluta(self, pozycja_faktury):
        """Test default currency"""
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja_faktury],
        )
        assert faktura.waluta == "PLN"

    def test_faktura_default_forma_platnosci(self, pozycja_faktury):
        """Test default payment form"""
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja_faktury],
        )
        assert faktura.forma_platnosci == "6"

    def test_faktura_stopka_faktury_default_none(self, pozycja_faktury):
        """Test that stopka_faktury defaults to None"""
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja_faktury],
        )
        assert faktura.stopka_faktury is None

    def test_faktura_stopka_faktury_set(self, pozycja_faktury):
        """Test setting stopka_faktury"""
        tekst = "ZESTAWIENIE:\nData\n2026-01-01"
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja_faktury],
            stopka_faktury=tekst,
        )
        assert faktura.stopka_faktury == tekst

    def test_oblicz_sumy_single_item(self):
        """Test sum calculation with single item"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23,
        )
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja],
        )
        sumy = faktura.oblicz_sumy()
        assert sumy["netto"] == 100.00
        assert sumy["vat"] == 23.00
        assert sumy["brutto"] == 123.00

    def test_oblicz_sumy_multiple_items(self, pozycje_faktury):
        """Test sum calculation with multiple items"""
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=pozycje_faktury,
        )
        sumy = faktura.oblicz_sumy()
        assert sumy["netto"] == 2500.00  # 1500 + 1000
        assert sumy["vat"] == 575.00  # 345 + 230
        assert sumy["brutto"] == 3075.00  # 2500 + 575

    def test_oblicz_sumy_different_vat_rates(self):
        """Test sum calculation with different VAT rates"""
        pozycje = [
            PozycjaFaktury(
                nr=1,
                nazwa="Usługa 23%",
                jm="szt",
                ilosc=1.0,
                cena_netto=100.00,
                wartosc_netto=100.00,
                stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=2,
                nazwa="Książka 8%",
                jm="szt",
                ilosc=1.0,
                cena_netto=50.00,
                wartosc_netto=50.00,
                stawka_vat=8,
            ),
        ]
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=pozycje,
        )
        sumy = faktura.oblicz_sumy()
        assert sumy["netto"] == 150.00
        assert sumy["vat"] == 27.00  # 23 + 4
        assert sumy["brutto"] == 177.00

    def test_faktura_with_dodatkowe_opisy(self, pozycja_faktury):
        """Test invoice with additional descriptions"""
        opisy = [
            DodatkowyOpis(klucz="Uwagi", wartosc="Test"),
            DodatkowyOpis(klucz="Termin", wartosc="14 dni"),
        ]
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja_faktury],
            dodatkowe_opisy=opisy,
        )
        assert len(faktura.dodatkowe_opisy) == 2

    def test_faktura_waluta_max_length(self, pozycja_faktury):
        """Test currency code max length validation"""
        with pytest.raises(ValidationError):
            Faktura(
                numer="FV/001",
                data_wystawienia=date(2026, 2, 1),
                miejsce_wystawienia="Warszawa",
                data_sprzedazy=date(2026, 2, 1),
                waluta="EURO",  # Too long
                pozycje=[pozycja_faktury],
            )


class TestFakturaKSeF:
    """Tests for FakturaKSeF model"""

    def test_faktura_ksef_valid(self, sprzedawca, nabywca, faktura):
        """Test creating valid KSeF invoice"""
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)
        assert faktura_ksef.sprzedawca == sprzedawca
        assert faktura_ksef.nabywca == nabywca
        assert faktura_ksef.faktura == faktura

    def test_faktura_ksef_default_prefiks(self, sprzedawca, nabywca, faktura):
        """Test default taxpayer prefix"""
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)
        assert faktura_ksef.prefiks_podatnika == "PL"

    def test_faktura_ksef_default_system_info(self, sprzedawca, nabywca, faktura):
        """Test default system info"""
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)
        assert (
            faktura_ksef.system_info
            == "KSeF CLI Generator https://github.com/krzysbaranski/ksef-cli"
        )

    def test_faktura_ksef_custom_values(self, sprzedawca, nabywca, faktura):
        """Test KSeF invoice with custom values"""
        faktura_ksef = FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura,
            prefiks_podatnika="DE",
            system_info="Custom System",
        )
        assert faktura_ksef.prefiks_podatnika == "DE"
        assert faktura_ksef.system_info == "Custom System"
