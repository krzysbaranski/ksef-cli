"""Tests for interactive template functionality."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ksef_cli.interactive_template import InteractiveTemplate, _validate_date, _validate_nip, _validate_number
from ksef_cli.models import (
    Adres,
    Faktura,
    FakturaKSeF,
    Podmiot,
    PozycjaFaktury,
)


def _q(value):
    """Helper: return a mock questionary prompt whose .ask() returns value."""
    m = MagicMock()
    m.ask.return_value = value
    return m


@pytest.fixture
def sample_invoice():
    """Create a sample invoice for testing."""
    return FakturaKSeF(
        sprzedawca=Podmiot(
            nip="5260250274",
            nazwa="Test Sprzedawca",
            adres=Adres(
                kod_kraju="PL",
                adres_l1="ul. Testowa 1",
                adres_l2="Warszawa",
            ),
        ),
        nabywca=Podmiot(
            nip="9492107026",
            nazwa="Test Nabywca",
            adres=Adres(
                kod_kraju="PL",
                adres_l1="ul. Klienta 2",
            ),
        ),
        faktura=Faktura(
            numer="FV/001/2026",
            data_wystawienia=date(2026, 1, 15),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 1, 15),
            waluta="PLN",
            pozycje=[
                PozycjaFaktury(
                    nr=1,
                    nazwa="Usługa konsultacji",
                    jm="godz",
                    ilosc=8.0,
                    cena_netto=100.0,
                    wartosc_netto=800.0,
                    stawka_vat=23,
                ),
            ],
            stopka_faktury="Dziękujemy za współpracę!",
        ),
    )


class TestValidators:
    def test_validate_date_valid(self):
        assert _validate_date("2026-01-15") is True

    def test_validate_date_invalid(self):
        result = _validate_date("15-01-2026")
        assert result != True  # noqa: E712

    def test_validate_nip_valid(self):
        assert _validate_nip("5260250274") is True

    def test_validate_nip_too_short(self):
        result = _validate_nip("123")
        assert result != True  # noqa: E712

    def test_validate_number_valid(self):
        assert _validate_number("1.5") is True

    def test_validate_number_invalid(self):
        result = _validate_number("abc")
        assert result != True  # noqa: E712


class TestInteractiveTemplate:
    """Tests for InteractiveTemplate class"""

    def test_process_podmiot_keep_defaults(self, sample_invoice):
        """Test keeping seller/buyer data with defaults"""
        template = InteractiveTemplate()
        podmiot = sample_invoice.sprzedawca

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", return_value=_q(True)),
        ):
            result = template._process_podmiot("TEST", podmiot)

        assert result.nip == podmiot.nip
        assert result.nazwa == podmiot.nazwa
        assert result.adres.adres_l1 == podmiot.adres.adres_l1

    def test_process_podmiot_edit(self, sample_invoice):
        """Test editing seller/buyer data"""
        template = InteractiveTemplate()
        podmiot = sample_invoice.sprzedawca

        text_values = ["1234567890", "New Name", "New Address", "City"]
        text_iter = iter(text_values)

        def mock_text(*args, **kwargs):
            return _q(next(text_iter))

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", return_value=_q(False)),
            patch("ksef_cli.interactive_template.questionary.text", side_effect=mock_text),
        ):
            result = template._process_podmiot("TEST", podmiot)

        assert result.nip == "1234567890"
        assert result.nazwa == "New Name"
        assert result.adres.adres_l1 == "New Address"
        assert result.adres.adres_l2 == "City"

    def test_process_faktura_header_keep_defaults(self, sample_invoice):
        """Test keeping invoice header with defaults"""
        template = InteractiveTemplate()
        faktura = sample_invoice.faktura

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", return_value=_q(True)),
        ):
            result = template._process_faktura_header(faktura)

        assert result["numer"] == faktura.numer
        assert result["data_wystawienia"] == faktura.data_wystawienia
        assert result["miejsce_wystawienia"] == faktura.miejsce_wystawienia

    def test_process_faktura_header_edit(self, sample_invoice):
        """Test editing invoice header"""
        template = InteractiveTemplate()
        faktura = sample_invoice.faktura

        text_values = ["FV/002/2026", "2026-02-15", "Gdańsk", "2026-02-15", "EUR"]
        text_iter = iter(text_values)

        def mock_text(*args, **kwargs):
            return _q(next(text_iter))

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", return_value=_q(False)),
            patch("ksef_cli.interactive_template.questionary.text", side_effect=mock_text),
        ):
            result = template._process_faktura_header(faktura)

        assert result["numer"] == "FV/002/2026"
        assert result["waluta"] == "EUR"
        assert result["data_wystawienia"] == date(2026, 2, 15)

    def test_show_podmiot_panel(self):
        """Test displaying subject information in panel."""
        template = InteractiveTemplate()
        podmiot = Podmiot(
            nip="5260250274",
            nazwa="Test Company",
            adres=Adres(kod_kraju="PL", adres_l1="ul. Test 1", adres_l2="Warszawa"),
        )

        with patch("ksef_cli.interactive_template.console") as mock_console:
            template._show_podmiot_panel("Test Title", podmiot)
            assert mock_console.print.called

    def test_show_podmiot_legacy(self):
        """Test legacy _show_podmiot still works."""
        template = InteractiveTemplate()
        podmiot = Podmiot(
            nip="5260250274",
            nazwa="Test Company",
            adres=Adres(kod_kraju="PL", adres_l1="ul. Test 1"),
        )

        with patch("ksef_cli.interactive_template.console") as mock_console:
            template._show_podmiot(podmiot)
            assert mock_console.print.called

    def test_show_pozycja_legacy(self):
        """Test legacy _show_pozycja still works."""
        template = InteractiveTemplate()
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Test Item",
            jm="szt",
            ilosc=5.0,
            cena_netto=100.0,
            wartosc_netto=500.0,
            stawka_vat=23,
        )

        with patch("ksef_cli.interactive_template.console") as mock_console:
            template._show_pozycja(pozycja)
            assert mock_console.print.called

    def test_show_pozycje_table(self):
        """Test displaying line items table."""
        template = InteractiveTemplate()
        pozycje = [
            PozycjaFaktury(
                nr=1,
                nazwa="Item 1",
                jm="szt",
                ilosc=2.0,
                cena_netto=50.0,
                wartosc_netto=100.0,
                stawka_vat=23,
            )
        ]

        with patch("ksef_cli.interactive_template.console") as mock_console:
            template._show_pozycje_table(pozycje)
            assert mock_console.print.called

    def test_process_stopka_keep_defaults(self):
        """Test keeping footer with defaults"""
        template = InteractiveTemplate()
        stopka = "Dziękujemy za współpracę!"

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", return_value=_q(True)),
        ):
            result = template._process_stopka(stopka)

        assert result == stopka

    def test_process_stopka_edit(self):
        """Test editing footer"""
        template = InteractiveTemplate()
        stopka = "Old footer"

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", return_value=_q(False)),
            patch(
                "ksef_cli.interactive_template.questionary.text",
                return_value=_q("New footer"),
            ),
        ):
            result = template._process_stopka(stopka)

        assert result == "New footer"

    def test_process_stopka_no_footer_to_add(self):
        """Test adding footer when none exists"""
        template = InteractiveTemplate()

        with (
            patch("ksef_cli.interactive_template.console"),
            patch(
                "ksef_cli.interactive_template.questionary.text",
                return_value=_q("New footer"),
            ),
        ):
            result = template._process_stopka(None)

        assert result == "New footer"

    def test_process_stopka_empty_addition(self):
        """Test when no footer is added"""
        template = InteractiveTemplate()

        with (
            patch("ksef_cli.interactive_template.console"),
            patch(
                "ksef_cli.interactive_template.questionary.text", return_value=_q("")
            ),
        ):
            result = template._process_stopka(None)

        assert result is None

    def test_line_item_numbering(self, sample_invoice):
        """Test that line items are correctly renumbered after keep/delete operations"""
        sample_invoice.faktura.pozycje = [
            PozycjaFaktury(
                nr=1, nazwa="Item 1", jm="szt", ilosc=1.0,
                cena_netto=100.0, wartosc_netto=100.0, stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=2, nazwa="Item 2", jm="szt", ilosc=2.0,
                cena_netto=200.0, wartosc_netto=400.0, stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=3, nazwa="Item 3", jm="szt", ilosc=3.0,
                cena_netto=300.0, wartosc_netto=900.0, stawka_vat=23,
            ),
        ]

        template = InteractiveTemplate()

        # confirm: keep sprzedawca, keep nabywca, keep header, no new items; stopka keep
        confirm_returns = [True, True, True, False, True]
        confirm_iter = iter(confirm_returns)

        def mock_confirm(*args, **kwargs):
            return _q(next(confirm_iter))

        # select: keep item1, delete item2, keep item3
        select_returns = ["k", "u", "k"]
        select_iter = iter(select_returns)

        def mock_select(*args, **kwargs):
            return _q(next(select_iter))

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.confirm", side_effect=mock_confirm),
            patch("ksef_cli.interactive_template.questionary.select", side_effect=mock_select),
        ):
            result = template.process_template(sample_invoice)

        assert len(result.faktura.pozycje) == 2
        assert result.faktura.pozycje[0].nr == 1
        assert result.faktura.pozycje[0].nazwa == "Item 1"
        assert result.faktura.pozycje[1].nr == 2
        assert result.faktura.pozycje[1].nazwa == "Item 3"

    def test_new_pozycja(self):
        """Test creating a new line item."""
        template = InteractiveTemplate()

        text_values = ["Konsultacja", "godz", "4", "150.00", "23"]
        text_iter = iter(text_values)

        def mock_text(*args, **kwargs):
            return _q(next(text_iter))

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.text", side_effect=mock_text),
        ):
            result = template._new_pozycja(1)

        assert result.nr == 1
        assert result.nazwa == "Konsultacja"
        assert result.jm == "godz"
        assert result.ilosc == 4.0
        assert result.cena_netto == 150.0
        assert result.wartosc_netto == 600.0
        assert result.stawka_vat == 23

    def test_edit_pozycja(self):
        """Test editing an existing line item."""
        template = InteractiveTemplate()
        existing = PozycjaFaktury(
            nr=1, nazwa="Old name", jm="szt", ilosc=1.0,
            cena_netto=100.0, wartosc_netto=100.0, stawka_vat=23,
        )

        text_values = ["New name", "kg", "2", "200", "8"]
        text_iter = iter(text_values)

        def mock_text(*args, **kwargs):
            return _q(next(text_iter))

        with (
            patch("ksef_cli.interactive_template.console"),
            patch("ksef_cli.interactive_template.questionary.text", side_effect=mock_text),
        ):
            result = template._edit_pozycja(2, existing)

        assert result.nr == 2
        assert result.nazwa == "New name"
        assert result.ilosc == 2.0
        assert result.cena_netto == 200.0
        assert result.wartosc_netto == 400.0
        assert result.stawka_vat == 8
