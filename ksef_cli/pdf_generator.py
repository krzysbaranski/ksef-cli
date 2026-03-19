"""PDF generator for KSeF invoices."""

import io
import os
from typing import Optional

from lxml import etree
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class KSeFPDFGenerator:
    """Generator PDF dla faktur KSeF"""

    NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"

    def __init__(self):
        self._register_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _register_fonts(self):
        """Rejestruje czcionki obsługujące polskie znaki"""
        # DejaVu Sans fonts support Polish characters (ą, ę, ó, ł, ś, ć, ń, ź, ż)
        # Cross-platform font paths
        import sys

        if sys.platform == "win32":
            font_dirs = [
                "C:\\Windows\\Fonts",
                os.path.expandvars("%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts"),
            ]
        elif sys.platform == "darwin":
            font_dirs = [
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
                "/System/Library/Fonts",
            ]
        else:  # Linux and other Unix-like systems
            font_dirs = [
                "/usr/share/fonts/truetype/dejavu",
                "/usr/share/fonts/TTF",
                os.path.expanduser("~/.fonts"),
            ]

        font_files = [
            ("DejaVuSans.ttf", "DejaVuSans"),
            ("DejaVuSans-Bold.ttf", "DejaVuSans-Bold"),
        ]

        for font_file, font_name in font_files:
            for font_dir in font_dirs:
                font_path = os.path.join(font_dir, font_file)
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        break  # Font registered, move to next font
                    except pdfmetrics.PdfFontEmbedError:
                        pass  # Font already registered, try next
                    except OSError:
                        continue  # File access issue, try next path

    def _setup_styles(self):
        """Konfiguracja stylów dokumentu"""
        # Use DejaVu Sans font for Polish character support, fallback to Helvetica
        font_regular = "DejaVuSans" if self._font_available("DejaVuSans") else "Helvetica"
        font_bold = (
            "DejaVuSans-Bold" if self._font_available("DejaVuSans-Bold") else "Helvetica-Bold"
        )

        self.styles.add(
            ParagraphStyle(
                name="InvoiceTitle",
                fontSize=16,
                leading=20,
                alignment=1,  # Center
                spaceAfter=12,
                fontName=font_bold,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                fontSize=12,
                leading=14,
                fontName=font_bold,
                spaceBefore=12,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="FieldLabel",
                fontSize=9,
                leading=11,
                fontName=font_bold,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="FieldValue",
                fontSize=10,
                leading=12,
                fontName=font_regular,
            )
        )

        # Store font names for use in table styles
        self._font_regular = font_regular
        self._font_bold = font_bold

    def _font_available(self, font_name: str) -> bool:
        """Check if font is registered"""
        return font_name in pdfmetrics.getRegisteredFontNames()

    def generuj_z_xml(
        self, xml_content: str, output_path: str, numer_ksef: Optional[str] = None
    ) -> str:
        """
        Generuje PDF z zawartości XML faktury KSeF.

        Args:
            xml_content: Zawartość XML faktury
            output_path: Ścieżka do pliku wyjściowego PDF
            numer_ksef: Opcjonalny numer KSeF do wygenerowania kodu QR weryfikacji

        Returns:
            Ścieżka do wygenerowanego pliku PDF
        """
        root = etree.fromstring(xml_content.encode("utf-8"))
        return self._generuj_pdf(root, output_path, numer_ksef)

    def generuj_z_pliku(
        self, xml_path: str, output_path: str, numer_ksef: Optional[str] = None
    ) -> str:
        """
        Generuje PDF z pliku XML faktury KSeF.

        Args:
            xml_path: Ścieżka do pliku XML
            output_path: Ścieżka do pliku wyjściowego PDF
            numer_ksef: Opcjonalny numer KSeF do wygenerowania kodu QR weryfikacji

        Returns:
            Ścieżka do wygenerowanego pliku PDF
        """
        with open(xml_path, "rb") as f:
            tree = etree.parse(f)
        return self._generuj_pdf(tree.getroot(), output_path, numer_ksef)

    def _generuj_pdf(
        self, root: etree._Element, output_path: str, numer_ksef: Optional[str] = None
    ) -> str:
        """Generuje PDF z elementu XML"""
        ns = {"ns": self.NAMESPACE}

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        elements = []

        # Tytuł faktury
        numer_faktury = self._get_text(root, ".//ns:Fa/ns:P_2", ns) or "Faktura"
        elements.append(Paragraph(f"FAKTURA VAT {numer_faktury}", self.styles["InvoiceTitle"]))
        elements.append(Spacer(1, 6 * mm))

        # Dane nagłówka
        elements.extend(self._generuj_naglowek(root, ns))
        elements.append(Spacer(1, 4 * mm))

        # Dane stron
        elements.extend(self._generuj_dane_stron(root, ns))
        elements.append(Spacer(1, 4 * mm))

        # Pozycje faktury
        elements.extend(self._generuj_pozycje(root, ns))
        elements.append(Spacer(1, 4 * mm))

        # Podsumowanie
        elements.extend(self._generuj_podsumowanie(root, ns))
        elements.append(Spacer(1, 4 * mm))

        # Płatność
        elements.extend(self._generuj_platnosc(root, ns))

        # Dodatkowe opisy (DodatkowyOpis)
        dodatkowe_opisy = self._generuj_dodatkowe_opisy(root, ns)
        if dodatkowe_opisy:
            elements.append(Spacer(1, 4 * mm))
            elements.extend(dodatkowe_opisy)

        # Sekcja weryfikacji KSeF (gdy podano numer KSeF)
        if numer_ksef:
            elements.append(Spacer(1, 4 * mm))
            elements.extend(self._generuj_weryfikacja_ksef(numer_ksef))

        doc.build(elements)
        return output_path

    def _get_text(
        self, root: etree._Element, xpath: str, ns: dict, default: Optional[str] = None
    ) -> Optional[str]:
        """Pobiera tekst z elementu XML"""
        elem = root.find(xpath, ns)
        return elem.text if elem is not None else default

    def _generuj_naglowek(self, root: etree._Element, ns: dict) -> list:
        """Generuje sekcję nagłówka"""
        elements = []

        data_wystawienia = self._get_text(root, ".//ns:Fa/ns:P_1", ns) or "-"
        miejsce = self._get_text(root, ".//ns:Fa/ns:P_1M", ns) or "-"
        data_sprzedazy = self._get_text(root, ".//ns:Fa/ns:P_6", ns) or "-"

        header_data = [
            ["Data wystawienia:", data_wystawienia, "Miejsce wystawienia:", miejsce],
            ["Data sprzedaży:", data_sprzedazy, "", ""],
        ]

        table = Table(header_data, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), self._font_bold),
                    ("FONTNAME", (2, 0), (2, -1), self._font_bold),
                    ("FONTNAME", (1, 0), (1, -1), self._font_regular),
                    ("FONTNAME", (3, 0), (3, -1), self._font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(table)

        return elements

    def _generuj_dane_stron(self, root: etree._Element, ns: dict) -> list:
        """Generuje sekcję danych sprzedawcy i nabywcy"""
        elements = []

        # Dane sprzedawcy
        sprzedawca_nip = self._get_text(root, ".//ns:Podmiot1//ns:NIP", ns) or "-"
        sprzedawca_nazwa = self._get_text(root, ".//ns:Podmiot1//ns:Nazwa", ns) or "-"
        sprzedawca_adres_l1 = self._get_text(root, ".//ns:Podmiot1//ns:AdresL1", ns) or ""
        sprzedawca_adres_l2 = self._get_text(root, ".//ns:Podmiot1//ns:AdresL2", ns) or ""
        sprzedawca_adres = f"{sprzedawca_adres_l1}"
        if sprzedawca_adres_l2:
            sprzedawca_adres += f", {sprzedawca_adres_l2}"

        # Dane nabywcy
        nabywca_nip = self._get_text(root, ".//ns:Podmiot2//ns:NIP", ns) or "-"
        nabywca_nazwa = self._get_text(root, ".//ns:Podmiot2//ns:Nazwa", ns) or "-"
        nabywca_adres_l1 = self._get_text(root, ".//ns:Podmiot2//ns:AdresL1", ns) or ""
        nabywca_adres_l2 = self._get_text(root, ".//ns:Podmiot2//ns:AdresL2", ns) or ""
        nabywca_adres = f"{nabywca_adres_l1}"
        if nabywca_adres_l2:
            nabywca_adres += f", {nabywca_adres_l2}"

        party_data = [
            [
                Paragraph("<b>SPRZEDAWCA</b>", self.styles["FieldValue"]),
                "",
                Paragraph("<b>NABYWCA</b>", self.styles["FieldValue"]),
                "",
            ],
            ["NIP:", sprzedawca_nip, "NIP:", nabywca_nip],
            ["Nazwa:", sprzedawca_nazwa, "Nazwa:", nabywca_nazwa],
            ["Adres:", sprzedawca_adres, "Adres:", nabywca_adres],
        ]

        table = Table(party_data, colWidths=[20 * mm, 70 * mm, 20 * mm, 70 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), self._font_bold),
                    ("FONTNAME", (2, 0), (2, -1), self._font_bold),
                    ("FONTNAME", (1, 0), (1, -1), self._font_regular),
                    ("FONTNAME", (3, 0), (3, -1), self._font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("SPAN", (0, 0), (1, 0)),
                    ("SPAN", (2, 0), (3, 0)),
                    ("BACKGROUND", (0, 0), (1, 0), colors.lightgrey),
                    ("BACKGROUND", (2, 0), (3, 0), colors.lightgrey),
                    ("BOX", (0, 0), (1, -1), 0.5, colors.black),
                    ("BOX", (2, 0), (3, -1), 0.5, colors.black),
                ]
            )
        )
        elements.append(table)

        return elements

    def _generuj_pozycje(self, root: etree._Element, ns: dict) -> list:
        """Generuje tabelę pozycji faktury"""
        elements = []

        elements.append(Paragraph("POZYCJE FAKTURY", self.styles["SectionHeader"]))

        # Nagłówek tabeli
        header = ["Lp.", "Nazwa", "J.m.", "Ilość", "Cena netto", "Wartość netto", "VAT %"]
        data = [header]

        # Pozycje
        wiersze = root.findall(".//ns:FaWiersz", ns)
        for wiersz in wiersze:
            nr = self._get_text_from_elem(wiersz, "ns:NrWierszaFa", ns) or ""
            nazwa = self._get_text_from_elem(wiersz, "ns:P_7", ns) or ""
            jm = self._get_text_from_elem(wiersz, "ns:P_8A", ns) or ""
            ilosc = self._get_text_from_elem(wiersz, "ns:P_8B", ns) or ""
            cena = self._get_text_from_elem(wiersz, "ns:P_9A", ns) or ""
            wartosc = self._get_text_from_elem(wiersz, "ns:P_11", ns) or ""
            vat = self._get_text_from_elem(wiersz, "ns:P_12", ns) or ""

            data.append([nr, nazwa, jm, ilosc, cena, wartosc, f"{vat}%"])

        col_widths = [10 * mm, 60 * mm, 15 * mm, 20 * mm, 25 * mm, 30 * mm, 20 * mm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), self._font_bold),
                    ("FONTNAME", (0, 1), (-1, -1), self._font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(table)

        return elements

    def _get_text_from_elem(
        self, parent: etree._Element, xpath: str, ns: dict, default: Optional[str] = None
    ) -> Optional[str]:
        """Pobiera tekst z elementu XML względem rodzica"""
        elem = parent.find(xpath, ns)
        return elem.text if elem is not None else default

    def _generuj_podsumowanie(self, root: etree._Element, ns: dict) -> list:
        """Generuje podsumowanie kwot"""
        elements = []

        elements.append(Paragraph("PODSUMOWANIE", self.styles["SectionHeader"]))

        suma_netto = self._get_text(root, ".//ns:Fa/ns:P_13_1", ns) or "0.00"
        suma_vat = self._get_text(root, ".//ns:Fa/ns:P_14_1", ns) or "0.00"
        suma_brutto = self._get_text(root, ".//ns:Fa/ns:P_15", ns) or "0.00"
        waluta = self._get_text(root, ".//ns:Fa/ns:KodWaluty", ns) or "PLN"

        summary_data = [
            ["Suma netto:", f"{suma_netto} {waluta}"],
            ["Suma VAT:", f"{suma_vat} {waluta}"],
            ["SUMA BRUTTO:", f"{suma_brutto} {waluta}"],
        ]

        table = Table(summary_data, colWidths=[130 * mm, 50 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), self._font_bold),
                    ("FONTNAME", (1, 0), (1, 1), self._font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 2), (1, 2), self._font_bold),
                    ("FONTSIZE", (0, 2), (1, 2), 12),
                    ("BACKGROUND", (0, 2), (1, 2), colors.lightgrey),
                    ("BOX", (0, 2), (1, 2), 1, colors.black),
                ]
            )
        )
        elements.append(table)

        return elements

    def _generuj_platnosc(self, root: etree._Element, ns: dict) -> list:
        """Generuje sekcję płatności"""
        elements = []

        forma_platnosci_kod = self._get_text(root, ".//ns:Platnosc/ns:FormaPlatnosci", ns) or "-"

        # Mapowanie kodów form płatności
        formy_platnosci = {
            "1": "Gotówka",
            "2": "Karta płatnicza",
            "3": "Bon",
            "4": "Czek",
            "5": "Kredyt",
            "6": "Przelew",
            "7": "Płatność mobilna",
        }
        forma_platnosci = formy_platnosci.get(forma_platnosci_kod, forma_platnosci_kod)

        payment_data = [["Forma płatności:", forma_platnosci]]

        table = Table(payment_data, colWidths=[45 * mm, 135 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), self._font_bold),
                    ("FONTNAME", (1, 0), (1, -1), self._font_regular),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements.append(table)

        return elements

    def _generuj_dodatkowe_opisy(self, root: etree._Element, ns: dict) -> list:
        """Generuje sekcję dodatkowych opisów (DodatkowyOpis)"""
        elements = []

        dodatkowe_opisy = root.findall(".//ns:Fa/ns:DodatkowyOpis", ns)
        if not dodatkowe_opisy:
            return elements

        elements.append(Paragraph("DODATKOWE INFORMACJE", self.styles["SectionHeader"]))

        opisy_data = []
        for opis in dodatkowe_opisy:
            klucz = self._get_text_from_elem(opis, "ns:Klucz", ns) or ""
            wartosc = self._get_text_from_elem(opis, "ns:Wartosc", ns) or ""
            opisy_data.append([f"{klucz}:", wartosc])

        if opisy_data:
            table = Table(opisy_data, colWidths=[45 * mm, 135 * mm])
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (0, -1), self._font_bold),
                        ("FONTNAME", (1, 0), (1, -1), self._font_regular),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(table)

        return elements

    def _generuj_weryfikacja_ksef(self, numer_ksef: str) -> list:
        """Generuje sekcję weryfikacji KSeF z kodem QR."""
        from .qr_generator import generate_qr_code_png, get_verification_url

        elements = []
        elements.append(Paragraph("WERYFIKACJA FAKTURY W KSeF", self.styles["SectionHeader"]))

        url = get_verification_url(numer_ksef)
        qr_png = generate_qr_code_png(url)

        qr_image = Image(io.BytesIO(qr_png), width=30 * mm, height=30 * mm)

        info_data = [
            [qr_image, Paragraph(f"<b>Numer KSeF:</b> {numer_ksef}", self.styles["FieldValue"])],
            [
                "",
                Paragraph(
                    f"<b>Link weryfikacyjny:</b><br/>{url}",
                    self.styles["FieldValue"],
                ),
            ],
            [
                "",
                Paragraph(
                    "Zeskanuj kod QR lub otwórz link, aby zweryfikować fakturę w systemie KSeF.",
                    self.styles["FieldValue"],
                ),
            ],
        ]

        table = Table(info_data, colWidths=[35 * mm, 145 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (0, -1)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightyellow),
                ]
            )
        )
        elements.append(table)

        return elements
