from datetime import datetime
from lxml import etree
from .models import FakturaKSeF


class KSeFGenerator:
    """Generator XML dla faktur KSeF"""

    NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"
    XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
    XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"

    def __init__(self):
        self.nsmap = {
            None: self.NAMESPACE,
            'xsi': self.XSI_NAMESPACE,
            'xsd': self.XSD_NAMESPACE
        }

    def generuj(self, dane: FakturaKSeF) -> str:
        """Generuje XML faktury KSeF"""
        root = etree.Element(
            f"{{{self.NAMESPACE}}}Faktura",
            nsmap=self.nsmap
        )

        # Nagłówek
        self._dodaj_naglowek(root, dane)

        # Podmiot 1 (Sprzedawca)
        self._dodaj_podmiot1(root, dane.sprzedawca, dane.prefiks_podatnika)

        # Podmiot 2 (Nabywca)
        self._dodaj_podmiot2(root, dane.nabywca)

        # Faktura
        self._dodaj_fakture(root, dane.faktura)

        # Formatowanie XML
        xml_string = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding='utf-8'
        )

        return xml_string.decode('utf-8')

    def _dodaj_naglowek(self, root, dane):
        """Dodaje nagłówek faktury"""
        naglowek = etree.SubElement(root, f"{{{self.NAMESPACE}}}Naglowek")

        kod_formularza = etree.SubElement(
            naglowek,
            f"{{{self.NAMESPACE}}}KodFormularza",
            kodSystemowy="FA (3)",
            wersjaSchemy="1-0E"
        )
        kod_formularza.text = "FA"

        wariant = etree.SubElement(naglowek, f"{{{self.NAMESPACE}}}WariantFormularza")
        wariant.text = "3"

        data_wytw = etree.SubElement(naglowek, f"{{{self.NAMESPACE}}}DataWytworzeniaFa")
        data_wytw.text = datetime.utcnow().isoformat() + "Z"

        system_info = etree.SubElement(naglowek, f"{{{self.NAMESPACE}}}SystemInfo")
        system_info.text = dane.system_info

    def _dodaj_podmiot1(self, root, sprzedawca, prefiks):
        """Dodaje dane sprzedawcy (Podmiot1)"""
        podmiot = etree.SubElement(root, f"{{{self.NAMESPACE}}}Podmiot1")

        prefiks_elem = etree.SubElement(podmiot, f"{{{self.NAMESPACE}}}PrefiksPodatnika")
        prefiks_elem.text = prefiks

        dane_ident = etree.SubElement(podmiot, f"{{{self.NAMESPACE}}}DaneIdentyfikacyjne")
        nip = etree.SubElement(dane_ident, f"{{{self.NAMESPACE}}}NIP")
        nip.text = sprzedawca.nip
        nazwa = etree.SubElement(dane_ident, f"{{{self.NAMESPACE}}}Nazwa")
        nazwa.text = sprzedawca.nazwa

        self._dodaj_adres(podmiot, sprzedawca.adres)

    def _dodaj_podmiot2(self, root, nabywca):
        """Dodaje dane nabywcy (Podmiot2)"""
        podmiot = etree.SubElement(root, f"{{{self.NAMESPACE}}}Podmiot2")

        dane_ident = etree.SubElement(podmiot, f"{{{self.NAMESPACE}}}DaneIdentyfikacyjne")
        nip = etree.SubElement(dane_ident, f"{{{self.NAMESPACE}}}NIP")
        nip.text = nabywca.nip
        nazwa = etree.SubElement(dane_ident, f"{{{self.NAMESPACE}}}Nazwa")
        nazwa.text = nabywca.nazwa

        self._dodaj_adres(podmiot, nabywca.adres)

        # Dodatkowe pola dla Podmiotu2
        jst = etree.SubElement(podmiot, f"{{{self.NAMESPACE}}}JST")
        jst.text = "2"
        gv = etree.SubElement(podmiot, f"{{{self.NAMESPACE}}}GV")
        gv.text = "2"

    def _dodaj_adres(self, parent, adres):
        """Dodaje adres do podmiotu"""
        adres_elem = etree.SubElement(parent, f"{{{self.NAMESPACE}}}Adres")

        kod_kraju = etree.SubElement(adres_elem, f"{{{self.NAMESPACE}}}KodKraju")
        kod_kraju.text = adres.kod_kraju

        adres_l1 = etree.SubElement(adres_elem, f"{{{self.NAMESPACE}}}AdresL1")
        adres_l1.text = adres.adres_l1

        if adres.adres_l2:
            adres_l2 = etree.SubElement(adres_elem, f"{{{self.NAMESPACE}}}AdresL2")
            adres_l2.text = adres.adres_l2

    def _dodaj_fakture(self, root, faktura):
        """Dodaje dane faktury"""
        fa = etree.SubElement(root, f"{{{self.NAMESPACE}}}Fa")

        # Waluta
        waluta = etree.SubElement(fa, f"{{{self.NAMESPACE}}}KodWaluty")
        waluta.text = faktura.waluta

        # Data wystawienia
        p1 = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_1")
        p1.text = faktura.data_wystawienia.isoformat()

        # Miejsce wystawienia
        p1m = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_1M")
        p1m.text = faktura.miejsce_wystawienia

        # Numer faktury
        p2 = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_2")
        p2.text = faktura.numer

        # Data sprzedaży
        p6 = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_6")
        p6.text = faktura.data_sprzedazy.isoformat()

        # Oblicz sumy
        sumy = faktura.oblicz_sumy()

        # Suma netto
        p13_1 = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_13_1")
        p13_1.text = str(sumy['netto'])

        # Suma VAT
        p14_1 = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_14_1")
        p14_1.text = str(sumy['vat'])

        # Suma brutto
        p15 = etree.SubElement(fa, f"{{{self.NAMESPACE}}}P_15")
        p15.text = str(sumy['brutto'])

        # Adnotacje (zgodnie z przykładem)
        self._dodaj_adnotacje(fa)

        # Rodzaj faktury
        rodzaj = etree.SubElement(fa, f"{{{self.NAMESPACE}}}RodzajFaktury")
        rodzaj.text = "VAT"

        # Dodatkowe opisy
        if faktura.dodatkowe_opisy:
            for opis in faktura.dodatkowe_opisy:
                dod_opis = etree.SubElement(fa, f"{{{self.NAMESPACE}}}DodatkowyOpis")
                klucz = etree.SubElement(dod_opis, f"{{{self.NAMESPACE}}}Klucz")
                klucz.text = opis.klucz
                wartosc = etree.SubElement(dod_opis, f"{{{self.NAMESPACE}}}Wartosc")
                wartosc.text = opis.wartosc

        # Pozycje faktury
        for pozycja in faktura.pozycje:
            self._dodaj_wiersz(fa, pozycja)

        # Płatność
        platnosc = etree.SubElement(fa, f"{{{self.NAMESPACE}}}Platnosc")
        forma = etree.SubElement(platnosc, f"{{{self.NAMESPACE}}}FormaPlatnosci")
        forma.text = faktura.forma_platnosci

    def _dodaj_adnotacje(self, fa):
        """Dodaje adnotacje do faktury"""
        adnotacje = etree.SubElement(fa, f"{{{self.NAMESPACE}}}Adnotacje")

        for field in ['P_16', 'P_17', 'P_18', 'P_18A']:
            elem = etree.SubElement(adnotacje, f"{{{self.NAMESPACE}}}{field}")
            elem.text = "2"

        zwolnienie = etree.SubElement(adnotacje, f"{{{self.NAMESPACE}}}Zwolnienie")
        p19n = etree.SubElement(zwolnienie, f"{{{self.NAMESPACE}}}P_19N")
        p19n.text = "1"

        nowe_srodki = etree.SubElement(adnotacje, f"{{{self.NAMESPACE}}}NoweSrodkiTransportu")
        p22n = etree.SubElement(nowe_srodki, f"{{{self.NAMESPACE}}}P_22N")
        p22n.text = "1"

        p23 = etree.SubElement(adnotacje, f"{{{self.NAMESPACE}}}P_23")
        p23.text = "2"

        p_marzy = etree.SubElement(adnotacje, f"{{{self.NAMESPACE}}}PMarzy")
        p_marzy_n = etree.SubElement(p_marzy, f"{{{self.NAMESPACE}}}P_PMarzyN")
        p_marzy_n.text = "1"

    def _dodaj_wiersz(self, fa, pozycja):
        """Dodaje wiersz faktury"""
        wiersz = etree.SubElement(fa, f"{{{self.NAMESPACE}}}FaWiersz")

        nr = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}NrWierszaFa")
        nr.text = str(pozycja.nr)

        p7 = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}P_7")
        p7.text = pozycja.nazwa

        p8a = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}P_8A")
        p8a.text = pozycja.jm

        p8b = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}P_8B")
        p8b.text = str(pozycja.ilosc)

        p9a = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}P_9A")
        p9a.text = str(pozycja.cena_netto)

        p11 = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}P_11")
        p11.text = str(pozycja.wartosc_netto)

        p12 = etree.SubElement(wiersz, f"{{{self.NAMESPACE}}}P_12")
        p12.text = str(pozycja.stawka_vat)