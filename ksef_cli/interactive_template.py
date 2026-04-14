"""Interactive template-based invoice generation with rich TUI."""

from datetime import date, datetime
from typing import Optional

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import Adres, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury

console = Console()

STYLE = questionary.Style(
    [
        ("qmark", "fg:#00bfff bold"),
        ("question", "bold"),
        ("answer", "fg:#00bfff bold"),
        ("pointer", "fg:#00bfff bold"),
        ("highlighted", "fg:#00bfff bold"),
        ("selected", "fg:#00bfff"),
        ("separator", "fg:#6c6c6c"),
        ("instruction", "fg:#6c6c6c"),
    ]
)


def _validate_date(value: str) -> bool | str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return "Format daty: RRRR-MM-DD (np. 2026-04-15)"


def _validate_number(value: str) -> bool | str:
    try:
        float(value)
        return True
    except ValueError:
        return "Podaj liczbę (np. 1.5 lub 100)"


def _validate_int(value: str) -> bool | str:
    try:
        int(value)
        return True
    except ValueError:
        return "Podaj liczbę całkowitą"


def _validate_nip(value: str) -> bool | str:
    v = value.strip()
    if len(v) == 10 and v.isdigit():
        return True
    return "NIP musi mieć dokładnie 10 cyfr"


