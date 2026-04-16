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
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Colours ──────────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#1a3557")
STEEL = colors.HexColor("#e8eef5")
LIGHT_GREY = colors.HexColor("#f5f5f5")
MID_GREY = colors.HexColor("#cccccc")
WHITE = colors.white

# ── VAT rate buckets defined by FA(3) schema ──────────────────────────────────
VAT_RATE_LABELS = {
    "1": "23%",
    "2": "8%",
    "3": "5%",
    "4": "0%",
    "5": "ZW",
    "6": "OO",
    "7": "Marża",
    "8": "NP",
    "9": "Inne",
    "10": "np.",
    "11": "nie podlega",
}

FORMY_PLATNOSCI = {
    "1": "Gotówka",
    "2": "Karta płatnicza",
    "3": "Bon",
    "4": "Czek",
    "5": "Kredyt",
    "6": "Przelew",
    "7": "Płatność mobilna",
}


class KSeFPDFGenerator:
    """Generator PDF dla faktur KSeF"""

    NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"

    def __init__(self):
        self._register_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    # ── Font registration ─────────────────────────────────────────────────────

    def _register_fonts(self):
        """Register fonts with Polish character support."""
        # Priority search: bundled package fonts → system DejaVu → Arial (macOS)
        candidates = [
            # Bundled with this package
            (
                os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf"),
                "DejaVuSans",
            ),
            (
                os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf"),
                "DejaVuSans-Bold",
            ),
        ]

        # System DejaVu paths (Linux, some macOS via Homebrew)
        for search_dir in [
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/TTF",
            "/opt/homebrew/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
        ]:
            candidates += [
                (os.path.join(search_dir, "DejaVuSans.ttf"), "DejaVuSans"),
                (os.path.join(search_dir, "DejaVuSans-Bold.ttf"), "DejaVuSans-Bold"),
            ]

        # macOS Arial (always present, full Unicode support)
        for search_dir in [
            "/System/Library/Fonts/Supplemental",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]:
            candidates += [
                (os.path.join(search_dir, "Arial.ttf"), "DejaVuSans"),
                (os.path.join(search_dir, "Arial Bold.ttf"), "DejaVuSans-Bold"),
                (os.path.join(search_dir, "Arial.ttf"), "DejaVuSans"),
            ]

        # Windows Arial
        candidates += [
            (r"C:\Windows\Fonts\arial.ttf", "DejaVuSans"),
            (r"C:\Windows\Fonts\arialbd.ttf", "DejaVuSans-Bold"),
        ]

        registered: set[str] = set()
        for font_path, font_name in candidates:
            if font_name in registered:
                continue
            if not os.path.exists(font_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered.add(font_name)
            except Exception:
                continue

    def _font_available(self, font_name: str) -> bool:
        return font_name in pdfmetrics.getRegisteredFontNames()

    # ── Styles ────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        font_regular = "DejaVuSans" if self._font_available("DejaVuSans") else "Helvetica"
        font_bold = (
            "DejaVuSans-Bold" if self._font_available("DejaVuSans-Bold") else "Helvetica-Bold"
        )
        self._font_regular = font_regular
        self._font_bold = font_bold

        self.styles.add(
            ParagraphStyle(
                "InvoiceTitle",
                fontSize=20,
                leading=24,
                alignment=1,
                fontName=font_bold,
                textColor=WHITE,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "SectionHeader",
                fontSize=9,
                leading=11,
                fontName=font_bold,
                textColor=NAVY,
                spaceBefore=0,
                spaceAfter=3,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "FieldLabel",
                fontSize=8,
                leading=10,
                fontName=font_bold,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "FieldValue",
                fontSize=8,
                leading=10,
                fontName=font_regular,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "FooterNote",
                fontSize=8,
                leading=10,
                fontName=font_regular,
                textColor=colors.HexColor("#555555"),
                alignment=1,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "TotalRowLabel",
                fontSize=11,
                leading=14,
                fontName=font_bold,
                textColor=WHITE,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "TotalRowValue",
                fontSize=11,
                leading=14,
                fontName=font_bold,
                textColor=WHITE,
                alignment=2,  # right
            )
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def generuj_z_xml(
        self, xml_content: str, output_path: str, numer_ksef: Optional[str] = None
    ) -> str:
        root = etree.fromstring(xml_content.encode("utf-8"))
        return self._generuj_pdf(root, output_path, numer_ksef)

    def generuj_z_pliku(
        self, xml_path: str, output_path: str, numer_ksef: Optional[str] = None
    ) -> str:
        with open(xml_path, "rb") as f:
            tree = etree.parse(f)
        return self._generuj_pdf(tree.getroot(), output_path, numer_ksef)

    # ── Main builder ──────────────────────────────────────────────────────────

    def _generuj_pdf(
        self, root: etree._Element, output_path: str, numer_ksef: Optional[str] = None
    ) -> str:
        ns = {"ns": self.NAMESPACE}

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=10 * mm,
            bottomMargin=15 * mm,
        )

        elements: list = []

        # ── Title bar ────────────────────────────────────────────────────────
        elements.extend(self._generuj_tytul(root, ns))
        elements.append(Spacer(1, 5 * mm))

        # ── Header dates ─────────────────────────────────────────────────────
        elements.extend(self._generuj_naglowek(root, ns))
        elements.append(Spacer(1, 5 * mm))

        # ── Parties ──────────────────────────────────────────────────────────
        elements.extend(self._generuj_dane_stron(root, ns))
        elements.append(Spacer(1, 5 * mm))

        # ── Line items ────────────────────────────────────────────────────────
        elements.extend(self._generuj_pozycje(root, ns))
        elements.append(Spacer(1, 5 * mm))

        # ── Summary ──────────────────────────────────────────────────────────
        elements.extend(self._generuj_podsumowanie(root, ns))
        elements.append(Spacer(1, 5 * mm))

        # ── Payment ──────────────────────────────────────────────────────────
        elements.extend(self._generuj_platnosc(root, ns))

        # ── Additional descriptions ───────────────────────────────────────────
        dodatkowe = self._generuj_dodatkowe_opisy(root, ns)
        if dodatkowe:
            elements.append(Spacer(1, 4 * mm))
            elements.extend(dodatkowe)

        # ── Footer (Stopka) ───────────────────────────────────────────────────
        stopka = self._generuj_stopka(root, ns)
        if stopka:
            elements.append(Spacer(1, 5 * mm))
            elements.extend(stopka)

        # ── KSeF QR verification ─────────────────────────────────────────────
        if numer_ksef:
            elements.append(Spacer(1, 4 * mm))
            elements.extend(self._generuj_weryfikacja_ksef(numer_ksef))

        doc.build(elements)
        return output_path

    # ── Section builders ─────────────────────────────────────────────────────

    def _generuj_tytul(self, root: etree._Element, ns: dict) -> list:
        """Dark navy title bar with invoice number and type."""
        numer = self._get_text(root, ".//ns:Fa/ns:P_2", ns) or "Faktura"
        rodzaj = self._get_text(root, ".//ns:Fa/ns:RodzajFaktury", ns) or "VAT"
        label = f"FAKTURA {rodzaj} {numer}"

        # Title rendered as a 1-cell table so we can set background colour
        title_para = Paragraph(label, self.styles["InvoiceTitle"])
        table = Table([[title_para]], colWidths=[180 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return [table]

    def _generuj_naglowek(self, root: etree._Element, ns: dict) -> list:
        """Issue date, issue place, sale date — compact 4-column row."""
        data_wystawienia = self._get_text(root, ".//ns:Fa/ns:P_1", ns) or "-"
        miejsce = self._get_text(root, ".//ns:Fa/ns:P_1M", ns) or "-"
        data_sprzedazy = self._get_text(root, ".//ns:Fa/ns:P_6", ns) or "-"
        waluta = self._get_text(root, ".//ns:Fa/ns:KodWaluty", ns) or "PLN"

        def lbl(text):
            return Paragraph(text, self.styles["FieldLabel"])

        def val(text):
            return Paragraph(text, self.styles["FieldValue"])

        rows = [
            [
                lbl("Data wystawienia:"),
                val(data_wystawienia),
                lbl("Miejsce wystawienia:"),
                val(miejsce),
            ],
            [lbl("Data sprzedaży:"), val(data_sprzedazy), lbl("Waluta:"), val(waluta)],
        ]

        table = Table(rows, colWidths=[40 * mm, 40 * mm, 50 * mm, 50 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return [table]

    def _generuj_dane_stron(self, root: etree._Element, ns: dict) -> list:
        """Two-box layout: seller left, buyer right."""

        def get_party(xpath_prefix: str) -> dict:
            nip = self._get_text(root, f".//ns:{xpath_prefix}//ns:NIP", ns) or "-"
            nazwa = self._get_text(root, f".//ns:{xpath_prefix}//ns:Nazwa", ns) or "-"
            l1 = self._get_text(root, f".//ns:{xpath_prefix}//ns:AdresL1", ns) or ""
            l2 = self._get_text(root, f".//ns:{xpath_prefix}//ns:AdresL2", ns) or ""
            return {"nip": nip, "nazwa": nazwa, "adres": f"{l1}{', ' + l2 if l2 else ''}"}

        sprzedawca = get_party("Podmiot1")
        nabywca = get_party("Podmiot2")

        def party_block(label: str, p: dict) -> list:
            """Returns rows for one party."""
            bold = self._font_bold
            regular = self._font_regular
            return [
                [Paragraph(f"<b>{label}</b>", self.styles["FieldLabel"]), ""],
                ["NIP:", p["nip"]],
                ["Nazwa:", p["nazwa"]],
                ["Adres:", p["adres"]],
            ]

        # Each party box is 89mm wide (180mm total - 2mm gap in middle)
        PARTY_W = 89 * mm
        LABEL_W = 18 * mm
        VALUE_W = PARTY_W - LABEL_W

        def party_table(label: str, p: dict) -> Table:
            data = party_block(label, p)
            t = Table(data, colWidths=[LABEL_W, VALUE_W])
            t.setStyle(
                TableStyle(
                    [
                        # header row
                        ("SPAN", (0, 0), (1, 0)),
                        ("BACKGROUND", (0, 0), (1, 0), STEEL),
                        ("FONTNAME", (0, 0), (1, 0), self._font_bold),
                        ("FONTSIZE", (0, 0), (1, 0), 9),
                        ("TOPPADDING", (0, 0), (1, 0), 5),
                        ("BOTTOMPADDING", (0, 0), (1, 0), 5),
                        ("LEFTPADDING", (0, 0), (1, 0), 6),
                        # data rows
                        ("FONTNAME", (0, 1), (0, -1), self._font_bold),
                        ("FONTNAME", (1, 1), (1, -1), self._font_regular),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("TOPPADDING", (0, 1), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
                        ("LEFTPADDING", (0, 1), (0, -1), 6),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        # border
                        ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                        ("LINEBELOW", (0, 0), (1, 0), 0.5, MID_GREY),
                    ]
                )
            )
            return t

        outer = Table(
            [[party_table("SPRZEDAWCA", sprzedawca), "", party_table("NABYWCA", nabywca)]],
            colWidths=[PARTY_W, 2 * mm, PARTY_W],
            hAlign="LEFT",
        )
        outer.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    # Remove all padding from the gap column so 2mm isn't eaten
                    ("LEFTPADDING", (1, 0), (1, -1), 0),
                    ("RIGHTPADDING", (1, 0), (1, -1), 0),
                    ("TOPPADDING", (1, 0), (1, -1), 0),
                    ("BOTTOMPADDING", (1, 0), (1, -1), 0),
                ]
            )
        )
        return [outer]

    def _generuj_pozycje(self, root: etree._Element, ns: dict) -> list:
        """Line-items table with netto, VAT%, VAT amount, brutto columns."""
        elements = []

        elements.append(Paragraph("POZYCJE FAKTURY", self.styles["SectionHeader"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=3))

        header = [
            "Lp.",
            "Nazwa",
            "J.m.",
            "Ilość",
            "Cena netto",
            "Wartość netto",
            "VAT %",
            "Kwota VAT",
            "Wartość brutto",
        ]
        data = [header]

        wiersze = root.findall(".//ns:FaWiersz", ns)
        for wiersz in wiersze:
            nr = self._get_text_from_elem(wiersz, "ns:NrWierszaFa", ns) or ""
            nazwa = self._get_text_from_elem(wiersz, "ns:P_7", ns) or ""
            jm = self._get_text_from_elem(wiersz, "ns:P_8A", ns) or ""
            ilosc = self._get_text_from_elem(wiersz, "ns:P_8B", ns) or ""
            cena = self._get_text_from_elem(wiersz, "ns:P_9A", ns) or ""
            wartosc_netto = self._get_text_from_elem(wiersz, "ns:P_11", ns) or ""
            vat_rate = self._get_text_from_elem(wiersz, "ns:P_12", ns) or ""

            # Calculate VAT amount and gross value
            try:
                netto_val = float(wartosc_netto)
                vat_pct = float(vat_rate)
                kwota_vat = round(netto_val * vat_pct / 100, 2)
                brutto = round(netto_val + kwota_vat, 2)
                kwota_vat_str = f"{kwota_vat:.2f}"
                brutto_str = f"{brutto:.2f}"
            except (ValueError, TypeError):
                kwota_vat_str = ""
                brutto_str = ""

            # Format VAT rate label
            vat_label = f"{vat_rate}%" if vat_rate.replace(".", "").isdigit() else vat_rate

            data.append(
                [nr, nazwa, jm, ilosc, cena, wartosc_netto, vat_label, kwota_vat_str, brutto_str]
            )

        col_widths = [
            8 * mm,
            52 * mm,
            12 * mm,
            14 * mm,
            22 * mm,
            22 * mm,
            12 * mm,
            18 * mm,
            20 * mm,
        ]
        table = Table(data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    # Header
                    ("FONTNAME", (0, 0), (-1, 0), self._font_bold),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("BACKGROUND", (0, 0), (-1, 0), STEEL),
                    ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    # Data rows
                    ("FONTNAME", (0, 1), (-1, -1), self._font_regular),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("TOPPADDING", (0, 1), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                    # Alignment
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Lp.
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),  # J.m.
                    ("ALIGN", (3, 1), (-1, -1), "RIGHT"),  # numeric columns
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Borders
                    ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, MID_GREY),
                    ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                    # Highlight brutto column
                    ("FONTNAME", (-1, 1), (-1, -1), self._font_bold),
                ]
            )
        )
        elements.append(table)
        return elements

    def _generuj_podsumowanie(self, root: etree._Element, ns: dict) -> list:
        """Summary table: per-rate netto/VAT breakdown + total brutto."""
        elements = []

        elements.append(Paragraph("PODSUMOWANIE", self.styles["SectionHeader"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=3))

        waluta = self._get_text(root, ".//ns:Fa/ns:KodWaluty", ns) or "PLN"
        suma_brutto = self._get_text(root, ".//ns:Fa/ns:P_15", ns) or "0.00"

        # Collect per-rate rows (P_13_X = netto, P_14_X = VAT)
        rate_rows = []
        for idx, label in VAT_RATE_LABELS.items():
            netto = self._get_text(root, f".//ns:Fa/ns:P_13_{idx}", ns)
            vat = self._get_text(root, f".//ns:Fa/ns:P_14_{idx}", ns)
            if netto is not None:
                try:
                    brutto_val = float(netto) + float(vat or "0")
                    vat_str = f"{float(vat):.2f} {waluta}" if vat else f"0.00 {waluta}"
                    rate_rows.append(
                        [
                            f"Stawka {label}:",
                            f"{float(netto):.2f} {waluta}",
                            vat_str,
                            f"{brutto_val:.2f} {waluta}",
                        ]
                    )
                except (ValueError, TypeError):
                    pass

        # If we have per-rate data, show a breakdown header first
        W = 180 * mm
        left = 90 * mm
        right_cols = [30 * mm, 30 * mm, 30 * mm]

        if rate_rows:
            header_row = [
                Paragraph("<b>Stawka VAT</b>", self.styles["FieldLabel"]),
                Paragraph("<b>Wartość netto</b>", self.styles["FieldLabel"]),
                Paragraph("<b>Kwota VAT</b>", self.styles["FieldLabel"]),
                Paragraph("<b>Wartość brutto</b>", self.styles["FieldLabel"]),
            ]
            breakdown_data = [header_row] + [
                [
                    Paragraph(r[0], self.styles["FieldValue"]),
                    Paragraph(r[1], self.styles["FieldValue"]),
                    Paragraph(r[2], self.styles["FieldValue"]),
                    Paragraph(r[3], self.styles["FieldValue"]),
                ]
                for r in rate_rows
            ]
            breakdown_table = Table(breakdown_data, colWidths=[left] + right_cols)
            breakdown_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, MID_GREY),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.25, MID_GREY),
                        ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                    ]
                )
            )
            elements.append(breakdown_table)
            elements.append(Spacer(1, 2 * mm))

        # Total brutto row (always shown) — use white-text styles so navy bg is legible
        total_data = [
            [
                Paragraph("SUMA BRUTTO:", self.styles["TotalRowLabel"]),
                Paragraph(f"{float(suma_brutto):.2f} {waluta}", self.styles["TotalRowValue"]),
            ]
        ]
        total_table = Table(
            total_data, colWidths=[left + right_cols[0] + right_cols[1], right_cols[2]]
        )
        total_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (0, -1), 8),
                    ("RIGHTPADDING", (1, 0), (1, -1), 8),
                ]
            )
        )
        elements.append(total_table)
        return elements

    def _generuj_platnosc(self, root: etree._Element, ns: dict) -> list:
        """Payment method section."""
        kod = self._get_text(root, ".//ns:Platnosc/ns:FormaPlatnosci", ns) or "-"
        forma = FORMY_PLATNOSCI.get(kod, kod)

        # Also check for bank account and payment deadline
        termin = self._get_text(root, ".//ns:Platnosc/ns:TerminPlatnosci/ns:Termin", ns)
        numer_konta = self._get_text(root, ".//ns:Platnosc/ns:RachunekBankowy/ns:NrRB", ns)

        rows = [
            [
                Paragraph("<b>Forma płatności:</b>", self.styles["FieldLabel"]),
                Paragraph(forma, self.styles["FieldValue"]),
            ]
        ]
        if termin:
            rows.append(
                [
                    Paragraph("<b>Termin płatności:</b>", self.styles["FieldLabel"]),
                    Paragraph(termin, self.styles["FieldValue"]),
                ]
            )
        if numer_konta:
            rows.append(
                [
                    Paragraph("<b>Numer rachunku:</b>", self.styles["FieldLabel"]),
                    Paragraph(numer_konta, self.styles["FieldValue"]),
                ]
            )

        table = Table(rows, colWidths=[45 * mm, 135 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return [table]

    def _generuj_stopka(self, root: etree._Element, ns: dict) -> list:
        """Invoice footer text from <Stopka><Informacje><StopkaFaktury>."""
        stopka_text = self._get_text(root, ".//ns:Stopka/ns:Informacje/ns:StopkaFaktury", ns)
        if not stopka_text or not stopka_text.strip():
            return []

        elements: list = []
        elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=4))
        # Convert newlines to HTML line breaks for proper display
        formatted_stopka = stopka_text.strip().replace("\n", "<br/>")
        elements.append(Paragraph(formatted_stopka, self.styles["FooterNote"]))
        return elements

    def _generuj_dodatkowe_opisy(self, root: etree._Element, ns: dict) -> list:
        """DodatkowyOpis key-value pairs."""
        elements: list = []
        opisy = root.findall(".//ns:Fa/ns:DodatkowyOpis", ns)
        if not opisy:
            return elements

        elements.append(Paragraph("DODATKOWE INFORMACJE", self.styles["SectionHeader"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=3))

        rows = []
        for opis in opisy:
            klucz = self._get_text_from_elem(opis, "ns:Klucz", ns) or ""
            wartosc = self._get_text_from_elem(opis, "ns:Wartosc", ns) or ""
            rows.append(
                [
                    Paragraph(f"<b>{klucz}:</b>", self.styles["FieldLabel"]),
                    Paragraph(wartosc, self.styles["FieldValue"]),
                ]
            )

        table = Table(rows, colWidths=[45 * mm, 135 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, MID_GREY),
                ]
            )
        )
        elements.append(table)
        return elements

    def _generuj_weryfikacja_ksef(self, numer_ksef: str) -> list:
        """KSeF verification QR code section."""
        from .qr_generator import generate_qr_code_png, get_verification_url

        elements = []
        elements.append(Paragraph("WERYFIKACJA FAKTURY W KSeF", self.styles["SectionHeader"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=3))

        url = get_verification_url(numer_ksef)
        qr_png = generate_qr_code_png(url)
        qr_image = Image(io.BytesIO(qr_png), width=28 * mm, height=28 * mm)

        info_data = [
            [
                qr_image,
                Paragraph(f"<b>Numer KSeF:</b> {numer_ksef}", self.styles["FieldValue"]),
            ],
            [
                "",
                Paragraph(f"<b>Link:</b> {url}", self.styles["FieldValue"]),
            ],
            [
                "",
                Paragraph(
                    "Zeskanuj kod QR lub otwórz link, aby zweryfikować fakturę w systemie KSeF.",
                    self.styles["FieldValue"],
                ),
            ],
        ]

        table = Table(info_data, colWidths=[32 * mm, 148 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (0, -1)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                    ("LINEAFTER", (0, 0), (0, -1), 0.5, MID_GREY),
                ]
            )
        )
        elements.append(table)
        return elements

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_text(
        self, root: etree._Element, xpath: str, ns: dict, default: Optional[str] = None
    ) -> Optional[str]:
        elem = root.find(xpath, ns)
        return elem.text if elem is not None else default

    def _get_text_from_elem(
        self, parent: etree._Element, xpath: str, ns: dict, default: Optional[str] = None
    ) -> Optional[str]:
        elem = parent.find(xpath, ns)
        return elem.text if elem is not None else default
