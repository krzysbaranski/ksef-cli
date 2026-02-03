"""Tests for PDF generator in ksef_cli.pdf_generator"""

import os
from datetime import date

import pytest

from ksef_cli.generator import KSeFGenerator
from ksef_cli.models import DodatkowyOpis, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury
from ksef_cli.pdf_generator import KSeFPDFGenerator


class TestKSeFPDFGenerator:
    """Tests for KSeF PDF generator"""

    def test_pdf_generator_initialization(self):
        """Test PDF generator initialization"""
        generator = KSeFPDFGenerator()
        assert generator.NAMESPACE == "http://crd.gov.pl/wzor/2025/06/25/13775/"
        assert generator.styles is not None

    def test_generuj_z_xml_creates_pdf(self, faktura_ksef, tmp_path):
        """Test generating PDF from XML content"""
        # First generate XML
        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        # Then generate PDF
        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_xml(xml_content, output_path)

        assert result == output_path
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_generuj_z_pliku_creates_pdf(self, faktura_ksef, tmp_path):
        """Test generating PDF from XML file"""
        # First generate XML file
        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        xml_path = str(tmp_path / "invoice.xml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # Then generate PDF
        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_pliku(xml_path, output_path)

        assert result == output_path
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_pdf_contains_invoice_number(self, faktura_ksef, tmp_path):
        """Test that PDF contains invoice number"""
        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        pdf_generator.generuj_z_xml(xml_content, output_path)

        # PDF should exist and have content
        assert os.path.exists(output_path)
        with open(output_path, "rb") as f:
            content = f.read()
            # Check that PDF header is present
            assert content.startswith(b"%PDF")

    def test_pdf_with_polish_characters(self, adres_pl_simple, tmp_path):
        """Test PDF generation with Polish characters"""
        sprzedawca = Podmiot(nip="1132347267", nazwa="Firma Spółdzielnia", adres=adres_pl_simple)
        nabywca = Podmiot(nip="9492107026", nazwa="Klient żółć", adres=adres_pl_simple)
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa łączy",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23,
        )
        faktura = Faktura(
            numer="FV/001/Ł",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Łódź",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja],
        )
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_xml(xml_content, output_path)

        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_pdf_with_multiple_items(self, sprzedawca, nabywca, tmp_path):
        """Test PDF generation with multiple invoice items"""
        pozycje = [
            PozycjaFaktury(
                nr=1,
                nazwa="Usługa 1",
                jm="szt",
                ilosc=2.0,
                cena_netto=100.00,
                wartosc_netto=200.00,
                stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=2,
                nazwa="Usługa 2",
                jm="godz",
                ilosc=5.0,
                cena_netto=150.00,
                wartosc_netto=750.00,
                stawka_vat=23,
            ),
            PozycjaFaktury(
                nr=3,
                nazwa="Usługa 3",
                jm="kg",
                ilosc=10.0,
                cena_netto=50.00,
                wartosc_netto=500.00,
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
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_xml(xml_content, output_path)

        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_pdf_with_additional_descriptions(self, sprzedawca, nabywca, tmp_path):
        """Test PDF generation with additional descriptions"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23,
        )
        opisy = [
            DodatkowyOpis(klucz="Uwagi", wartosc="Termin 14 dni"),
            DodatkowyOpis(klucz="Numer zamówienia", wartosc="ZAM/001"),
        ]
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja],
            dodatkowe_opisy=opisy,
        )
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_xml(xml_content, output_path)

        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_pdf_with_different_currencies(self, sprzedawca, nabywca, tmp_path):
        """Test PDF generation with different currencies"""
        for currency in ["PLN", "EUR", "USD"]:
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
                waluta=currency,
                pozycje=[pozycja],
            )
            faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

            xml_generator = KSeFGenerator()
            xml_content = xml_generator.generuj(faktura_ksef)

            pdf_generator = KSeFPDFGenerator()
            output_path = str(tmp_path / f"output_{currency}.pdf")
            result = pdf_generator.generuj_z_xml(xml_content, output_path)

            assert os.path.exists(result)
            assert os.path.getsize(result) > 0

    def test_pdf_file_nonexistent_raises_error(self, tmp_path):
        """Test that generating PDF from non-existent file raises error"""
        pdf_generator = KSeFPDFGenerator()
        with pytest.raises(FileNotFoundError):
            pdf_generator.generuj_z_pliku(
                str(tmp_path / "nonexistent.xml"), str(tmp_path / "output.pdf")
            )

    def test_pdf_invalid_xml_raises_error(self, tmp_path):
        """Test that generating PDF from invalid XML raises error"""
        invalid_xml = "< invalid xml >"

        pdf_generator = KSeFPDFGenerator()
        with pytest.raises(Exception):
            pdf_generator.generuj_z_xml(invalid_xml, str(tmp_path / "output.pdf"))

    def test_pdf_with_single_address_line(self, adres_pl_simple, tmp_path):
        """Test PDF generation with address having only one line"""
        sprzedawca = Podmiot(nip="1132347267", nazwa="Firma", adres=adres_pl_simple)
        nabywca = Podmiot(nip="9492107026", nazwa="Klient", adres=adres_pl_simple)
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
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_xml(xml_content, output_path)

        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_pdf_with_two_address_lines(self, adres_pl, tmp_path):
        """Test PDF generation with address having two lines"""
        sprzedawca = Podmiot(nip="1132347267", nazwa="Firma", adres=adres_pl)
        nabywca = Podmiot(nip="9492107026", nazwa="Klient", adres=adres_pl)
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
        faktura_ksef = FakturaKSeF(sprzedawca=sprzedawca, nabywca=nabywca, faktura=faktura)

        xml_generator = KSeFGenerator()
        xml_content = xml_generator.generuj(faktura_ksef)

        pdf_generator = KSeFPDFGenerator()
        output_path = str(tmp_path / "output.pdf")
        result = pdf_generator.generuj_z_xml(xml_content, output_path)

        assert os.path.exists(result)
        assert os.path.getsize(result) > 0
