"""Tests for interactive template functionality."""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from ksef_cli.interactive_template import InteractiveTemplate
from ksef_cli.models import (
    Adres,
    FakturaKSeF,
    Faktura,
    Podmiot,
    PozycjaFaktury,
)


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


class TestInteractiveTemplate:
    """Tests for InteractiveTemplate class"""

    def test_process_podmiot_keep_defaults(self, sample_invoice):
        """Test keeping seller/buyer data with defaults"""
        template = InteractiveTemplate()
        podmiot = sample_invoice.sprzedawca

        with patch("click.echo"), patch("click.confirm", return_value=True):
            result = template._process_podmiot("TEST", podmiot)

            assert result.nip == podmiot.nip
            assert result.nazwa == podmiot.nazwa
            assert result.adres.adres_l1 == podmiot.adres.adres_l1

    def test_process_podmiot_edit(self, sample_invoice):
        """Test editing seller/buyer data"""
        template = InteractiveTemplate()
        podmiot = sample_invoice.sprzedawca

        with (
            patch("click.echo"),
            patch("click.confirm", return_value=False),
            patch("click.prompt") as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "1234567890",
                "New Name",
                "New Address",
                "City",
            ]

            result = template._process_podmiot("TEST", podmiot)

            assert result.nip == "1234567890"
            assert result.nazwa == "New Name"
            assert result.adres.adres_l1 == "New Address"
            assert result.adres.adres_l2 == "City"

    def test_process_faktura_header_keep_defaults(self, sample_invoice):
        """Test keeping invoice header with defaults"""
        template = InteractiveTemplate()
        faktura = sample_invoice.faktura

        with patch("click.echo"), patch("click.confirm", return_value=True):
            result = template._process_faktura_header(faktura)

            assert result["numer"] == faktura.numer
            assert result["data_wystawienia"] == faktura.data_wystawienia
            assert result["miejsce_wystawienia"] == faktura.miejsce_wystawienia

    def test_process_faktura_header_edit(self, sample_invoice):
        """Test editing invoice header"""
        template = InteractiveTemplate()
        faktura = sample_invoice.faktura

        mock_date = MagicMock()
        mock_date.date.return_value = date(2026, 2, 15)

        with (
            patch("click.echo"),
            patch("click.confirm", return_value=False),
            patch("click.prompt") as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "FV/002/2026",
                mock_date,
                "Gdańsk",
                mock_date,
                "EUR",
            ]

            result = template._process_faktura_header(faktura)

            assert result["numer"] == "FV/002/2026"
            assert result["waluta"] == "EUR"

    def test_show_podmiot(self):
        """Test displaying subject information"""
        template = InteractiveTemplate()
        podmiot = Podmiot(
            nip="5260250274",
            nazwa="Test Company",
            adres=Adres(kod_kraju="PL", adres_l1="ul. Test 1", adres_l2="Warszawa"),
        )

        with patch("click.echo") as mock_echo:
            template._show_podmiot(podmiot)

            assert mock_echo.called
            calls = [str(call) for call in mock_echo.call_args_list]
            output = " ".join(calls)
            assert "5260250274" in output
            assert "Test Company" in output

    def test_show_pozycja(self):
        """Test displaying line item information"""
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

        with patch("click.echo") as mock_echo:
            template._show_pozycja(pozycja)

            assert mock_echo.called
            calls = [str(call) for call in mock_echo.call_args_list]
            output = " ".join(calls)
            assert "Test Item" in output
            assert "500" in output

    def test_process_stopka_keep_defaults(self):
        """Test keeping footer with defaults"""
        template = InteractiveTemplate()
        stopka = "Dziękujemy za współpracę!"

        with patch("click.echo"), patch("click.confirm", return_value=True):
            result = template._process_stopka(stopka)

            assert result == stopka

    def test_process_stopka_edit(self):
        """Test editing footer"""
        template = InteractiveTemplate()
        stopka = "Old footer"

        with (
            patch("click.echo"),
            patch("click.confirm", return_value=False),
            patch.object(template, "_prompt_multiline", return_value="New footer"),
        ):
            result = template._process_stopka(stopka)

            assert result == "New footer"

    def test_process_stopka_no_footer_to_add(self):
        """Test adding footer when none exists"""
        template = InteractiveTemplate()

        with (
            patch("click.echo"),
            patch.object(template, "_prompt_multiline", return_value="New footer"),
        ):
            result = template._process_stopka(None)

            assert result == "New footer"

    def test_process_stopka_empty_addition(self):
        """Test when no footer is added"""
        template = InteractiveTemplate()

        with patch("click.echo"), patch.object(template, "_prompt_multiline", return_value=None):
            result = template._process_stopka(None)

            assert result is None

    def test_show_podmiot(self):
        """Test displaying subject information"""
        template = InteractiveTemplate()
        podmiot = Podmiot(
            nip="5260250274",
            nazwa="Test Company",
            adres=Adres(kod_kraju="PL", adres_l1="ul. Test 1", adres_l2="Warszawa"),
        )

        with patch("click.echo") as mock_echo:
            template._show_podmiot(podmiot)

            # Verify output was called
            assert mock_echo.called
            calls = [str(call) for call in mock_echo.call_args_list]
            output = " ".join(calls)
            assert "5260250274" in output
            assert "Test Company" in output

    def test_show_pozycja(self):
        """Test displaying line item information"""
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

        with patch("click.echo") as mock_echo:
            template._show_pozycja(pozycja)

            # Verify output was called
            assert mock_echo.called
            calls = [str(call) for call in mock_echo.call_args_list]
            output = " ".join(calls)
            assert "Test Item" in output
            assert "500" in output

    def test_prompt_multiline_with_ctrl_d(self):
        """Test multiline prompt ending with Ctrl+D"""
        template = InteractiveTemplate()

        with patch("click.echo"), patch("click.prompt") as mock_prompt:
            # Simulate two lines then Ctrl+D
            def side_effect(*args, **kwargs):
                raise EOFError()

            mock_prompt.side_effect = [
                "Linia 1",
                "Linia 2",
            ] + [
                EOFError()
            ] * 10  # Multiple EOFErrors just in case

            result = template._prompt_multiline("Test prompt")

            # Result should be the lines joined
            assert result == "Linia 1\nLinia 2"

    def test_prompt_multiline_with_empty_line_confirmation(self):
        """Test multiline prompt with empty line confirmation"""
        template = InteractiveTemplate()

        with (
            patch("click.echo"),
            patch("click.prompt") as mock_prompt,
            patch("click.confirm") as mock_confirm,
        ):
            # Two lines, empty line, confirm finish
            mock_prompt.side_effect = ["Linia 1", "Linia 2", ""]
            mock_confirm.return_value = True

            result = template._prompt_multiline("Test prompt")

            assert result == "Linia 1\nLinia 2"

    def test_prompt_multiline_empty_input(self):
        """Test multiline prompt with no input"""
        template = InteractiveTemplate()

        with patch("click.echo"), patch("click.prompt") as mock_prompt:
            # Empty line at start with Ctrl+D
            mock_prompt.side_effect = EOFError()

            result = template._prompt_multiline("Test prompt")

            assert result is None

    def test_line_item_numbering(self, sample_invoice):
        """Test that line items are correctly numbered after keep/delete operations"""
        sample_invoice.faktura.pozycje = [
            PozycjaFaktury(
                nr=1,
                nazwa="Item 1",
                jm="szt",
                ilosc=1.0,
                cena_netto=100.0,
                wartosc_netto=100.0,
                stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=2,
                nazwa="Item 2",
                jm="szt",
                ilosc=2.0,
                cena_netto=200.0,
                wartosc_netto=400.0,
                stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=3,
                nazwa="Item 3",
                jm="szt",
                ilosc=3.0,
                cena_netto=300.0,
                wartosc_netto=900.0,
                stawka_vat=23,
            ),
        ]

        template = InteractiveTemplate()

        with (
            patch("click.echo"),
            patch("click.confirm") as mock_confirm,
            patch("click.prompt") as mock_prompt,
        ):
            confirm_returns = [True, True, True, False, True]
            mock_confirm.side_effect = confirm_returns

            # Keep 1, delete 2, keep 3
            prompt_returns = ["k", "u", "k"]
            mock_prompt.side_effect = prompt_returns

            result = template.process_template(sample_invoice)

            # Verify numbering is 1, 2 (not 1, 3)
            assert len(result.faktura.pozycje) == 2
            assert result.faktura.pozycje[0].nr == 1
            assert result.faktura.pozycje[0].nazwa == "Item 1"
            assert result.faktura.pozycje[1].nr == 2
            assert result.faktura.pozycje[1].nazwa == "Item 3"

    def test_prompt_multiline_with_keyboard_interrupt(self):
        """Test multiline prompt handling Ctrl+C (KeyboardInterrupt)"""
        template = InteractiveTemplate()

        with patch("click.echo"), patch("click.prompt") as mock_prompt:
            # First line succeeds, second raises KeyboardInterrupt
            mock_prompt.side_effect = ["First line", KeyboardInterrupt()]

            result = template._prompt_multiline("Test prompt")

            # Should return None when interrupted
            assert result is None

    def test_prompt_multiline_empty_lines_ignored(self):
        """Test that empty lines at start are skipped"""
        template = InteractiveTemplate()

        with patch("click.echo"), patch("click.prompt") as mock_prompt:
            # Empty line, then content, then finish
            mock_prompt.side_effect = ["", "Content line", ""]

            result = template._prompt_multiline("Test prompt")

            # Should return the content (empty lines at start are ignored)
            assert result == "Content line"
