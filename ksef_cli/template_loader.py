"""Load invoice templates from XML files."""

from datetime import date
from lxml import etree

from .models import Adres, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury


class TemplateLoader:
    """Load and parse invoice XML templates."""

    NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"

    def load_from_xml(self, file_path: str) -> FakturaKSeF:
        """Load invoice from XML template file."""
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            return self._parse_faktura(root)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid XML: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {file_path}")

    def _parse_faktura(self, root) -> FakturaKSeF:
        """Parse XML root into FakturaKSeF model."""
        sprzedawca = self._parse_podmiot1(root)
        nabywca = self._parse_podmiot2(root)
        faktura = self._parse_fa(root)

        # Get footer from root level if exists
        stopka = self._get_text(root, "Stopka/Informacje/StopkaFaktury")
        if stopka:
            faktura.stopka_faktury = stopka

        return FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=faktura,
        )

    def _parse_podmiot1(self, root) -> Podmiot:
        """Parse Podmiot1 (seller) from XML."""
        elem = root.find(f"{{{self.NAMESPACE}}}Podmiot1")
        if elem is None:
            raise ValueError("Podmiot1 (seller) not found in template")

        dane_ident = elem.find(f"{{{self.NAMESPACE}}}DaneIdentyfikacyjne")
        nip = self._get_text(dane_ident, "NIP")
        nazwa = self._get_text(dane_ident, "Nazwa")
        adres = self._parse_adres(elem)

        return Podmiot(nip=nip, nazwa=nazwa, adres=adres)

    def _parse_podmiot2(self, root) -> Podmiot:
        """Parse Podmiot2 (buyer) from XML."""
        elem = root.find(f"{{{self.NAMESPACE}}}Podmiot2")
        if elem is None:
            raise ValueError("Podmiot2 (buyer) not found in template")

        dane_ident = elem.find(f"{{{self.NAMESPACE}}}DaneIdentyfikacyjne")
        nip = self._get_text(dane_ident, "NIP")
        nazwa = self._get_text(dane_ident, "Nazwa")
        adres = self._parse_adres(elem)

        return Podmiot(nip=nip, nazwa=nazwa, adres=adres)

    def _parse_adres(self, parent) -> Adres:
        """Parse address from element."""
        adres_elem = parent.find(f"{{{self.NAMESPACE}}}Adres")
        kod_kraju = self._get_text(adres_elem, "KodKraju") or "PL"
        adres_l1 = self._get_text(adres_elem, "AdresL1")
        adres_l2 = self._get_text(adres_elem, "AdresL2")

        return Adres(kod_kraju=kod_kraju, adres_l1=adres_l1, adres_l2=adres_l2)

    def _parse_fa(self, root) -> Faktura:
        """Parse Fa (invoice) from XML."""
        fa = root.find(f"{{{self.NAMESPACE}}}Fa")
        if fa is None:
            raise ValueError("Fa (invoice) not found in template")

        numer = self._get_text(fa, "P_2")
        data_wystawienia_str = self._get_text(fa, "P_1")
        miejsce_wystawienia = self._get_text(fa, "P_1M")
        data_sprzedazy_str = self._get_text(fa, "P_6")
        waluta = self._get_text(fa, "KodWaluty") or "PLN"

        data_wystawienia = date.fromisoformat(data_wystawienia_str)
        data_sprzedazy = date.fromisoformat(data_sprzedazy_str)

        # Parse line items (Wiersze)
        pozycje = self._parse_pozycje(fa)

        forma_platnosci = self._get_text(fa, "Platnosc/FormaPlatnosci") or "6"

        return Faktura(
            numer=numer,
            data_wystawienia=data_wystawienia,
            miejsce_wystawienia=miejsce_wystawienia,
            data_sprzedazy=data_sprzedazy,
            waluta=waluta,
            pozycje=pozycje,
            forma_platnosci=forma_platnosci,
            stopka_faktury=None,
        )

    def _parse_pozycje(self, fa) -> list[PozycjaFaktury]:
        """Parse line items from invoice."""
        pozycje = []
        wiersz_elements = fa.findall(f"{{{self.NAMESPACE}}}FaWiersz")

        for wiersz in wiersz_elements:
            nr = int(self._get_text(wiersz, "NrWierszaFa") or "0")
            nazwa = self._get_text(wiersz, "P_7")
            jm = self._get_text(wiersz, "P_8A")
            ilosc = float(self._get_text(wiersz, "P_8B") or "0")
            cena_netto = float(self._get_text(wiersz, "P_9A") or "0")
            wartosc_netto = float(self._get_text(wiersz, "P_11") or "0")
            stawka_vat = int(self._get_text(wiersz, "P_12") or "0")

            pozycje.append(
                PozycjaFaktury(
                    nr=nr,
                    nazwa=nazwa,
                    jm=jm,
                    ilosc=ilosc,
                    cena_netto=cena_netto,
                    wartosc_netto=wartosc_netto,
                    stawka_vat=stawka_vat,
                )
            )

        return pozycje

    def _get_text(self, parent, tag_path: str) -> str | None:
        """Get text from element by tag name or path."""
        if parent is None:
            return None

        # Handle nested paths like "Platnosc/FormaPlatnosci"
        if "/" in tag_path:
            parts = tag_path.split("/")
            current = parent
            for part in parts:
                current = current.find(f"{{{self.NAMESPACE}}}{part}")
                if current is None:
                    return None
            return current.text

        elem = parent.find(f"{{{self.NAMESPACE}}}{tag_path}")
        return elem.text if elem is not None else None
