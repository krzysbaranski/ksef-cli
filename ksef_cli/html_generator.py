"""HTML generator for KSeF invoices using XSL-inspired templates."""

from typing import List, Optional

from lxml import etree


class KSeFHTMLGenerator:
    """Generator HTML dla faktur KSeF - inspirowany oficjalnym stylem XSL."""

    NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"

    # Invoice type mappings (from official XSL)
    RODZAJ_FAKTURY = {
        "VAT": "Faktura podstawowa",
        "KOR": "Faktura korygująca",
        "ZAL": "Faktura dokumentująca otrzymanie zapłaty lub jej części przed dokonaniem "
        "czynności oraz faktura wystawiona w związku z art. 106f ust. 4 ustawy "
        "(faktura zaliczkowa)",
        "ROZ": "Faktura wystawiona w związku z art. 106f ust. 3 ustawy",
        "UPR": "Faktura, o której mowa w art. 106e ust. 5 pkt 3 ustawy",
        "KOR_ZAL": "Faktura korygująca fakturę dokumentującą otrzymanie zapłaty lub jej części "
        "przed dokonaniem czynności oraz fakturę wystawioną w związku z art. 106f ust. 4 "
        "ustawy (faktura korygująca fakturę zaliczkową)",
        "KOR_ROZ": "Faktura korygująca fakturę wystawioną w związku z art. 106f ust. 3 ustawy",
    }

    # Payment method mappings
    FORMY_PLATNOSCI = {
        "1": "Gotówka",
        "2": "Karta płatnicza",
        "3": "Bon",
        "4": "Czek",
        "5": "Kredyt",
        "6": "Przelew",
        "7": "Płatność mobilna",
    }

    def __init__(self):
        self._ns = {"ns": self.NAMESPACE}

    def generuj_html(self, xml_content: str, numer_ksef: Optional[str] = None) -> str:
        """
        Generuje HTML z zawartości XML faktury KSeF.

        Args:
            xml_content: Zawartość XML faktury
            numer_ksef: Opcjonalny numer KSeF do wygenerowania kodu QR weryfikacji

        Returns:
            Zawartość HTML
        """
        root = etree.fromstring(xml_content.encode("utf-8"))
        return self._generuj_html(root, numer_ksef)

    def generuj_html_z_pliku(self, xml_path: str, numer_ksef: Optional[str] = None) -> str:
        """
        Generuje HTML z pliku XML faktury KSeF.

        Args:
            xml_path: Ścieżka do pliku XML
            numer_ksef: Opcjonalny numer KSeF do wygenerowania kodu QR weryfikacji

        Returns:
            Zawartość HTML
        """
        with open(xml_path, "rb") as f:
            tree = etree.parse(f)
        return self._generuj_html(tree.getroot(), numer_ksef)

    def _get_text(
        self, root: etree._Element, xpath: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Pobiera tekst z elementu XML."""
        elem = root.find(xpath, self._ns)
        return elem.text if elem is not None and elem.text else default

    def _generuj_html(self, root: etree._Element, numer_ksef: Optional[str] = None) -> str:
        """Generuje kompletny dokument HTML."""
        html_parts: List[str] = []

        # Document header
        html_parts.append(self._generuj_html_header())

        # Main content
        html_parts.append('<div class="faktura">')

        # KSeF header
        html_parts.append(self._generuj_ksef_header())

        # Form code info
        html_parts.append(self._generuj_kod_formularza(root))

        # Invoice type and title
        html_parts.append(self._generuj_tytul(root))

        # Invoice details
        html_parts.append(self._generuj_dane_faktury(root))

        # Seller and Buyer
        html_parts.append(self._generuj_strony(root))

        # Third party (Podmiot3)
        html_parts.append(self._generuj_podmiot3(root))

        # Authorized party (PodmiotUpowazniony)
        html_parts.append(self._generuj_podmiot_upowazniony(root))

        # Invoice lines
        html_parts.append(self._generuj_pozycje(root))

        # VAT summary
        html_parts.append(self._generuj_podsumowanie_vat(root))

        # Payment
        html_parts.append(self._generuj_platnosc(root))

        # Annotations
        html_parts.append(self._generuj_adnotacje(root))

        # Correction reason (for KOR invoices)
        html_parts.append(self._generuj_przyczyna_korekty(root))

        # Additional descriptions
        html_parts.append(self._generuj_dodatkowe_opisy(root))

        # Transaction conditions
        html_parts.append(self._generuj_warunki_transakcji(root))

        # Footer
        html_parts.append(self._generuj_stopka(root))

        # KSeF verification QR code (when KSeF number is provided)
        if numer_ksef:
            html_parts.append(self._generuj_weryfikacja_ksef(numer_ksef))

        # System info
        html_parts.append(self._generuj_system_info(root))

        html_parts.append("</div>")  # Close faktura div
        html_parts.append(self._generuj_html_footer())

        return "\n".join(html_parts)

    def _generuj_html_header(self) -> str:
        """Generuje nagłówek HTML z CSS."""
        return """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>e-FAKTURA KSeF</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .faktura {
            max-width: 210mm;
            margin: 0 auto;
            background: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .ksef-header {
            text-align: left;
            margin-bottom: 10px;
            color: #333;
        }
        .ksef-header b { font-size: 14px; }
        .ksef-header .red { color: #cc0000; }
        .kod-formularza {
            background: #e0e0e0;
            padding: 5px 10px;
            margin-bottom: 15px;
            font-size: 11px;
        }
        .tytul {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            background: #f0f0f0;
            border: 1px solid #ccc;
        }
        .tytul h1 { margin: 0 0 5px 0; font-size: 18px; }
        .tytul .rodzaj { font-size: 12px; color: #666; }
        .section {
            margin: 15px 0;
            padding: 10px;
            border: 1px solid #ddd;
        }
        .section-header {
            font-weight: bold;
            font-size: 13px;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        th, td {
            padding: 5px 8px;
            text-align: left;
            border: 1px solid #ddd;
        }
        th {
            background: #e8e8e8;
            font-weight: bold;
        }
        .strony-table td { border: none; vertical-align: top; }
        .strony-table .header { background: #e0e0e0; font-weight: bold; }
        .label { font-weight: bold; color: #555; }
        .value { color: #000; }
        .pozycje-table th { text-align: center; font-size: 11px; }
        .pozycje-table td { text-align: right; font-size: 11px; }
        .pozycje-table td:nth-child(1),
        .pozycje-table td:nth-child(2) { text-align: left; }
        .podsumowanie { text-align: right; }
        .podsumowanie .total {
            font-size: 14px;
            font-weight: bold;
            background: #f0f0f0;
        }
        .info-row { margin: 5px 0; }
        .info-row .label { display: inline-block; min-width: 150px; }
        .system-info {
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ccc;
            font-size: 10px;
            color: #666;
        }
        .adnotacja { margin: 5px 0; padding: 5px; background: #fafafa; }
        .stopka-faktury {
            font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
            font-size: 11px;
            white-space: pre;
            margin: 0;
            padding: 5px 0;
            background: none;
            border: none;
        }
        @media print {
            body { background: white; padding: 0; }
            .faktura { box-shadow: none; max-width: none; }
        }
    </style>
</head>
<body>"""

    def _generuj_html_footer(self) -> str:
        """Generuje stopkę HTML."""
        return """</body>
</html>"""

    def _generuj_ksef_header(self) -> str:
        """Generuje nagłówek KSeF."""
        return """<div class="ksef-header">
    <b>Krajowy System <span class="red">e</span>-Faktur (KS<span class="red">e</span>F)</b>
</div>"""

    def _generuj_kod_formularza(self, root: etree._Element) -> str:
        """Generuje informację o kodzie formularza."""
        kod = self._get_text(root, ".//ns:Naglowek/ns:KodFormularza", "FA")
        wariant = self._get_text(root, ".//ns:Naglowek/ns:WariantFormularza", "3")

        # Get kodSystemowy attribute
        kod_elem = root.find(".//ns:Naglowek/ns:KodFormularza", self._ns)
        kod_systemowy = ""
        if kod_elem is not None:
            kod_systemowy = kod_elem.get("kodSystemowy", "FA (3)")

        return f"""<div class="kod-formularza">
    <span class="kod">{kod}</span> <span class="wariant">({wariant})</span>
    &nbsp;|&nbsp; Kod systemowy: <b>{kod_systemowy}</b>
</div>"""

    def _generuj_tytul(self, root: etree._Element) -> str:
        """Generuje tytuł faktury."""
        numer = self._get_text(root, ".//ns:Fa/ns:P_2", "-")
        rodzaj_kod = self._get_text(root, ".//ns:Fa/ns:RodzajFaktury", "VAT") or "VAT"
        rodzaj_nazwa = self.RODZAJ_FAKTURY.get(rodzaj_kod, "Faktura")

        return f"""<div class="tytul">
    <h1>FAKTURA VAT nr {numer}</h1>
    <div class="rodzaj">{rodzaj_nazwa}</div>
</div>"""

    def _generuj_dane_faktury(self, root: etree._Element) -> str:
        """Generuje dane faktury."""
        waluta = self._get_text(root, ".//ns:Fa/ns:KodWaluty", "PLN")
        data_wyst = self._get_text(root, ".//ns:Fa/ns:P_1", "-")
        miejsce = self._get_text(root, ".//ns:Fa/ns:P_1M", "")
        data_sprz = self._get_text(root, ".//ns:Fa/ns:P_6", "")

        # Period dates
        okres_od = self._get_text(root, ".//ns:Fa/ns:OkresFa/ns:P_6_Od", "")
        okres_do = self._get_text(root, ".//ns:Fa/ns:OkresFa/ns:P_6_Do", "")

        html = '<div class="section">'
        html += f"""
    <div class="info-row"><span class="label">Kod waluty:</span> <b>{waluta}</b></div>
    <div class="info-row"><span class="label">Data wystawienia:</span> <b>{data_wyst}</b></div>"""

        if miejsce:
            html += f'\n    <div class="info-row"><span class="label">Miejsce wystawienia:</span> <b>{miejsce}</b></div>'

        if data_sprz:
            html += f'\n    <div class="info-row"><span class="label">Data sprzedaży:</span> <b>{data_sprz}</b></div>'

        if okres_od and okres_do:
            html += f"""
    <div class="info-row"><span class="label">Okres od:</span> <b>{okres_od}</b></div>
    <div class="info-row"><span class="label">Okres do:</span> <b>{okres_do}</b></div>"""

        # TP flag (related parties)
        tp = self._get_text(root, ".//ns:Fa/ns:TP", "")
        if tp == "1":
            html += (
                '\n    <div class="info-row adnotacja">✓ Powiązania między nabywcą a dostawcą</div>'
            )

        html += "\n</div>"
        return html

    def _generuj_strony(self, root: etree._Element) -> str:
        """Generuje sekcję sprzedawcy i nabywcy."""
        # Seller data
        sprzedawca_nip = self._get_text(root, ".//ns:Podmiot1//ns:NIP", "-")
        sprzedawca_nazwa = self._get_text(root, ".//ns:Podmiot1//ns:Nazwa", "-")
        sprzedawca_adres1 = self._get_text(root, ".//ns:Podmiot1//ns:AdresL1", "")
        sprzedawca_adres2 = self._get_text(root, ".//ns:Podmiot1//ns:AdresL2", "")
        sprzedawca_kod_kraju = self._get_text(root, ".//ns:Podmiot1//ns:Adres/ns:KodKraju", "PL")
        sprzedawca_email = self._get_text(root, ".//ns:Podmiot1//ns:DaneKontaktowe/ns:Email", "")
        sprzedawca_tel = self._get_text(root, ".//ns:Podmiot1//ns:DaneKontaktowe/ns:Telefon", "")

        # Buyer data
        nabywca_nip = self._get_text(root, ".//ns:Podmiot2//ns:NIP", "-")
        nabywca_nazwa = self._get_text(root, ".//ns:Podmiot2//ns:Nazwa", "-")
        nabywca_adres1 = self._get_text(root, ".//ns:Podmiot2//ns:AdresL1", "")
        nabywca_adres2 = self._get_text(root, ".//ns:Podmiot2//ns:AdresL2", "")
        nabywca_kod_kraju = self._get_text(root, ".//ns:Podmiot2//ns:Adres/ns:KodKraju", "PL")
        nabywca_email = self._get_text(root, ".//ns:Podmiot2//ns:DaneKontaktowe/ns:Email", "")
        nabywca_tel = self._get_text(root, ".//ns:Podmiot2//ns:DaneKontaktowe/ns:Telefon", "")
        nabywca_nr_klienta = self._get_text(root, ".//ns:Podmiot2/ns:NrKlienta", "")

        sprzedawca_adres = sprzedawca_adres1 or ""
        if sprzedawca_adres2:
            sprzedawca_adres += f", {sprzedawca_adres2}"

        nabywca_adres = nabywca_adres1 or ""
        if nabywca_adres2:
            nabywca_adres += f", {nabywca_adres2}"

        html = """<div class="section">
    <table class="strony-table">
        <tr>
            <td class="header" style="width:50%">SPRZEDAWCA</td>
            <td class="header" style="width:50%">NABYWCA</td>
        </tr>
        <tr>
            <td>
                <div><span class="label">NIP:</span> <b>"""
        html += f"{sprzedawca_kod_kraju} {sprzedawca_nip}</b></div>"
        html += f'\n                <div><span class="label">Nazwa:</span> {sprzedawca_nazwa}</div>'
        html += f'\n                <div><span class="label">Adres:</span> {sprzedawca_adres}</div>'
        if sprzedawca_email:
            html += (
                f'\n                <div><span class="label">Email:</span> {sprzedawca_email}</div>'
            )
        if sprzedawca_tel:
            html += (
                f'\n                <div><span class="label">Telefon:</span> {sprzedawca_tel}</div>'
            )
        html += """
            </td>
            <td>
                <div><span class="label">NIP:</span> <b>"""
        html += f"{nabywca_kod_kraju} {nabywca_nip}</b></div>"
        html += f'\n                <div><span class="label">Nazwa:</span> {nabywca_nazwa}</div>'
        html += f'\n                <div><span class="label">Adres:</span> {nabywca_adres}</div>'
        if nabywca_email:
            html += (
                f'\n                <div><span class="label">Email:</span> {nabywca_email}</div>'
            )
        if nabywca_tel:
            html += (
                f'\n                <div><span class="label">Telefon:</span> {nabywca_tel}</div>'
            )
        if nabywca_nr_klienta:
            html += f'\n                <div><span class="label">Nr klienta:</span> {nabywca_nr_klienta}</div>'
        html += """
            </td>
        </tr>
    </table>
</div>"""
        return html

    def _generuj_podmiot3(self, root: etree._Element) -> str:
        """Generuje sekcję podmiotów trzecich."""
        podmioty = root.findall(".//ns:Podmiot3", self._ns)
        if not podmioty:
            return ""

        html = '<div class="section">\n    <div class="section-header">PODMIOTY TRZECIE</div>'

        for i, podmiot in enumerate(podmioty, 1):
            nip = self._get_text(podmiot, ".//ns:NIP", "")
            nazwa = self._get_text(podmiot, ".//ns:Nazwa", "")
            rola = self._get_text(podmiot, ".//ns:Rola", "")

            html += '\n    <div style="margin: 10px 0; padding: 5px; background: #fafafa;">'
            html += f"\n        <b>Podmiot {i}</b>"
            if rola:
                html += f" - Rola: {rola}"
            if nip:
                html += f'\n        <div><span class="label">NIP:</span> {nip}</div>'
            if nazwa:
                html += f'\n        <div><span class="label">Nazwa:</span> {nazwa}</div>'
            html += "\n    </div>"

        html += "\n</div>"
        return html

    def _generuj_podmiot_upowazniony(self, root: etree._Element) -> str:
        """Generuje sekcję podmiotu upoważnionego."""
        podmiot = root.find(".//ns:PodmiotUpowazniony", self._ns)
        if podmiot is None:
            return ""

        nip = self._get_text(podmiot, ".//ns:NIP", "")
        nazwa = self._get_text(podmiot, ".//ns:Nazwa", "")
        rola = self._get_text(podmiot, ".//ns:Rola", "")

        html = '<div class="section">\n    <div class="section-header">PODMIOT UPOWAŻNIONY</div>'
        if rola:
            html += f'\n    <div><span class="label">Rola:</span> {rola}</div>'
        if nip:
            html += f'\n    <div><span class="label">NIP:</span> {nip}</div>'
        if nazwa:
            html += f'\n    <div><span class="label">Nazwa:</span> {nazwa}</div>'
        html += "\n</div>"
        return html

    def _generuj_pozycje(self, root: etree._Element) -> str:
        """Generuje tabelę pozycji faktury."""
        wiersze = root.findall(".//ns:FaWiersz", self._ns)
        if not wiersze:
            return ""

        html = """<div class="section">
    <div class="section-header">POZYCJE FAKTURY</div>
    <table class="pozycje-table">
        <thead>
            <tr>
                <th>Lp.</th>
                <th>Nazwa towaru/usługi</th>
                <th>J.m.</th>
                <th>Ilość</th>
                <th>Cena netto</th>
                <th>Wartość netto</th>
                <th>VAT %</th>
            </tr>
        </thead>
        <tbody>"""

        for wiersz in wiersze:
            nr = self._get_text(wiersz, "ns:NrWierszaFa", "")
            nazwa = self._get_text(wiersz, "ns:P_7", "")
            jm = self._get_text(wiersz, "ns:P_8A", "")
            ilosc = self._get_text(wiersz, "ns:P_8B", "")
            cena = self._get_text(wiersz, "ns:P_9A", "")
            wartosc = self._get_text(wiersz, "ns:P_11", "")
            vat = self._get_text(wiersz, "ns:P_12", "")

            html += f"""
            <tr>
                <td>{nr}</td>
                <td style="text-align:left">{nazwa}</td>
                <td>{jm}</td>
                <td>{ilosc}</td>
                <td>{cena}</td>
                <td>{wartosc}</td>
                <td>{vat}%</td>
            </tr>"""

        html += """
        </tbody>
    </table>
</div>"""
        return html

    def _generuj_podsumowanie_vat(self, root: etree._Element) -> str:
        """Generuje podsumowanie VAT."""
        waluta = self._get_text(root, ".//ns:Fa/ns:KodWaluty", "PLN")
        netto = self._get_text(root, ".//ns:Fa/ns:P_13_1", "0.00")
        vat = self._get_text(root, ".//ns:Fa/ns:P_14_1", "0.00")
        brutto = self._get_text(root, ".//ns:Fa/ns:P_15", "0.00")

        return f"""<div class="section podsumowanie">
    <table style="width: 50%; margin-left: auto;">
        <tr>
            <td class="label">Suma netto:</td>
            <td><b>{netto} {waluta}</b></td>
        </tr>
        <tr>
            <td class="label">Suma VAT:</td>
            <td><b>{vat} {waluta}</b></td>
        </tr>
        <tr class="total">
            <td class="label">SUMA BRUTTO:</td>
            <td><b>{brutto} {waluta}</b></td>
        </tr>
    </table>
</div>"""

    def _generuj_platnosc(self, root: etree._Element) -> str:
        """Generuje sekcję płatności."""
        forma_kod = self._get_text(root, ".//ns:Platnosc/ns:FormaPlatnosci", "")
        forma_nazwa = self.FORMY_PLATNOSCI.get(forma_kod, forma_kod) if forma_kod else ""

        termin = self._get_text(root, ".//ns:Platnosc/ns:TerminPlatnosci/ns:Termin", "")
        rachunek = self._get_text(root, ".//ns:Platnosc/ns:RachunekBankowy/ns:NrRB", "")
        nazwa_banku = self._get_text(root, ".//ns:Platnosc/ns:RachunekBankowy/ns:NazwaBanku", "")
        swift = self._get_text(root, ".//ns:Platnosc/ns:RachunekBankowy/ns:SWIFT", "")

        if not any([forma_nazwa, termin, rachunek]):
            return ""

        html = '<div class="section">\n    <div class="section-header">PŁATNOŚĆ</div>'

        if forma_nazwa:
            html += f'\n    <div class="info-row"><span class="label">Forma płatności:</span> {forma_nazwa}</div>'
        if termin:
            html += f'\n    <div class="info-row"><span class="label">Termin płatności:</span> {termin}</div>'
        if rachunek:
            html += f'\n    <div class="info-row"><span class="label">Numer rachunku:</span> {rachunek}</div>'
        if nazwa_banku:
            html += (
                f'\n    <div class="info-row"><span class="label">Bank:</span> {nazwa_banku}</div>'
            )
        if swift:
            html += (
                f'\n    <div class="info-row"><span class="label">SWIFT/BIC:</span> {swift}</div>'
            )

        html += "\n</div>"
        return html

    def _generuj_adnotacje(self, root: etree._Element) -> str:
        """Generuje sekcję adnotacji."""
        adnotacje = root.find(".//ns:Fa/ns:Adnotacje", self._ns)
        if adnotacje is None:
            return ""

        items = []

        # P_16 - special procedure
        p16 = self._get_text(adnotacje, "ns:P_16", "")
        if p16 == "1":
            items.append("Metoda kasowa")

        # P_17 - self-billing
        p17 = self._get_text(adnotacje, "ns:P_17", "")
        if p17 == "1":
            items.append("Samofakturowanie")

        # P_18 - tax representative
        p18 = self._get_text(adnotacje, "ns:P_18", "")
        if p18 == "1":
            items.append("Wystawienie przez przedstawiciela podatkowego")

        # P_23 - cash method
        p23 = self._get_text(adnotacje, "ns:P_23", "")
        if p23 == "1":
            items.append("Metoda kasowa VAT")

        # Zwolnienie
        zwolnienie = adnotacje.find("ns:Zwolnienie", self._ns)
        if zwolnienie is not None:
            p19 = self._get_text(zwolnienie, "ns:P_19", "")
            if p19:
                items.append(f"Podstawa zwolnienia: {p19}")

        if not items:
            return ""

        html = '<div class="section">\n    <div class="section-header">ADNOTACJE</div>'
        for item in items:
            html += f'\n    <div class="adnotacja">✓ {item}</div>'
        html += "\n</div>"
        return html

    def _generuj_przyczyna_korekty(self, root: etree._Element) -> str:
        """Generuje przyczynę korekty dla faktur korygujących."""
        przyczyna = self._get_text(root, ".//ns:Fa/ns:PrzyczynaKorekty", "")
        nr_faktury_kor = self._get_text(root, ".//ns:Fa/ns:NrFaKorygowanej", "")

        if not przyczyna and not nr_faktury_kor:
            return ""

        html = '<div class="section">\n    <div class="section-header">KOREKTA</div>'
        if nr_faktury_kor:
            html += f'\n    <div class="info-row"><span class="label">Nr faktury korygowanej:</span> {nr_faktury_kor}</div>'
        if przyczyna:
            html += f'\n    <div class="info-row"><span class="label">Przyczyna korekty:</span> {przyczyna}</div>'
        html += "\n</div>"
        return html

    def _generuj_dodatkowe_opisy(self, root: etree._Element) -> str:
        """Generuje sekcję dodatkowych opisów."""
        opisy = root.findall(".//ns:Fa/ns:DodatkowyOpis", self._ns)
        if not opisy:
            return ""

        html = '<div class="section">\n    <div class="section-header">DODATKOWE INFORMACJE</div>'

        for opis in opisy:
            klucz = self._get_text(opis, "ns:Klucz", "")
            wartosc = self._get_text(opis, "ns:Wartosc", "")
            if klucz or wartosc:
                html += f'\n    <div class="info-row"><span class="label">{klucz}:</span> {wartosc}</div>'

        html += "\n</div>"
        return html

    def _generuj_warunki_transakcji(self, root: etree._Element) -> str:
        """Generuje sekcję warunków transakcji."""
        warunki = root.find(".//ns:Fa/ns:WarunkiTransakcji", self._ns)
        if warunki is None:
            return ""

        html = '<div class="section">\n    <div class="section-header">WARUNKI TRANSAKCJI</div>'

        # Zamówienie
        zamowienia = warunki.findall(".//ns:Zamowienia/ns:DataZamowienia", self._ns)
        for zam in zamowienia:
            if zam.text:
                html += f'\n    <div class="info-row"><span class="label">Data zamówienia:</span> {zam.text}</div>'

        # Umowa
        umowy = warunki.findall(".//ns:Umowy/ns:DataUmowy", self._ns)
        for um in umowy:
            if um.text:
                html += f'\n    <div class="info-row"><span class="label">Data umowy:</span> {um.text}</div>'

        html += "\n</div>"
        return html

    def _generuj_stopka(self, root: etree._Element) -> str:
        """Generuje stopkę faktury."""
        stopka = root.find(".//ns:Stopka", self._ns)
        if stopka is None:
            return ""

        stopka_faktury = self._get_text(stopka, "ns:Informacje/ns:StopkaFaktury", "")
        rejestry = self._get_text(stopka, "ns:Rejestry/ns:KRS", "")

        if not stopka_faktury and not rejestry:
            return ""

        html = '<div class="section">\n    <div class="section-header">INFORMACJE DODATKOWE</div>'
        if rejestry:
            html += f'\n    <div class="info-row"><span class="label">KRS:</span> {rejestry}</div>'
        if stopka_faktury:
            html += f'\n    <div class="info-row"><pre class="stopka-faktury">{stopka_faktury}</pre></div>'
        html += "\n</div>"
        return html

    def _generuj_weryfikacja_ksef(self, numer_ksef: str) -> str:
        """Generuje sekcję weryfikacji KSeF z kodem QR."""
        from .qr_generator import generate_qr_code_base64, get_verification_url

        url = get_verification_url(numer_ksef)
        qr_base64 = generate_qr_code_base64(url)

        return f"""<div class="section ksef-weryfikacja">
    <div class="section-header">WERYFIKACJA FAKTURY W KSeF</div>
    <div style="display: flex; align-items: flex-start; gap: 20px; flex-wrap: wrap;">
        <div>
            <img src="data:image/png;base64,{qr_base64}" alt="Kod QR weryfikacji KSeF"
                 style="width: 120px; height: 120px; border: 1px solid #ccc;">
        </div>
        <div>
            <div class="info-row">
                <span class="label">Numer KSeF:</span> <b>{numer_ksef}</b>
            </div>
            <div class="info-row">
                <span class="label">Link weryfikacyjny:</span>
                <a href="{url}" target="_blank">{url}</a>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #555;">
                Zeskanuj kod QR lub kliknij link, aby zweryfikować fakturę w systemie KSeF.
            </div>
        </div>
    </div>
</div>"""

    def _generuj_system_info(self, root: etree._Element) -> str:
        """Generuje informacje systemowe."""
        data_wytw = self._get_text(root, ".//ns:Naglowek/ns:DataWytworzeniaFa", "")
        system_info = self._get_text(root, ".//ns:Naglowek/ns:SystemInfo", "")

        html = '<div class="system-info">'
        if data_wytw:
            html += f"\n    Data i czas wytworzenia faktury: <b>{data_wytw}</b>"
        if system_info:
            html += f"\n    <br>System: <b>{system_info}</b>"
        html += "\n</div>"
        return html
