"""Tests for CLI commands in ksef_cli.cli"""
import pytest
import json
import tempfile
from pathlib import Path
from click.testing import CliRunner
from datetime import date
from ksef_cli.cli import cli


class TestGenerateCommand:
    """Tests for generate command"""

    def test_generate_command_basic(self, sample_invoice_json, tmp_path):
        """Test basic generate command"""
        runner = CliRunner()
        
        # Create input file
        input_file = tmp_path / "input.json"
        with open(input_file, 'w') as f:
            json.dump(sample_invoice_json, f)
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(input_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert '✓ Faktura wygenerowana' in result.output

    def test_generate_command_creates_valid_xml(self, sample_invoice_json, tmp_path):
        """Test that generate command creates valid XML"""
        from lxml import etree
        
        runner = CliRunner()
        
        input_file = tmp_path / "input.json"
        with open(input_file, 'w') as f:
            json.dump(sample_invoice_json, f)
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(input_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        
        # Parse the output XML
        with open(output_file, 'rb') as f:
            tree = etree.parse(f)
        
        root = tree.getroot()
        assert root.tag.endswith('Faktura')

    def test_generate_command_missing_input_file(self, tmp_path):
        """Test generate command with missing input file"""
        runner = CliRunner()
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(tmp_path / "nonexistent.json"),
            '-o', str(output_file)
        ])
        
        assert result.exit_code != 0

    def test_generate_command_invalid_json(self, tmp_path):
        """Test generate command with invalid JSON"""
        runner = CliRunner()
        
        input_file = tmp_path / "invalid.json"
        with open(input_file, 'w') as f:
            f.write("{ invalid json }")
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(input_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code != 0

    def test_generate_command_missing_required_fields(self, tmp_path):
        """Test generate command with missing required fields"""
        runner = CliRunner()
        
        # Incomplete data
        incomplete_data = {
            "sprzedawca": {
                "nip": "1132347267"
                # Missing nazwa and adres
            }
        }
        
        input_file = tmp_path / "incomplete.json"
        with open(input_file, 'w') as f:
            json.dump(incomplete_data, f)
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(input_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code != 0

    def test_generate_command_with_dodatkowe_opisy(self, tmp_path):
        """Test generate command with additional descriptions"""
        runner = CliRunner()
        
        data = {
            "sprzedawca": {
                "nip": "1132347267",
                "nazwa": "Test Firma",
                "adres": {
                    "kod_kraju": "PL",
                    "adres_l1": "ul. Test 1"
                }
            },
            "nabywca": {
                "nip": "9492107026",
                "nazwa": "Klient",
                "adres": {
                    "kod_kraju": "PL",
                    "adres_l1": "ul. Test 2"
                }
            },
            "faktura": {
                "numer": "FV/001",
                "data_wystawienia": "2026-02-01",
                "miejsce_wystawienia": "Warszawa",
                "data_sprzedazy": "2026-02-01",
                "waluta": "PLN",
                "pozycje": [
                    {
                        "nr": 1,
                        "nazwa": "Usługa",
                        "jm": "szt",
                        "ilosc": 1,
                        "cena_netto": 100.00,
                        "wartosc_netto": 100.00,
                        "stawka_vat": 23
                    }
                ],
                "forma_platnosci": "6",
                "dodatkowe_opisy": [
                    {
                        "klucz": "Uwagi",
                        "wartosc": "Termin: 14 dni"
                    }
                ]
            }
        }
        
        input_file = tmp_path / "input.json"
        with open(input_file, 'w') as f:
            json.dump(data, f)
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(input_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        
        # Check that additional descriptions are in XML
        with open(output_file, 'r') as f:
            xml_content = f.read()
        
        assert 'Uwagi' in xml_content
        assert 'Termin: 14 dni' in xml_content

    def test_generate_command_multiple_items(self, tmp_path):
        """Test generate command with multiple invoice items"""
        runner = CliRunner()
        
        data = {
            "sprzedawca": {
                "nip": "1132347267",
                "nazwa": "Test Firma",
                "adres": {
                    "kod_kraju": "PL",
                    "adres_l1": "ul. Test 1"
                }
            },
            "nabywca": {
                "nip": "9492107026",
                "nazwa": "Klient",
                "adres": {
                    "kod_kraju": "PL",
                    "adres_l1": "ul. Test 2"
                }
            },
            "faktura": {
                "numer": "FV/001",
                "data_wystawienia": "2026-02-01",
                "miejsce_wystawienia": "Warszawa",
                "data_sprzedazy": "2026-02-01",
                "waluta": "PLN",
                "pozycje": [
                    {
                        "nr": 1,
                        "nazwa": "Usługa 1",
                        "jm": "szt",
                        "ilosc": 2,
                        "cena_netto": 100.00,
                        "wartosc_netto": 200.00,
                        "stawka_vat": 23
                    },
                    {
                        "nr": 2,
                        "nazwa": "Usługa 2",
                        "jm": "godz",
                        "ilosc": 5,
                        "cena_netto": 150.00,
                        "wartosc_netto": 750.00,
                        "stawka_vat": 23
                    }
                ],
                "forma_platnosci": "6"
            }
        }
        
        input_file = tmp_path / "input.json"
        with open(input_file, 'w') as f:
            json.dump(data, f)
        
        output_file = tmp_path / "output.xml"
        
        result = runner.invoke(cli, [
            'generate',
            '-i', str(input_file),
            '-o', str(output_file)
        ])
        
        assert result.exit_code == 0
        
        with open(output_file, 'r') as f:
            xml_content = f.read()
        
        assert 'Usługa 1' in xml_content
        assert 'Usługa 2' in xml_content


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
        with open(xml_file, 'w') as f:
            f.write(xml)
        
        result = runner.invoke(cli, [
            'validate',
            '-f', str(xml_file)
        ])
        
        assert result.exit_code == 0
        assert '✓ Plik' in result.output
        assert 'jest poprawnym XML' in result.output

    def test_validate_command_invalid_xml(self, tmp_path):
        """Test validate command with invalid XML"""
        runner = CliRunner()
        
        xml_file = tmp_path / "invalid.xml"
        with open(xml_file, 'w') as f:
            f.write("< invalid xml >")
        
        result = runner.invoke(cli, [
            'validate',
            '-f', str(xml_file)
        ])
        
        assert result.exit_code != 0
        assert '✗ Błąd walidacji' in result.output

    def test_validate_command_missing_file(self, tmp_path):
        """Test validate command with missing file"""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'validate',
            '-f', str(tmp_path / "nonexistent.xml")
        ])
        
        assert result.exit_code != 0

    def test_validate_command_shows_root_element(self, faktura_ksef, tmp_path):
        """Test that validate command shows root element"""
        from ksef_cli.generator import KSeFGenerator
        
        runner = CliRunner()
        
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        xml_file = tmp_path / "valid.xml"
        with open(xml_file, 'w') as f:
            f.write(xml)
        
        result = runner.invoke(cli, [
            'validate',
            '-f', str(xml_file)
        ])
        
        assert result.exit_code == 0
        assert 'Element główny' in result.output


class TestInteractiveCommand:
    """Tests for interactive command"""

    def test_interactive_command_basic_flow(self, tmp_path):
        """Test interactive command with basic input"""
        runner = CliRunner()
        
        # Prepare input for interactive prompts
        input_data = [
            '1132347267',  # Sprzedawca NIP
            'Moja Firma',  # Sprzedawca Nazwa
            'ul. Test 1',  # Sprzedawca Adres L1
            '',  # Sprzedawca Adres L2 (empty)
            '9492107026',  # Nabywca NIP
            'Klient',  # Nabywca Nazwa
            'ul. Test 2',  # Nabywca Adres L1
            'FV/001',  # Numer faktury
            '2026-02-01',  # Data wystawienia
            'Warszawa',  # Miejsce wystawienia
            '2026-02-01',  # Data sprzedaży
            'Usługa testowa',  # Nazwa pozycji
            'szt',  # Jednostka miary
            '1',  # Ilość
            '100',  # Cena netto
            '23',  # Stawka VAT
            'n',  # Nie dodawaj kolejnej pozycji
            str(tmp_path / 'test_output.xml')  # Nazwa pliku wyjściowego
        ]
        
        result = runner.invoke(cli, ['interactive'], input='\n'.join(input_data))
        
        # Interactive mode should complete
        assert '✓ Faktura wygenerowana' in result.output
        assert (tmp_path / 'test_output.xml').exists()

    def test_interactive_command_creates_valid_xml(self, tmp_path):
        """Test that interactive command creates valid XML"""
        from lxml import etree
        
        runner = CliRunner()
        
        input_data = [
            '1132347267',
            'Test Firma',
            'ul. Test 1',
            '',
            '9492107026',
            'Klient',
            'ul. Test 2',
            'FV/001',
            '2026-02-01',
            'Warszawa',
            '2026-02-01',
            'Usługa',
            'szt',
            '1',
            '100',
            '23',
            'n',
            str(tmp_path / 'output.xml')
        ]
        
        result = runner.invoke(cli, ['interactive'], input='\n'.join(input_data))
        
        output_file = tmp_path / 'output.xml'
        assert output_file.exists()
        
        # Parse and validate XML
        with open(output_file, 'rb') as f:
            tree = etree.parse(f)
        
        root = tree.getroot()
        assert root.tag.endswith('Faktura')

    def test_interactive_command_multiple_items(self, tmp_path):
        """Test interactive command with multiple items"""
        runner = CliRunner()
        
        input_data = [
            '1132347267',
            'Test Firma',
            'ul. Test 1',
            '',
            '9492107026',
            'Klient',
            'ul. Test 2',
            'FV/001',
            '2026-02-01',
            'Warszawa',
            '2026-02-01',
            'Usługa 1',  # First item
            'szt',
            '1',
            '100',
            '23',
            'y',  # Add another item
            'Usługa 2',  # Second item
            'godz',
            '2',
            '150',
            '23',
            'n',  # No more items
            str(tmp_path / 'output.xml')
        ]
        
        result = runner.invoke(cli, ['interactive'], input='\n'.join(input_data))
        
        output_file = tmp_path / 'output.xml'
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            xml_content = f.read()
        
        assert 'Usługa 1' in xml_content
        assert 'Usługa 2' in xml_content


class TestCLIVersion:
    """Tests for CLI version"""

    def test_version_option(self):
        """Test --version option"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert '1.0.0' in result.output


class TestCLIHelp:
    """Tests for CLI help"""

    def test_help_option(self):
        """Test --help option"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'KSeF CLI' in result.output
        assert 'generate' in result.output
        assert 'interactive' in result.output
        assert 'validate' in result.output

    def test_generate_help(self):
        """Test generate command help"""
        runner = CliRunner()
        result = runner.invoke(cli, ['generate', '--help'])
        
        assert result.exit_code == 0
        assert 'input' in result.output
        assert 'output' in result.output

    def test_validate_help(self):
        """Test validate command help"""
        runner = CliRunner()
        result = runner.invoke(cli, ['validate', '--help'])
        
        assert result.exit_code == 0
        assert 'file' in result.output
