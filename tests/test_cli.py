"""Tests for CLI commands in ksef_cli.cli"""

import json

from click.testing import CliRunner

from ksef_cli.cli import cli


class TestValidateCommand:
    """Tests for validate command"""

    def test_validate_command_valid_xml(self, faktura_ksef, tmp_path):
        """Test validate command with valid XML"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        # Generate XML file
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "valid.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        result = runner.invoke(cli, ["validate", "-f", str(xml_file)])

        assert result.exit_code == 0
        assert "✓ Plik" in result.output
        assert "jest poprawny" in result.output

    def test_validate_command_invalid_xml(self, tmp_path):
        """Test validate command with invalid XML"""
        runner = CliRunner()

        xml_file = tmp_path / "invalid.xml"
        with open(xml_file, "w") as f:
            f.write("< invalid xml >")

        result = runner.invoke(cli, ["validate", "-f", str(xml_file)])

        assert result.exit_code != 0
        assert "zawiera błędy" in result.output or "Błąd walidacji" in result.output

    def test_validate_command_missing_file(self, tmp_path):
        """Test validate command with missing file"""
        runner = CliRunner()

        result = runner.invoke(cli, ["validate", "-f", str(tmp_path / "nonexistent.xml")])

        assert result.exit_code != 0

    def test_validate_command_valid_structure(self, faktura_ksef, tmp_path):
        """Test that validate command validates structure correctly"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "valid.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        result = runner.invoke(cli, ["validate", "-f", str(xml_file)])

        assert result.exit_code == 0
        assert "jest poprawny" in result.output


class TestInteractiveCommand:
    """Tests for interactive command"""

    def test_interactive_command_basic_flow(self, tmp_path):
        """Test interactive command with basic input"""
        runner = CliRunner()

        # Prepare input for interactive prompts
        input_data = [
            "n",  # Czy masz plik szablonu? (No)
            "5260250274",  # Sprzedawca NIP
            "Moja Firma",  # Sprzedawca Nazwa
            "ul. Test 1",  # Sprzedawca Adres L1
            "",  # Sprzedawca Adres L2 (empty)
            "9492107026",  # Nabywca NIP
            "Klient",  # Nabywca Nazwa
            "ul. Test 2",  # Nabywca Adres L1
            "FV/001",  # Numer faktury
            "2026-02-01",  # Data wystawienia
            "Warszawa",  # Miejsce wystawienia
            "2026-02-01",  # Data sprzedaży
            "Usługa testowa",  # Nazwa pozycji
            "szt",  # Jednostka miary
            "1",  # Ilość
            "100",  # Cena netto
            "23",  # Stawka VAT
            "n",  # Nie dodawaj kolejnej pozycji
            "",  # Stopka faktury (opcjonalnie, pominięcie)
            str(tmp_path / "test_output.xml"),  # Nazwa pliku wyjściowego
            "n",  # Czy chcesz wygenerować wizualizację PDF? (No)
        ]

        result = runner.invoke(cli, ["interactive"], input="\n".join(input_data))

        # Interactive mode should complete
        assert "✓ Faktura wygenerowana" in result.output
        assert (tmp_path / "test_output.xml").exists()

    def test_interactive_command_creates_valid_xml(self, tmp_path):
        """Test that interactive command creates valid XML"""
        from lxml import etree

        runner = CliRunner()

        input_data = [
            "n",  # Czy masz plik szablonu? (No)
            "5260250274",
            "Test Firma",
            "ul. Test 1",
            "",
            "9492107026",
            "Klient",
            "ul. Test 2",
            "FV/001",
            "2026-02-01",
            "Warszawa",
            "2026-02-01",
            "Usługa",
            "szt",
            "1",
            "100",
            "23",
            "n",
            "",  # Stopka faktury (opcjonalnie, pominięcie)
            str(tmp_path / "output.xml"),
            "n",  # Czy chcesz wygenerować wizualizację PDF? (No)
        ]

        result = runner.invoke(cli, ["interactive"], input="\n".join(input_data))

        # Interactive mode should complete successfully
        assert result.exit_code == 0

        output_file = tmp_path / "output.xml"
        assert output_file.exists()

        # Parse and validate XML
        with open(output_file, "rb") as f:
            tree = etree.parse(f)

        root = tree.getroot()
        assert root.tag.endswith("Faktura")

    def test_interactive_command_multiple_items(self, tmp_path):
        """Test interactive command with multiple items"""
        runner = CliRunner()

        input_data = [
            "n",  # Czy masz plik szablonu? (No)
            "5260250274",
            "Test Firma",
            "ul. Test 1",
            "",
            "9492107026",
            "Klient",
            "ul. Test 2",
            "FV/001",
            "2026-02-01",
            "Warszawa",
            "2026-02-01",
            "Usługa 1",  # First item
            "szt",
            "1",
            "100",
            "23",
            "y",  # Add another item
            "Usługa 2",  # Second item
            "godz",
            "2",
            "150",
            "23",
            "n",  # No more items
            "",  # Stopka faktury (opcjonalnie, pominięcie)
            str(tmp_path / "output.xml"),
            "n",  # Czy chcesz wygenerować wizualizację PDF? (No)
        ]

        result = runner.invoke(cli, ["interactive"], input="\n".join(input_data))

        # Interactive mode should complete successfully
        assert result.exit_code == 0

        output_file = tmp_path / "output.xml"
        assert output_file.exists()

        with open(output_file, "r") as f:
            xml_content = f.read()

        assert "Usługa 1" in xml_content
        assert "Usługa 2" in xml_content


