"""Tests for XML generator in ksef_cli.generator"""
import pytest
from lxml import etree
from datetime import date
from ksef_cli.generator import KSeFGenerator
from ksef_cli.models import (
    Adres,
    Podmiot,
    PozycjaFaktury,
    Faktura,
    FakturaKSeF,
    DodatkowyOpis
)


class TestKSeFGenerator:
    """Tests for KSeF XML generator"""

    def test_generator_initialization(self):
        """Test generator initialization"""
        generator = KSeFGenerator()
        assert generator.NAMESPACE == "http://crd.gov.pl/wzor/2025/06/25/13775/"
        assert generator.XSI_NAMESPACE == "http://www.w3.org/2001/XMLSchema-instance"

    def test_generuj_basic_invoice(self, faktura_ksef):
        """Test generating basic invoice XML"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        assert xml is not None
        assert isinstance(xml, str)
        assert '<?xml version=' in xml
        assert 'encoding="utf-8"' in xml

    def test_xml_valid_structure(self, faktura_ksef):
        """Test XML has valid structure"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        # Parse XML
        root = etree.fromstring(xml.encode('utf-8'))
        
        # Check root element
        assert root.tag.endswith('Faktura')
        
    def test_xml_namespace(self, faktura_ksef):
        """Test XML namespaces are correct"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        
        # Check namespace
        assert 'http://crd.gov.pl/wzor/2025/06/25/13775/' in root.tag

    def test_xml_encoding_utf8(self, faktura_ksef):
        """Test XML uses UTF-8 encoding"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        assert 'encoding="utf-8"' in xml
        
        # Ensure it can be parsed
        root = etree.fromstring(xml.encode('utf-8'))
        assert root is not None

    def test_xml_polish_characters(self, adres_pl_simple):
        """Test XML handles Polish characters correctly"""
        sprzedawca = Podmiot(
            nip="1132347267",
            nazwa="Firma Spółdzielnia",
            adres=adres_pl_simple
        )
        nabywca = Podmiot(
            nip="9492107026",
            nazwa="Klient żółć",
            adres=adres_pl_simple
        )
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa łączy",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23
        )
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Łódź",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja]
        )
        faktura_ksef = FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura
        )
        
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        assert 'Spółdzielnia' in xml
        assert 'żółć' in xml
        assert 'łączy' in xml
        assert 'Łódź' in xml

    def test_naglowek_elements(self, faktura_ksef):
        """Test header elements are present"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        # Find header
        naglowek = root.find('.//ns:Naglowek', ns)
        assert naglowek is not None
        
        # Check KodFormularza
        kod_form = naglowek.find('ns:KodFormularza', ns)
        assert kod_form is not None
        assert kod_form.text == 'FA'
        assert kod_form.get('kodSystemowy') == 'FA (3)'
        assert kod_form.get('wersjaSchemy') == '1-0E'
        
        # Check WariantFormularza
        wariant = naglowek.find('ns:WariantFormularza', ns)
        assert wariant is not None
        assert wariant.text == '3'
        
        # Check SystemInfo
        system_info = naglowek.find('ns:SystemInfo', ns)
        assert system_info is not None
        assert system_info.text == 'KSeF CLI Generator'

    def test_podmiot1_sprzedawca(self, faktura_ksef):
        """Test seller (Podmiot1) data"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        podmiot1 = root.find('.//ns:Podmiot1', ns)
        assert podmiot1 is not None
        
        # Check prefix
        prefiks = podmiot1.find('ns:PrefiksPodatnika', ns)
        assert prefiks is not None
        assert prefiks.text == 'PL'
        
        # Check NIP
        nip = podmiot1.find('.//ns:NIP', ns)
        assert nip is not None
        assert nip.text == '1132347267'
        
        # Check Nazwa
        nazwa = podmiot1.find('.//ns:Nazwa', ns)
        assert nazwa is not None
        assert nazwa.text == 'Moja Firma Sp. z o.o.'

    def test_podmiot2_nabywca(self, faktura_ksef):
        """Test buyer (Podmiot2) data"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        podmiot2 = root.find('.//ns:Podmiot2', ns)
        assert podmiot2 is not None
        
        # Check NIP
        nip = podmiot2.find('.//ns:NIP', ns)
        assert nip is not None
        assert nip.text == '9492107026'
        
        # Check Nazwa
        nazwa = podmiot2.find('.//ns:Nazwa', ns)
        assert nazwa is not None
        assert nazwa.text == 'Klient Sp. z o.o.'
        
        # Check JST
        jst = podmiot2.find('ns:JST', ns)
        assert jst is not None
        assert jst.text == '2'
        
        # Check GV
        gv = podmiot2.find('ns:GV', ns)
        assert gv is not None
        assert gv.text == '2'

    def test_adres_with_two_lines(self, sprzedawca, nabywca, faktura):
        """Test address with two lines"""
        generator = KSeFGenerator()
        faktura_ksef = FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura
        )
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        # Find seller's address
        podmiot1 = root.find('.//ns:Podmiot1', ns)
        adres = podmiot1.find('ns:Adres', ns)
        
        adres_l1 = adres.find('ns:AdresL1', ns)
        assert adres_l1 is not None
        assert adres_l1.text == 'ul. Testowa 123'
        
        adres_l2 = adres.find('ns:AdresL2', ns)
        assert adres_l2 is not None
        assert adres_l2.text == '00-001 Warszawa'

    def test_adres_without_second_line(self, sprzedawca, nabywca, faktura):
        """Test address without second line"""
        generator = KSeFGenerator()
        faktura_ksef = FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura
        )
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        # Find buyer's address (has no L2)
        podmiot2 = root.find('.//ns:Podmiot2', ns)
        adres = podmiot2.find('ns:Adres', ns)
        
        adres_l1 = adres.find('ns:AdresL1', ns)
        assert adres_l1 is not None
        
        adres_l2 = adres.find('ns:AdresL2', ns)
        assert adres_l2 is None  # Should not be present

    def test_faktura_basic_fields(self, faktura_ksef):
        """Test basic invoice fields"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        fa = root.find('.//ns:Fa', ns)
        assert fa is not None
        
        # Currency
        waluta = fa.find('ns:KodWaluty', ns)
        assert waluta is not None
        assert waluta.text == 'PLN'
        
        # Invoice number
        p2 = fa.find('ns:P_2', ns)
        assert p2 is not None
        assert p2.text == 'FV/2026/01/001'
        
        # Place of issue
        p1m = fa.find('ns:P_1M', ns)
        assert p1m is not None
        assert p1m.text == 'Warszawa'
        
        # Invoice type
        rodzaj = fa.find('ns:RodzajFaktury', ns)
        assert rodzaj is not None
        assert rodzaj.text == 'VAT'

    def test_faktura_dates_format(self, faktura_ksef):
        """Test date formatting in invoice"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        fa = root.find('.//ns:Fa', ns)
        
        # Issue date
        p1 = fa.find('ns:P_1', ns)
        assert p1 is not None
        assert p1.text == '2026-02-01'
        
        # Sale date
        p6 = fa.find('ns:P_6', ns)
        assert p6 is not None
        assert p6.text == '2026-02-01'

    def test_faktura_sums(self, faktura_ksef):
        """Test invoice sums calculation"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        fa = root.find('.//ns:Fa', ns)
        
        # Net sum
        p13_1 = fa.find('ns:P_13_1', ns)
        assert p13_1 is not None
        assert float(p13_1.text) == 2500.00
        
        # VAT sum
        p14_1 = fa.find('ns:P_14_1', ns)
        assert p14_1 is not None
        assert float(p14_1.text) == 575.00
        
        # Gross sum
        p15 = fa.find('ns:P_15', ns)
        assert p15 is not None
        assert float(p15.text) == 3075.00

    def test_faktura_wiersz_single(self, sprzedawca, nabywca):
        """Test single invoice line"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa testowa",
            jm="godz",
            ilosc=5.0,
            cena_netto=100.00,
            wartosc_netto=500.00,
            stawka_vat=23
        )
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja]
        )
        faktura_ksef = FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura
        )
        
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        wiersz = root.find('.//ns:FaWiersz', ns)
        assert wiersz is not None
        
        # Line number
        nr = wiersz.find('ns:NrWierszaFa', ns)
        assert nr is not None
        assert nr.text == '1'
        
        # Item name
        p7 = wiersz.find('ns:P_7', ns)
        assert p7 is not None
        assert p7.text == 'Usługa testowa'
        
        # Unit
        p8a = wiersz.find('ns:P_8A', ns)
        assert p8a is not None
        assert p8a.text == 'godz'
        
        # Quantity
        p8b = wiersz.find('ns:P_8B', ns)
        assert p8b is not None
        assert float(p8b.text) == 5.0
        
        # Unit price
        p9a = wiersz.find('ns:P_9A', ns)
        assert p9a is not None
        assert float(p9a.text) == 100.00
        
        # Net value
        p11 = wiersz.find('ns:P_11', ns)
        assert p11 is not None
        assert float(p11.text) == 500.00
        
        # VAT rate
        p12 = wiersz.find('ns:P_12', ns)
        assert p12 is not None
        assert p12.text == '23'

    def test_faktura_wiersz_multiple(self, faktura_ksef):
        """Test multiple invoice lines"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        wiersze = root.findall('.//ns:FaWiersz', ns)
        assert len(wiersze) == 2
        
        # Check first line
        assert wiersze[0].find('ns:NrWierszaFa', ns).text == '1'
        assert wiersze[0].find('ns:P_7', ns).text == 'Usługa programistyczna'
        
        # Check second line
        assert wiersze[1].find('ns:NrWierszaFa', ns).text == '2'
        assert wiersze[1].find('ns:P_7', ns).text == 'Konsultacje IT'

    def test_dodatkowe_opisy(self, sprzedawca, nabywca):
        """Test additional descriptions"""
        pozycja = PozycjaFaktury(
            nr=1,
            nazwa="Usługa",
            jm="szt",
            ilosc=1.0,
            cena_netto=100.00,
            wartosc_netto=100.00,
            stawka_vat=23
        )
        opisy = [
            DodatkowyOpis(klucz="Uwagi", wartosc="Test 1"),
            DodatkowyOpis(klucz="Termin", wartosc="14 dni")
        ]
        faktura = Faktura(
            numer="FV/001",
            data_wystawienia=date(2026, 2, 1),
            miejsce_wystawienia="Warszawa",
            data_sprzedazy=date(2026, 2, 1),
            pozycje=[pozycja],
            dodatkowe_opisy=opisy
        )
        faktura_ksef = FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura
        )
        
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        dod_opisy = root.findall('.//ns:DodatkowyOpis', ns)
        assert len(dod_opisy) == 2
        
        # Check first description
        assert dod_opisy[0].find('ns:Klucz', ns).text == 'Uwagi'
        assert dod_opisy[0].find('ns:Wartosc', ns).text == 'Test 1'

    def test_platnosc(self, faktura_ksef):
        """Test payment information"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        platnosc = root.find('.//ns:Platnosc', ns)
        assert platnosc is not None
        
        forma = platnosc.find('ns:FormaPlatnosci', ns)
        assert forma is not None
        assert forma.text == '6'

    def test_adnotacje(self, faktura_ksef):
        """Test annotations section"""
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)
        
        root = etree.fromstring(xml.encode('utf-8'))
        ns = {'ns': generator.NAMESPACE}
        
        adnotacje = root.find('.//ns:Adnotacje', ns)
        assert adnotacje is not None
        
        # Check various annotation fields
        p16 = adnotacje.find('ns:P_16', ns)
        assert p16 is not None
        assert p16.text == '2'
        
        zwolnienie = adnotacje.find('.//ns:Zwolnienie', ns)
        assert zwolnienie is not None

    def test_different_currencies(self, sprzedawca, nabywca):
        """Test invoice with different currencies"""
        for currency in ['PLN', 'EUR', 'USD']:
            pozycja = PozycjaFaktury(
                nr=1,
                nazwa="Usługa",
                jm="szt",
                ilosc=1.0,
                cena_netto=100.00,
                wartosc_netto=100.00,
                stawka_vat=23
            )
            faktura = Faktura(
                numer="FV/001",
                data_wystawienia=date(2026, 2, 1),
                miejsce_wystawienia="Warszawa",
                data_sprzedazy=date(2026, 2, 1),
                waluta=currency,
                pozycje=[pozycja]
            )
            faktura_ksef = FakturaKSeF(
                sprzedawca=sprzedawca,
                nabywca=nabywca,
                faktura=faktura
            )
            
            generator = KSeFGenerator()
            xml = generator.generuj(faktura_ksef)
            
            root = etree.fromstring(xml.encode('utf-8'))
            ns = {'ns': generator.NAMESPACE}
            
            waluta = root.find('.//ns:KodWaluty', ns)
            assert waluta.text == currency