class InteractiveTemplate:
    """Rich TUI for template-based invoice generation."""

    def process_template(self, template: FakturaKSeF) -> FakturaKSeF:
        """Process template with user interactions."""
        console.print()
        console.print(
            Panel.fit(
                "[bold cyan]Generator Faktur KSeF[/bold cyan]\n[dim]Tryb szablonu — przejrzyj i edytuj dane[/dim]",
                border_style="cyan",
                padding=(0, 2),
            )
        )
        console.print()

        sprzedawca = self._process_podmiot("Dane Sprzedawcy", template.sprzedawca)
        console.print()
        nabywca = self._process_podmiot("Dane Nabywcy", template.nabywca)
        console.print()
        faktura = self._process_faktura_header(template.faktura)
        console.print()
        pozycje = self._process_pozycje(template.faktura.pozycje)
        console.print()
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

    def create_from_scratch(self) -> FakturaKSeF:
        """Create a new invoice from scratch using rich TUI."""
        console.print()
        console.print(
            Panel.fit(
                "[bold cyan]Generator Faktur KSeF[/bold cyan]\n[dim]Nowa faktura — wypełnij kolejne sekcje[/dim]",
                border_style="cyan",
                padding=(0, 2),
            )
        )
        console.print()

        # Seller
        console.print(Panel("[bold]Dane Sprzedawcy[/bold]", border_style="blue", expand=False))
        sprzedawca = self._collect_podmiot()
        console.print()

        # Buyer
        console.print(Panel("[bold]Dane Nabywcy[/bold]", border_style="blue", expand=False))
        nabywca = self._collect_podmiot()
        console.print()

        # Invoice header
        console.print(Panel("[bold]Dane Faktury[/bold]", border_style="blue", expand=False))
        today = date.today().isoformat()
        numer = questionary.text("Numer faktury:", style=STYLE).ask()
        data_wyst_str = questionary.text(
            "Data wystawienia (RRRR-MM-DD):", default=today, validate=_validate_date, style=STYLE
        ).ask()
        miejsce = questionary.text("Miejsce wystawienia:", style=STYLE).ask()
        data_sprz_str = questionary.text(
            "Data sprzedaży (RRRR-MM-DD):", default=today, validate=_validate_date, style=STYLE
        ).ask()
        waluta = questionary.text("Kod waluty:", default="PLN", style=STYLE).ask()
        console.print()

        # Line items
        console.print(Panel("[bold]Pozycje Faktury[/bold]", border_style="blue", expand=False))
        pozycje: list[PozycjaFaktury] = []
        nr = 1
        while True:
            console.print(f"\n  [bold cyan]Pozycja #{nr}[/bold cyan]")
            poz = self._new_pozycja(nr)
            pozycje.append(poz)
            nr += 1
            if not questionary.confirm("Dodać kolejną pozycję?", default=False, style=STYLE).ask():
                break

        self._show_pozycje_table(pozycje)
        console.print()

        # Footer
        stopka_str = questionary.text(
            "Stopka faktury (opcjonalnie, Enter aby pominąć):", style=STYLE
        ).ask()
        stopka = stopka_str.strip() if stopka_str else None

        return FakturaKSeF(
            sprzedawca=sprzedawca,
            nabywca=nabywca,
            faktura=Faktura(
                numer=numer,
                data_wystawienia=datetime.strptime(data_wyst_str, "%Y-%m-%d").date(),
                miejsce_wystawienia=miejsce,
                data_sprzedazy=datetime.strptime(data_sprz_str, "%Y-%m-%d").date(),
                waluta=waluta,
                pozycje=pozycje,
                stopka_faktury=stopka,
            ),
        )

    def _collect_podmiot(self) -> Podmiot:
        """Collect subject data interactively."""
        nip = questionary.text("NIP (10 cyfr):", validate=_validate_nip, style=STYLE).ask()
        nazwa = questionary.text("Nazwa firmy:", style=STYLE).ask()
        adres_l1 = questionary.text("Adres (linia 1):", style=STYLE).ask()
        adres_l2 = questionary.text(
            "Adres (linia 2, opcjonalnie, Enter aby pominąć):", style=STYLE
        ).ask()
        return Podmiot(
            nip=nip.strip(),
            nazwa=nazwa,
            adres=Adres(
                adres_l1=adres_l1,
                adres_l2=adres_l2.strip() if adres_l2 and adres_l2.strip() else None,
            ),
        )

    def _show_podmiot_panel(self, title: str, podmiot: Podmiot) -> None:
        """Display subject information in a rich panel."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Pole", style="dim", min_width=12)
        table.add_column("Wartość", style="bold")
        table.add_row("NIP", podmiot.nip)
        table.add_row("Nazwa", podmiot.nazwa)
        table.add_row("Adres", podmiot.adres.adres_l1)
        if podmiot.adres.adres_l2:
            table.add_row("", podmiot.adres.adres_l2)
        console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="blue"))

    def _process_podmiot(self, title: str, podmiot: Podmiot) -> Podmiot:
        """Process subject with rich UI."""
        self._show_podmiot_panel(title, podmiot)

        keep = questionary.confirm("Zachować dane z szablonu?", default=True, style=STYLE).ask()
        if not keep:
            nip = questionary.text(
                "NIP (10 cyfr):", default=podmiot.nip, validate=_validate_nip, style=STYLE
            ).ask()
            nazwa = questionary.text("Nazwa firmy:", default=podmiot.nazwa, style=STYLE).ask()
            adres_l1 = questionary.text(
                "Adres (linia 1):", default=podmiot.adres.adres_l1, style=STYLE
            ).ask()
            adres_l2_default = podmiot.adres.adres_l2 or ""
            adres_l2 = questionary.text(
                "Adres (linia 2, opcjonalnie):", default=adres_l2_default, style=STYLE
            ).ask()
            return Podmiot(
                nip=nip.strip(),
                nazwa=nazwa,
                adres=Adres(
                    adres_l1=adres_l1,
                    adres_l2=adres_l2.strip() if adres_l2 and adres_l2.strip() else None,
                ),
            )
        return podmiot

    # Keep old name for backward compatibility with tests
    def _show_podmiot(self, podmiot: Podmiot) -> None:
        """Display subject information (legacy helper)."""
        self._show_podmiot_panel("", podmiot)

    def _process_faktura_header(self, faktura: Faktura) -> dict:
        """Process invoice header with rich UI."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Pole", style="dim", min_width=18)
        table.add_column("Wartość", style="bold")
        table.add_row("Numer", faktura.numer)
        table.add_row("Data wystawienia", str(faktura.data_wystawienia))
        table.add_row("Miejsce wystawienia", faktura.miejsce_wystawienia)
        table.add_row("Data sprzedaży", str(faktura.data_sprzedazy))
        table.add_row("Waluta", faktura.waluta)
        console.print(Panel(table, title="[bold]Dane Faktury[/bold]", border_style="blue"))

        keep = questionary.confirm(
            "Zachować dane faktury z szablonu?", default=True, style=STYLE
        ).ask()
        if not keep:
            numer = questionary.text("Numer faktury:", default=faktura.numer, style=STYLE).ask()
            data_wyst_str = questionary.text(
                "Data wystawienia (RRRR-MM-DD):",
                default=faktura.data_wystawienia.isoformat(),
                validate=_validate_date,
                style=STYLE,
            ).ask()
            miejsce = questionary.text(
                "Miejsce wystawienia:", default=faktura.miejsce_wystawienia, style=STYLE
            ).ask()
            data_sprz_str = questionary.text(
                "Data sprzedaży (RRRR-MM-DD):",
                default=faktura.data_sprzedazy.isoformat(),
                validate=_validate_date,
                style=STYLE,
            ).ask()
            waluta = questionary.text("Kod waluty:", default=faktura.waluta, style=STYLE).ask()
            return {
                "numer": numer,
                "data_wystawienia": datetime.strptime(data_wyst_str, "%Y-%m-%d").date(),
                "miejsce_wystawienia": miejsce,
                "data_sprzedazy": datetime.strptime(data_sprz_str, "%Y-%m-%d").date(),
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

    def _show_pozycje_table(self, pozycje: list[PozycjaFaktury]) -> None:
        """Display line items in a rich table."""
        total_netto = sum(p.wartosc_netto for p in pozycje)
        total_vat = sum(round(p.wartosc_netto * p.stawka_vat / 100, 2) for p in pozycje)
        total_brutto = round(total_netto + total_vat, 2)

        table = Table(
            box=box.ROUNDED,
            show_footer=True,
            footer_style="bold",
        )
        table.add_column("Nr", justify="right", style="dim", footer="")
        table.add_column("Nazwa", footer="[bold]Suma[/bold]")
        table.add_column("J.m.", justify="center", footer="")
        table.add_column("Ilość", justify="right", footer="")
        table.add_column("Cena netto", justify="right", footer="")
        table.add_column(
            "Wartość netto", justify="right", footer=f"[bold]{total_netto:.2f}[/bold]"
        )
        table.add_column(
            "VAT%",
            justify="center",
            footer=f"[dim]+{total_vat:.2f} VAT → [bold]{total_brutto:.2f} brutto[/bold][/dim]",
        )

        for p in pozycje:
            table.add_row(
                str(p.nr),
                p.nazwa,
                p.jm,
                f"{p.ilosc:g}",
                f"{p.cena_netto:.2f}",
                f"{p.wartosc_netto:.2f}",
                f"{p.stawka_vat}%",
            )

        console.print(Panel(table, title="[bold]Pozycje Faktury[/bold]", border_style="blue"))

    # Keep old name for backward compatibility with tests
    def _show_pozycja(self, pozycja: PozycjaFaktury) -> None:
        """Display single line item (legacy helper)."""
        self._show_pozycje_table([pozycja])

    def _process_pozycje(self, pozycje: list[PozycjaFaktury]) -> list[PozycjaFaktury]:
        """Process line items with rich UI."""
        self._show_pozycje_table(pozycje)
        console.print()

        new_pozycje: list[PozycjaFaktury] = []
        nr = 1

        for poz in pozycje:
            console.print(
                f"  [bold]Pozycja #{poz.nr}[/bold] — [cyan]{poz.nazwa}[/cyan]"
                f"  [dim]{poz.ilosc:g} {poz.jm} × {poz.cena_netto:.2f} = {poz.wartosc_netto:.2f} PLN + {poz.stawka_vat}% VAT[/dim]"
            )
            action = questionary.select(
                "Co zrobić z tą pozycją?",
                choices=[
                    questionary.Choice("  Zachować", "k"),
                    questionary.Choice("  Edytować", "e"),
                    questionary.Choice("  Usunąć", "u"),
                ],
                style=STYLE,
            ).ask()

            if action == "k":
                new_pozycje.append(
                    PozycjaFaktury(
                        nr=nr,
                        nazwa=poz.nazwa,
                        jm=poz.jm,
                        ilosc=poz.ilosc,
                        cena_netto=poz.cena_netto,
                        wartosc_netto=poz.wartosc_netto,
                        stawka_vat=poz.stawka_vat,
                    )
                )
                nr += 1
            elif action == "e":
                new_pozycje.append(self._edit_pozycja(nr, poz))
                nr += 1
            # "u" = delete, skip

        while questionary.confirm("Dodać nową pozycję?", default=False, style=STYLE).ask():
            console.print(f"\n  [bold cyan]Nowa pozycja #{nr}[/bold cyan]")
            new_pozycje.append(self._new_pozycja(nr))
            nr += 1

        return new_pozycje

    def _edit_pozycja(self, nr: int, poz: PozycjaFaktury) -> PozycjaFaktury:
        """Edit an existing line item."""
        console.print()
        nazwa = questionary.text("Nazwa:", default=poz.nazwa, style=STYLE).ask()
        jm = questionary.text("Jednostka miary:", default=poz.jm, style=STYLE).ask()
        ilosc_str = questionary.text(
            "Ilość:", default=str(poz.ilosc), validate=_validate_number, style=STYLE
        ).ask()
        cena_str = questionary.text(
            "Cena netto:", default=str(poz.cena_netto), validate=_validate_number, style=STYLE
        ).ask()
        stawka_str = questionary.text(
            "Stawka VAT (%):", default=str(poz.stawka_vat), validate=_validate_int, style=STYLE
        ).ask()

        ilosc = float(ilosc_str)
        cena = float(cena_str)
        stawka = int(stawka_str)
        wartosc_netto = round(ilosc * cena, 2)

        console.print(
            f"  [dim]→ Wartość netto: {wartosc_netto:.2f} PLN + {stawka}% VAT = {wartosc_netto * (1 + stawka/100):.2f} PLN brutto[/dim]"
        )
        return PozycjaFaktury(
            nr=nr,
            nazwa=nazwa,
            jm=jm,
            ilosc=ilosc,
            cena_netto=cena,
            wartosc_netto=wartosc_netto,
            stawka_vat=stawka,
        )

    def _new_pozycja(self, nr: int) -> PozycjaFaktury:
        """Collect data for a new line item."""
        nazwa = questionary.text("Nazwa:", style=STYLE).ask()
        jm = questionary.text("Jednostka miary:", default="szt", style=STYLE).ask()
        ilosc_str = questionary.text("Ilość:", validate=_validate_number, style=STYLE).ask()
        cena_str = questionary.text("Cena netto:", validate=_validate_number, style=STYLE).ask()
        stawka_str = questionary.text(
            "Stawka VAT (%):", default="23", validate=_validate_int, style=STYLE
        ).ask()

        ilosc = float(ilosc_str)
        cena = float(cena_str)
        stawka = int(stawka_str)
        wartosc_netto = round(ilosc * cena, 2)

        console.print(
            f"  [dim]→ Wartość netto: {wartosc_netto:.2f} PLN + {stawka}% VAT = {wartosc_netto * (1 + stawka/100):.2f} PLN brutto[/dim]"
        )
        return PozycjaFaktury(
            nr=nr,
            nazwa=nazwa,
            jm=jm,
            ilosc=ilosc,
            cena_netto=cena,
            wartosc_netto=wartosc_netto,
            stawka_vat=stawka,
        )

    def _process_stopka(self, stopka: Optional[str]) -> Optional[str]:
        """Process invoice footer."""
        if stopka:
            console.print(
                Panel(
                    f"[italic]{stopka}[/italic]",
                    title="[bold]Stopka Faktury[/bold]",
                    border_style="blue",
                )
            )
            keep = questionary.confirm(
                "Zachować stopkę z szablonu?", default=True, style=STYLE
            ).ask()
            if keep:
                return stopka

        new_stopka = questionary.text(
            "Stopka faktury (opcjonalnie, Enter aby pominąć):", style=STYLE
        ).ask()
        return new_stopka.strip() if new_stopka and new_stopka.strip() else None