class TestCLIVersion:
    """Tests for CLI version"""

    def test_version_option(self):
        """Test --version option"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "1.0.0" in result.output


class TestCLIHelp:
    """Tests for CLI help"""

    def test_help_option(self):
        """Test --help option"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "KSeF CLI" in result.output
        assert "interactive" in result.output
        assert "validate" in result.output
        assert "visualize" in result.output

    def test_validate_help(self):
        """Test validate command help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "file" in result.output

    def test_visualize_help(self):
        """Test visualize command help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["visualize", "--help"])

        assert result.exit_code == 0
        assert "input" in result.output
        assert "output" in result.output


class TestVisualizeCommand:
    """Tests for visualize command"""

    def test_visualize_command_basic(self, faktura_ksef, tmp_path):
        """Test basic visualize command"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        # Generate XML file first
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(cli, ["visualize", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "✓ Wizualizacja PDF wygenerowana" in result.output

    def test_visualize_command_creates_valid_pdf(self, faktura_ksef, tmp_path):
        """Test that visualize command creates valid PDF"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(cli, ["visualize", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()

        # Check PDF header
        with open(output_file, "rb") as f:
            header = f.read(8)
            assert header.startswith(b"%PDF")

    def test_visualize_command_missing_input_file(self, tmp_path):
        """Test visualize command with missing input file"""
        runner = CliRunner()

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(
            cli, ["visualize", "-i", str(tmp_path / "nonexistent.xml"), "-o", str(output_file)]
        )

        assert result.exit_code != 0

    def test_visualize_command_invalid_xml(self, tmp_path):
        """Test visualize command with invalid XML"""
        runner = CliRunner()

        xml_file = tmp_path / "invalid.xml"
        with open(xml_file, "w") as f:
            f.write("< invalid xml >")

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(cli, ["visualize", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "✗ Błąd" in result.output


class TestHtmlCommand:
    """Tests for html command"""

    def test_html_command_creates_file(self, faktura_ksef, tmp_path):
        """Test that html command creates HTML file"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "✓ Wizualizacja HTML wygenerowana" in result.output

    def test_html_command_creates_valid_html(self, faktura_ksef, tmp_path):
        """Test that html command creates valid HTML"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        output_file = tmp_path / "output.html"

        runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        with open(output_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        assert "<!DOCTYPE html>" in html_content
        assert "FAKTURA VAT" in html_content
        assert "SPRZEDAWCA" in html_content
        assert "NABYWCA" in html_content

    def test_html_command_renders_polish_characters(self, faktura_ksef, tmp_path):
        """Test that html command renders Polish characters correctly"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        output_file = tmp_path / "output.html"

        runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        with open(output_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Check UTF-8 charset is declared for Polish character support
        assert 'charset="UTF-8"' in html_content

    def test_html_command_invalid_xml(self, tmp_path):
        """Test html command with invalid XML"""
        runner = CliRunner()

        xml_file = tmp_path / "invalid.xml"
        with open(xml_file, "w") as f:
            f.write("< invalid xml >")

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "✗ Błąd" in result.output

    def test_html_command_renders_stopka_faktury(self, sprzedawca, nabywca, tmp_path):
        """Test that html command renders StopkaFaktury correctly"""
        from datetime import date

        from ksef_cli.generator import KSeFGenerator
        from ksef_cli.models import Faktura, FakturaKSeF, PozycjaFaktury

        runner = CliRunner()

        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23,
        )
        tekst_stopki = "ZESTAWIENIE:\nData  Godziny\n2026-01-01  8 h"
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja],
            stopka_faktury=tekst_stopki,
        )
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        assert "INFORMACJE DODATKOWE" in html_content
        assert "stopka-faktury" in html_content
        assert "ZESTAWIENIE:" in html_content

    def test_html_command_with_ksef_number(self, faktura_ksef, tmp_path):
        """Test that html command includes QR code and verification link when --ksef-number is given"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        output_file = tmp_path / "output.html"
        numer_ksef = "5260250274-20230215-ABC123456789-AB"

        result = runner.invoke(
            cli, ["html", "-i", str(xml_file), "-o", str(output_file), "-k", numer_ksef]
        )

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        assert "WERYFIKACJA FAKTURY W KSeF" in html_content
        assert numer_ksef in html_content
        assert "https://ksef.podatki.gov.pl/web/verify/" in html_content
        assert "data:image/png;base64," in html_content

    def test_html_command_without_ksef_number_no_qr(self, faktura_ksef, tmp_path):
        """Test that html command does not include QR section when --ksef-number is not given"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        assert "WERYFIKACJA FAKTURY W KSeF" not in html_content
        assert "data:image/png;base64," not in html_content


class TestVisualizeCommandWithKSeFNumber:
    """Tests for visualize command with --ksef-number option"""

    def test_visualize_command_with_ksef_number(self, faktura_ksef, tmp_path):
        """Test that visualize command includes QR code section when --ksef-number is given"""
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        output_file = tmp_path / "output.pdf"
        numer_ksef = "5260250274-20230215-ABC123456789-AB"

        result = runner.invoke(
            cli, ["visualize", "-i", str(xml_file), "-o", str(output_file), "-k", numer_ksef]
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert "✓ Wizualizacja PDF wygenerowana" in result.output

        # Check PDF header
        with open(output_file, "rb") as f:
            header = f.read(8)
            assert header.startswith(b"%PDF")


class TestInteractiveCommandExceptionHandlers:
    """Tests for exception handlers in interactive command"""

    def test_interactive_command_generic_exception(self, tmp_path, monkeypatch):
        """Test interactive command handles unexpected exceptions"""
        from ksef_cli import generator as gen_module

        runner = CliRunner()

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("Unexpected interactive error")

        monkeypatch.setattr(gen_module.KSeFGenerator, "generuj", raise_unexpected)

        input_data = "\n".join(
            [
                "n",  # Czy masz plik szablonu? (No)
                "5260250274",  # sprzedawca NIP
                "Moja Firma",  # sprzedawca Nazwa
                "ul. Testowa 1",  # sprzedawca Adres (linia 1)
                "",  # sprzedawca Adres (linia 2) – optional, default=""
                "9492107026",  # nabywca NIP (no adres_l2 prompt for nabywca)
                "Klient",  # nabywca Nazwa
                "ul. Klienta 2",  # nabywca Adres (linia 1)
                "FV/001",  # Numer faktury
                "2026-02-01",  # Data wystawienia
                "Warszawa",  # Miejsce wystawienia
                "2026-02-01",  # Data sprzedaży
                "Usługa",  # Nazwa pozycji (item nr is auto-computed)
                "szt",  # Jednostka miary
                "1",  # Ilość
                "100.00",  # Cena netto
                "23",  # Stawka VAT
                "N",  # Dodać kolejną pozycję? (No)
                "",  # Stopka faktury (optional) – trailing \n lets prompt complete
                "",  # Nazwa pliku wyjściowego
                "",  # Czy chcesz wygenerować wizualizację PDF?
            ]
        )

        result = runner.invoke(cli, ["interactive"], input=input_data)

        assert result.exit_code != 0
        assert "Nieoczekiwany błąd" in result.output


class TestValidateCommandExceptionHandlers:
    """Tests for exception handlers in validate command"""

    def test_validate_command_generic_exception(self, tmp_path, monkeypatch):
        """Test validate command handles unexpected exceptions"""
        from ksef_cli import validator as val_module

        runner = CliRunner()

        xml_file = tmp_path / "valid.xml"
        with open(xml_file, "w") as f:
            f.write("<root/>")

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("Unexpected validate error")

        monkeypatch.setattr(val_module.KSeFValidator, "validate_xml", raise_unexpected)

        result = runner.invoke(cli, ["validate", "-f", str(xml_file)])

        assert result.exit_code != 0
        assert "Błąd walidacji" in result.output


class TestVisualizeCommandExceptionHandlers:
    """Tests for exception handlers in visualize command"""

    def test_visualize_command_oserror(self, faktura_ksef, tmp_path, monkeypatch):
        """Test visualize command handles OSError"""
        from ksef_cli import pdf_generator as pdf_mod
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        def raise_oserror(*args, **kwargs):
            e = OSError("disk full")
            e.strerror = "disk full"
            raise e

        monkeypatch.setattr(pdf_mod.KSeFPDFGenerator, "generuj_z_pliku", raise_oserror)

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(cli, ["visualize", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "Błąd" in result.output

    def test_visualize_command_generic_exception(self, faktura_ksef, tmp_path, monkeypatch):
        """Test visualize command handles unexpected exceptions"""
        from ksef_cli import pdf_generator as pdf_mod
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("Unexpected PDF error")

        monkeypatch.setattr(pdf_mod.KSeFPDFGenerator, "generuj_z_pliku", raise_unexpected)

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(cli, ["visualize", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "Błąd generowania PDF" in result.output


class TestHtmlCommandExceptionHandlers:
    """Tests for exception handlers in html command"""

    def test_html_command_file_not_found(self, tmp_path, monkeypatch):
        """Test html command handles FileNotFoundError"""
        from ksef_cli import html_generator as html_mod

        runner = CliRunner()

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write("<root/>")

        def raise_not_found(*args, **kwargs):
            raise FileNotFoundError("file not found")

        monkeypatch.setattr(html_mod.KSeFHTMLGenerator, "generuj_html_z_pliku", raise_not_found)

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "Nie znaleziono pliku" in result.output

    def test_html_command_oserror(self, faktura_ksef, tmp_path, monkeypatch):
        """Test html command handles OSError"""
        from ksef_cli import html_generator as html_mod
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        def raise_oserror(*args, **kwargs):
            e = OSError("permission denied")
            e.strerror = "permission denied"
            raise e

        monkeypatch.setattr(html_mod.KSeFHTMLGenerator, "generuj_html_z_pliku", raise_oserror)

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "Błąd" in result.output

    def test_html_command_generic_exception(self, faktura_ksef, tmp_path, monkeypatch):
        """Test html command handles unexpected exceptions"""
        from ksef_cli import html_generator as html_mod
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        def raise_unexpected(*args, **kwargs):
            raise RuntimeError("Unexpected HTML error")

        monkeypatch.setattr(html_mod.KSeFHTMLGenerator, "generuj_html_z_pliku", raise_unexpected)

        output_file = tmp_path / "output.html"

        result = runner.invoke(cli, ["html", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "Błąd generowania HTML" in result.output


class TestInteractiveCommandValidationError:
    """Tests for ValidationError in interactive command"""

    def test_interactive_command_validation_error(self, tmp_path):
        """Test interactive command ValidationError with invalid NIP (too short)"""
        runner = CliRunner()

        # NIP '123' is too short (must be exactly 10 chars) so will trigger ValidationError
        input_data = "\n".join(
            [
                "n",  # Czy masz plik szablonu? (No)
                "123",  # Invalid NIP - too short (must be 10 chars)
                "Firma",
                "ul. Testowa 1",
                "",
                "9492107026",
                "Klient",
                "ul. Klienta 2",
                "FV/001",
                "2026-02-01",
                "Warszawa",
                "2026-02-01",
                "Usługa",
                "szt",
                "1",
                "100.00",
                "23",  # stawka VAT
                "N",  # Dodać kolejną pozycję? - No
                "",  # stopka (empty = None)
                str(tmp_path / "output.xml"),
            ]
        )

        result = runner.invoke(cli, ["interactive"], input=input_data)

        assert result.exit_code != 0
        assert "walidacji" in result.output or "Błąd" in result.output

    def test_interactive_command_oserror(self, monkeypatch, tmp_path):
        """Test interactive command OSError when writing output file fails"""
        runner = CliRunner()

        output_file = tmp_path / "output.xml"

        # Provide valid input data - but patch open to fail on write
        input_data = "\n".join(
            [
                "n",  # Czy masz plik szablonu? (No)
                "5260250274",
                "Firma",
                "ul. Testowa 1",
                "",
                "9492107026",
                "Klient",
                "ul. Klienta 2",
                "FV/001",
                "2026-02-01",
                "Warszawa",
                "2026-02-01",
                "Usługa",
                "szt",
                "1",
                "100.00",
                "23",  # stawka VAT
                "N",  # Dodać kolejną pozycję? (No)
                "",  # stopka faktury (empty)
                str(output_file),
            ]
        )

        original_open = open

        def patched_open(file, *args, **kwargs):
            if str(file) == str(output_file) and "w" in str(args):
                e = OSError("Permission denied")
                e.strerror = "Permission denied"
                raise e
            return original_open(file, *args, **kwargs)

        monkeypatch.setattr("builtins.open", patched_open)

        result = runner.invoke(cli, ["interactive"], input=input_data)

        assert result.exit_code != 0


class TestValidateCommandOsError:
    """Tests for OSError in validate command"""

    def test_validate_command_oserror(self, tmp_path, monkeypatch):
        """Test validate command handles OSError when reading the file"""
        runner = CliRunner()

        xml_file = tmp_path / "valid.xml"
        with open(xml_file, "w") as f:
            f.write("<root/>")

        original_open = open

        def patched_open(file, *args, **kwargs):
            if str(file) == str(xml_file):
                e = OSError("Permission denied")
                e.strerror = "Permission denied"
                raise e
            return original_open(file, *args, **kwargs)

        monkeypatch.setattr("builtins.open", patched_open)

        result = runner.invoke(cli, ["validate", "-f", str(xml_file)])

        assert result.exit_code != 0
        assert "Błąd odczytu pliku" in result.output


class TestVisualizeCommandFileNotFound:
    """Test FileNotFoundError in visualize command"""

    def test_visualize_command_file_not_found(self, faktura_ksef, tmp_path, monkeypatch):
        """Test visualize command handles FileNotFoundError from PDF generator"""
        from ksef_cli import pdf_generator as pdf_mod
        from ksef_cli.generator import KSeFGenerator

        runner = CliRunner()

        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        xml_file = tmp_path / "input.xml"
        with open(xml_file, "w") as f:
            f.write(xml)

        def raise_file_not_found(*args, **kwargs):
            raise FileNotFoundError("font file not found")

        monkeypatch.setattr(pdf_mod.KSeFPDFGenerator, "generuj_z_pliku", raise_file_not_found)

        output_file = tmp_path / "output.pdf"

        result = runner.invoke(cli, ["visualize", "-i", str(xml_file), "-o", str(output_file)])

        assert result.exit_code != 0
        assert "Nie znaleziono pliku" in result.output


class TestValidateCommandXmlSyntaxError:
    """Test etree.XMLSyntaxError handler in validate command"""

    def test_validate_command_xml_syntax_error_from_validator(self, tmp_path, monkeypatch):
        """Test validate command handles etree.XMLSyntaxError raised from validator"""
        from lxml import etree

        from ksef_cli import validator as val_module

        runner = CliRunner()

        xml_file = tmp_path / "valid.xml"
        with open(xml_file, "w") as f:
            f.write("<root/>")

        def raise_xml_syntax_error(*args, **kwargs):
            err = etree.XMLSyntaxError("bad XML", None, 5, 1)
            raise err

        monkeypatch.setattr(val_module.KSeFValidator, "validate_xml", raise_xml_syntax_error)

        result = runner.invoke(cli, ["validate", "-f", str(xml_file)])

        assert result.exit_code != 0
        assert "Błąd składni XML" in result.output


class TestInteractiveCommandAbort:
    """Test click.Abort re-raise in interactive command"""

    def test_interactive_command_abort_reraise(self, monkeypatch):
        """Test that click.Abort raised inside interactive command is re-raised"""
        import click as click_module

        from ksef_cli import models as models_module

        runner = CliRunner()

        def raise_abort(*args, **kwargs):
            raise click_module.Abort()

        monkeypatch.setattr(models_module.FakturaKSeF, "__init__", raise_abort)

        input_data = "\n".join(
            [
                "n",  # Czy masz plik szablonu? (No)
                "5260250274",
                "Firma",
                "ul. Testowa 1",
                "",
                "9492107026",
                "Klient",
                "ul. Klienta 2",
                "FV/001",
                "2026-02-01",
                "Warszawa",
                "2026-02-01",
                "Usługa",
                "szt",
                "1",
                "100.00",
                "23",
                "N",
                "",
                "/tmp/output.xml",
            ]
        )

        result = runner.invoke(cli, ["interactive"], input=input_data)

        assert result.exit_code != 0
