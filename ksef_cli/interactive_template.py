"""Interactive template-based invoice generation."""

import click
from datetime import date

from .models import Adres, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury


class InteractiveTemplate:
    """Conversational interface for template-based invoice generation."""

    def process_template(self, template: FakturaKSeF) -> FakturaKSeF:
        """Process template with user interactions."""
        click.echo("\n=== Generator Faktur KSeF - Tryb szablonu ===\n")

        # Process seller
        sprzedawca = self._process_podmiot(
            "DANE SPRZEDAWCY", template.sprzedawca, is_seller=True
        )

        # Process buyer
        nabywca = self._process_podmiot(
            "DANE NABYWCY", template.nabywca, is_seller=False
        )

        # Process invoice header
        faktura = self._process_faktura_header(template.faktura)

        # Process line items
        pozycje = self._process_pozycje(template.faktura.pozycje)

        # Process footer
        stopka = self._process_stopka(template.faktura.stopka_faktury)

        return FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=Faktura(
                numer=faktura["numer"],
                data_wystawienia=faktura["data_wystawienia"],
                miejsce_wystawienia=faktura["miejsce_wystawienia"],
                data_sprzedazy=faktura["data_sprzedazy"],
                waluta=faktura["waluta"],
                pozycje=pozycje,
                forma_platnosci=faktura["forma_platnosci"],
                stopka_faktury=stopka,
            ),
        )

    def _process_podmiot(
        self, title: str, podmiot: Podmiot, is_seller: bool = False
    ) -> Podmiot:
        """Process subject (seller/buyer) with template."""
        click.echo(f"{title}:")
        self._show_podmiot(podmiot)

        if not click.confirm("Zachować dane z szablonu?", default=True):
            # Edit mode
            nip = click.prompt("NIP")
            nazwa = click.prompt("Nazwa")
            adres_l1 = click.prompt("Adres (linia 1)")
            adres_l2 = click.prompt(
                "Adres (linia 2)", default="", show_default=False
            )

            return Podmiot(
                nip=nip,
                nazwa=nazwa,
                adres=Adres(
                    adres_l1=adres_l1,
                    adres_l2=adres_l2 if adres_l2 else None,
                ),
            )

        return podmiot

    def _show_podmiot(self, podmiot: Podmiot):
        """Display subject information."""
        click.echo(f"  NIP: {podmiot.nip}")
        click.echo(f"  Nazwa: {podmiot.nazwa}")
        click.echo(f"  Adres: {podmiot.adres.adres_l1}")
        if podmiot.adres.adres_l2:
            click.echo(f"         {podmiot.adres.adres_l2}")
        click.echo()

    def _process_faktura_header(self, faktura: Faktura) -> dict:
        """Process invoice header fields."""
        click.echo("DANE FAKTURY:")
        click.echo(f"  Numer: {faktura.numer}")
        click.echo(f"  Data wystawienia: {faktura.data_wystawienia}")
        click.echo(f"  Miejsce: {faktura.miejsce_wystawienia}")
        click.echo(f"  Data sprzedaży: {faktura.data_sprzedazy}")
        click.echo(f"  Waluta: {faktura.waluta}")
        click.echo()

        if not click.confirm("Zachować dane faktury z szablonu?", default=True):
            numer = click.prompt("Numer faktury", default=faktura.numer)
            data_wyst = click.prompt(
                "Data wystawienia (RRRR-MM-DD)",
                type=click.DateTime(["%Y-%m-%d"]),
                default=faktura.data_wystawienia.isoformat(),
            )
            miejsce = click.prompt(
                "Miejsce wystawienia", default=faktura.miejsce_wystawienia
            )
            data_sprz = click.prompt(
                "Data sprzedaży (RRRR-MM-DD)",
                type=click.DateTime(["%Y-%m-%d"]),
                default=faktura.data_sprzedazy.isoformat(),
            )
            waluta = click.prompt("Kod waluty", default=faktura.waluta)

            return {
                "numer": numer,
                "data_wystawienia": data_wyst.date(),
                "miejsce_wystawienia": miejsce,
                "data_sprzedazy": data_sprz.date(),
                "waluta": waluta,
                "forma_platnosci": faktura.forma_platnosci,
            }

        return {
            "numer": faktura.numer,
            "data_wystawienia": faktura.data_wystawienia,
            "miejsce_wystawienia": faktura.miejsce_wystawienia,
            "data_sprzedazy": faktura.data_sprzedazy,
            "waluta": faktura.waluta,
            "forma_platnosci": faktura.forma_platnosci,
        }

    def _process_pozycje(self, pozycje: list[PozycjaFaktury]) -> list[PozycjaFaktury]:
        """Process line items with keep/edit/delete options."""
        click.echo(f"POZYCJE FAKTURY ({len(pozycje)} pozycji w szablonie):")
        click.echo()

        new_pozycje = []
        nr = 1

        for poz in pozycje:
            click.echo(f"Pozycja #{nr}:")
            self._show_pozycja(poz)

            click.echo("  k=Zachować, e=Edytować, u=Usunąć")
            action = click.prompt(
                "Opcja",
                type=click.Choice(["k", "e", "u"], case_sensitive=False),
                show_choices=True,
            )

            if action.lower() == "k":
                # Keep with new number
                new_poz = PozycjaFaktury(
                    nr=nr,
                    nazwa=poz.nazwa,
                    jm=poz.jm,
                    ilosc=poz.ilosc,
                    cena_netto=poz.cena_netto,
                    wartosc_netto=poz.wartosc_netto,
                    stawka_vat=poz.stawka_vat,
                )
                new_pozycje.append(new_poz)
                nr += 1

            elif action.lower() == "e":
                # Edit
                click.echo()
                nazwa = click.prompt("Nazwa", default=poz.nazwa)
                jm = click.prompt("Jednostka miary", default=poz.jm)
                ilosc = click.prompt("Ilość", type=float, default=poz.ilosc)
                cena = click.prompt("Cena netto", type=float, default=poz.cena_netto)
                stawka = click.prompt(
                    "Stawka VAT (%)", type=int, default=poz.stawka_vat
                )

                wartosc_netto = round(ilosc * cena, 2)

                new_poz = PozycjaFaktury(
                    nr=nr,
                    nazwa=nazwa,
                    jm=jm,
                    ilosc=ilosc,
                    cena_netto=cena,
                    wartosc_netto=wartosc_netto,
                    stawka_vat=stawka,
                )
                new_pozycje.append(new_poz)
                nr += 1

            # elif action.lower() == "u": skip (delete)

            click.echo()

        # Add new line items
        while click.confirm("Dodać nową pozycję?", default=False):
            click.echo(f"\nPozycja #{nr}:")
            nazwa = click.prompt("Nazwa")
            jm = click.prompt("Jednostka miary", default="szt")
            ilosc = click.prompt("Ilość", type=float)
            cena = click.prompt("Cena netto", type=float)
            stawka = click.prompt("Stawka VAT (%)", type=int, default="23")

            wartosc_netto = round(ilosc * cena, 2)

            new_pozycje.append(
                PozycjaFaktury(
                    nr=nr,
                    nazwa=nazwa,
                    jm=jm,
                    ilosc=ilosc,
                    cena_netto=cena,
                    wartosc_netto=wartosc_netto,
                    stawka_vat=stawka,
                )
            )
            nr += 1

        return new_pozycje

    def _show_pozycja(self, pozycja: PozycjaFaktury):
        """Display line item information."""
        click.echo(f"  Nazwa: {pozycja.nazwa}")
        click.echo(f"  Jednostka: {pozycja.jm}, Ilość: {pozycja.ilosc}")
        click.echo(
            f"  Cena: {pozycja.cena_netto} PLN netto, Wartość: {pozycja.wartosc_netto} PLN"
        )
        click.echo(f"  VAT: {pozycja.stawka_vat}%")
        click.echo()

    def _process_stopka(self, stopka: str | None) -> str | None:
        """Process invoice footer."""
        if stopka:
            click.echo("STOPKA FAKTURY:")
            click.echo(f"  {stopka}")
            click.echo()

            if click.confirm("Zachować stopkę z szablonu?", default=True):
                return stopka

            stopka_input = self._prompt_multiline(
                "Nowa stopka (Enter aby pominąć, Ctrl+D aby zakończyć)"
            )
            return stopka_input if stopka_input else None

        stopka_input = self._prompt_multiline(
            "Stopka faktury (opcjonalnie, Ctrl+D aby zakończyć)"
        )
        return stopka_input if stopka_input else None

    def _prompt_multiline(self, prompt_text: str) -> str | None:
        """Prompt for multiline input (lines separated by Enter, end with Ctrl+D)."""
        click.echo(prompt_text)
        lines = []
        try:
            while True:
                line = click.prompt("", default="", show_default=False)
                if line:
                    lines.append(line)
                elif lines:
                    # Empty line after content - ask if done
                    if click.confirm("Zakończyć edycję?", default=True):
                        break
                else:
                    # Empty line at start - skip
                    pass
        except EOFError:
            # Ctrl+D pressed
            pass

        return "\n".join(lines) if lines else None
