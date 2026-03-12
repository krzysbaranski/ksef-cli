from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class Adres(BaseModel):
    kod_kraju: str = Field(default="PL", max_length=2)
    adres_l1: str
    adres_l2: Optional[str] = None


class Podmiot(BaseModel):
    nip: str = Field(min_length=10, max_length=10)
    nazwa: str
    adres: Adres


class PozycjaFaktury(BaseModel):
    nr: int
    nazwa: str
    jm: str  # jednostka miary
    ilosc: float
    cena_netto: float
    wartosc_netto: float
    stawka_vat: int
    kwota_vat: Optional[float] = None

    def oblicz_vat(self):
        """Oblicza kwotę VAT"""
        if self.kwota_vat is None:
            self.kwota_vat = round(self.wartosc_netto * self.stawka_vat / 100, 2)
        return self.kwota_vat


class DodatkowyOpis(BaseModel):
    klucz: str
    wartosc: str


class Faktura(BaseModel):
    numer: str
    data_wystawienia: date
    miejsce_wystawienia: str
    data_sprzedazy: date
    waluta: str = Field(default="PLN", max_length=3)
    pozycje: List[PozycjaFaktury]
    forma_platnosci: str = "6"
    dodatkowe_opisy: Optional[List[DodatkowyOpis]] = None

    def oblicz_sumy(self):
        """Oblicza sumy netto i VAT"""
        suma_netto = sum(p.wartosc_netto for p in self.pozycje)
        suma_vat = sum(p.oblicz_vat() for p in self.pozycje)
        suma_brutto = suma_netto + suma_vat
        return {
            "netto": round(suma_netto, 2),
            "vat": round(suma_vat, 2),
            "brutto": round(suma_brutto, 2),
        }


class FakturaKSeF(BaseModel):
    sprzedawca: Podmiot
    nabywca: Podmiot
    faktura: Faktura
    prefiks_podatnika: str = "PL"
    system_info: str = "KSeF CLI Generator https://github.com/krzysbaranski/ksef-cli"
