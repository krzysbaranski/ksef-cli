"""Tests for template loader functionality."""

from datetime import date

import pytest

from ksef_cli.generator import KSeFGenerator
from ksef_cli.models import (
    Adres,
    Faktura,
    FakturaKSeF,
    Podmiot,
    PozycjaFaktury,
)
from ksef_cli.template_loader import TemplateLoader


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
                PozycjaFaktury(
                    nr=2,
                    nazwa="Usługa programowania",
                    jm="godz",
                    ilosc=16.0,
                    cena_netto=150.0,
                    wartosc_netto=2400.0,
                    stawka_vat=23,
                ),
            ],
            stopka_faktury="Dziękujemy za współpracę!",
        ),
    )


class TestTemplateLoader:
    """Tests for TemplateLoader class"""

    def test_load_from_xml_basic(self, sample_invoice, tmp_path):
        """Test loading a basic invoice from XML template"""
        # Generate XML
        generator = KSeFGenerator()
        xml = generator.generuj(sample_invoice)

        # Save to file
        xml_file = tmp_path / "template.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        # Load from file
        loader = TemplateLoader()
        loaded = loader.load_from_xml(str(xml_file))

        # Verify seller data
        assert loaded.sprzedawca.nip == "5260250274"
        assert loaded.sprzedawca.nazwa == "Test Sprzedawca"
        assert loaded.sprzedawca.adres.adres_l1 == "ul. Testowa 1"
        assert loaded.sprzedawca.adres.adres_l2 == "Warszawa"

    def test_load_from_xml_buyer_data(self, sample_invoice, tmp_path):
        """Test that buyer data is correctly loaded"""
        generator = KSeFGenerator()
        xml = generator.generuj(sample_invoice)

        xml_file = tmp_path / "template.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        loader = TemplateLoader()
        loaded = loader.load_from_xml(str(xml_file))

        # Verify buyer data
        assert loaded.nabywca.nip == "9492107026"
        assert loaded.nabywca.nazwa == "Test Nabywca"
        assert loaded.nabywca.adres.adres_l1 == "ul. Klienta 2"

    def test_load_from_xml_invoice_header(self, sample_invoice, tmp_path):
        """Test that invoice header data is correctly loaded"""
        generator = KSeFGenerator()
        xml = generator.generuj(sample_invoice)

        xml_file = tmp_path / "template.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        loader = TemplateLoader()
        loaded = loader.load_from_xml(str(xml_file))

        # Verify invoice header
        assert loaded.faktura.numer == "FV/001/2026"
        assert loaded.faktura.data_wystawienia == date(2026, 1, 15)
        assert loaded.faktura.miejsce_wystawienia == "Warszawa"
        assert loaded.faktura.data_sprzedazy == date(2026, 1, 15)
        assert loaded.faktura.waluta == "PLN"

    def test_load_from_xml_line_items(self, sample_invoice, tmp_path):
        """Test that line items are correctly loaded"""
        generator = KSeFGenerator()
        xml = generator.generuj(sample_invoice)

        xml_file = tmp_path / "template.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        loader = TemplateLoader()
        loaded = loader.load_from_xml(str(xml_file))

        # Verify line items
        assert len(loaded.faktura.pozycje) == 2

        # First item
        poz1 = loaded.faktura.pozycje[0]
        assert poz1.nazwa == "Usługa konsultacji"
        assert poz1.jm == "godz"
        assert poz1.ilosc == 8.0
        assert poz1.cena_netto == 100.0
        assert poz1.wartosc_netto == 800.0
        assert poz1.stawka_vat == 23

        # Second item
        poz2 = loaded.faktura.pozycje[1]
        assert poz2.nazwa == "Usługa programowania"
        assert poz2.jm == "godz"
        assert poz2.ilosc == 16.0

    def test_load_from_xml_footer(self, sample_invoice, tmp_path):
        """Test that invoice footer is correctly loaded"""
        generator = KSeFGenerator()
        xml = generator.generuj(sample_invoice)

        xml_file = tmp_path / "template.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml)

        loader = TemplateLoader()
        loaded = loader.load_from_xml(str(xml_file))

        # Verify footer
        assert loaded.faktura.stopka_faktury == "Dziękujemy za współpracę!"

    def test_load_from_xml_file_not_found(self):
        """Test that OSError is raised for missing file"""
        loader = TemplateLoader()

        with pytest.raises(OSError):
            loader.load_from_xml("/nonexistent/path/template.xml")

    def test_load_from_xml_invalid_xml(self, tmp_path):
        """Test that ValueError is raised for invalid XML"""
        xml_file = tmp_path / "invalid.xml"
        with open(xml_file, "w") as f:
            f.write("< invalid xml >")

        loader = TemplateLoader()

        with pytest.raises(ValueError, match="Invalid XML"):
            loader.load_from_xml(str(xml_file))

    def test_load_and_regenerate(self, sample_invoice, tmp_path):
        """Test that a loaded invoice can be regenerated"""
        # Generate original
        generator = KSeFGenerator()
        original_xml = generator.generuj(sample_invoice)

        # Save and load
        xml_file = tmp_path / "template.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(original_xml)

        loader = TemplateLoader()
        loaded = loader.load_from_xml(str(xml_file))

        # Regenerate
        regenerated_xml = generator.generuj(loaded)

        # Both should contain the same key data
        assert "FV/001/2026" in regenerated_xml
        assert "5260250274" in regenerated_xml
        assert "Test Sprzedawca" in regenerated_xml
        assert "Usługa konsultacji" in regenerated_xml
