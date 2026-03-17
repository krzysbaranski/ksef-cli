import json
from datetime import date

import click
from pydantic import ValidationError

from .generator import KSeFGenerator
from .models import Adres, Faktura, FakturaKSeF, Podmiot, PozycjaFaktury


def format_validation_errors(error: ValidationError) -> str:
    """Format Pydantic validation errors into readable messages."""
    messages = []
    for err in error.errors():
        location = " -> ".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        messages.append(f"  - {location}: {msg}")
    return "\n".join(messages)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """KSeF CLI - Generator faktur w formacie KSeF"""
    pass


@cli.command()
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True),
    help="Plik JSON z danymi faktury",
)
@click.option(
    "-o", "--output", "output_file", required=True, type=click.Path(), help="Plik wyjściowy XML"
)
def generate(input_file, output_file):
    """Generuje fakturę KSeF z pliku JSON"""
    try:
        # Wczytaj dane z JSON
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Konwersja dat
        if isinstance(data["faktura"]["data_wystawienia"], str):
            data["faktura"]["data_wystawienia"] = date.fromisoformat(
                data["faktura"]["data_wystawienia"]
            )
        if isinstance(data["faktura"]["data_sprzedazy"], str):
            data["faktura"]["data_sprzedazy"] = date.fromisoformat(
                data["faktura"]["data_sprzedazy"]
            )

        # Stwórz model
        faktura_ksef = FakturaKSeF(**data)

        # Generuj XML
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        # Zapisz do pliku
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml)

        click.echo(f"✓ Faktura wygenerowana: {output_file}")

    except json.JSONDecodeError as e:
        click.echo(f"✗ Błąd parsowania JSON w pliku '{input_file}':", err=True)
        click.echo(f"  Linia {e.lineno}, kolumna {e.colno}: {e.msg}", err=True)
        raise click.Abort()
    except ValidationError as e:
        click.echo("✗ Błąd walidacji danych faktury:", err=True)
        click.echo(format_validation_errors(e), err=True)
        raise click.Abort()
    except KeyError as e:
        click.echo(f"✗ Brak wymaganego pola w danych: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"✗ Błąd konwersji danych: {e}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"✗ Błąd zapisu pliku '{output_file}': {e.strerror}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Nieoczekiwany błąd: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


@cli.command()
def interactive():
    """Tryb interaktywny - generuje fakturę krok po kroku"""
    try:
        click.echo("=== Generator Faktur KSeF - Tryb Interaktywny ===\n")

        # Sprzedawca
        click.echo("DANE SPRZEDAWCY:")
        sprzedawca_nip = click.prompt("NIP")
        sprzedawca_nazwa = click.prompt("Nazwa")
        sprzedawca_adres_l1 = click.prompt("Adres (linia 1)")
        sprzedawca_adres_l2 = click.prompt("Adres (linia 2)", default="", show_default=False)

        # Nabywca
        click.echo("\nDANE NABYWCY:")
        nabywca_nip = click.prompt("NIP")
        nabywca_nazwa = click.prompt("Nazwa")
        nabywca_adres_l1 = click.prompt("Adres (linia 1)")

        # Faktura
        click.echo("\nDANE FAKTURY:")
        numer = click.prompt("Numer faktury")
        data_wyst = click.prompt("Data wystawienia (RRRR-MM-DD)", type=click.DateTime(["%Y-%m-%d"]))
        miejsce = click.prompt("Miejsce wystawienia")
        data_sprz = click.prompt("Data sprzedaży (RRRR-MM-DD)", type=click.DateTime(["%Y-%m-%d"]))

        # Pozycje
        pozycje: list[PozycjaFaktury] = []
        click.echo("\nPOZYCJE FAKTURY:")
        while True:
            nr_poz = len(pozycje) + 1
            click.echo(f"\nPozycja #{nr_poz}:")
            nazwa = click.prompt("Nazwa")
            jm = click.prompt("Jednostka miary", default="szt")
            ilosc = click.prompt("Ilość", type=float)
            cena = click.prompt("Cena netto", type=float)
            stawka = click.prompt("Stawka VAT (%)", type=int, default="23")

            wartosc_netto = round(ilosc * cena, 2)

            pozycje.append(
                PozycjaFaktury(
                    nr=nr_poz,
                    nazwa=nazwa,
                    jm=jm,
                    ilosc=ilosc,
                    cena_netto=cena,
                    wartosc_netto=wartosc_netto,
                    stawka_vat=stawka,
                )
            )

            if not click.confirm("Dodać kolejną pozycję?", default=False):
                break

        # Stopka faktury (opcjonalna)
        stopka_faktury_input = click.prompt(
            "\nStopka faktury (opcjonalnie, naciśnij Enter aby pominąć)",
            default="",
            show_default=False,
        )
        stopka_faktury = stopka_faktury_input if stopka_faktury_input else None

        # Stwórz model
        faktura_ksef = FakturaKSeF(
            sprzedawca=Podmiot(
                nip=sprzedawca_nip,
                nazwa=sprzedawca_nazwa,
                adres=Adres(
                    adres_l1=sprzedawca_adres_l1,
                    adres_l2=sprzedawca_adres_l2 if sprzedawca_adres_l2 else None,
                ),
            ),
            nabywca=Podmiot(
                nip=nabywca_nip, nazwa=nabywca_nazwa, adres=Adres(adres_l1=nabywca_adres_l1)
            ),
            faktura=Faktura(
                numer=numer,
                data_wystawienia=data_wyst.date(),
                miejsce_wystawienia=miejsce,
                data_sprzedazy=data_sprz.date(),
                pozycje=pozycje,
                stopka_faktury=stopka_faktury,
            ),
        )

        # Generuj XML
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        # Zapisz
        output_file = click.prompt("\nNazwa pliku wyjściowego", default=f"faktura_{numer}.xml")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml)

        click.echo(f"\n✓ Faktura wygenerowana: {output_file}")

    except ValidationError as e:
        click.echo("\n✗ Błąd walidacji danych faktury:", err=True)
        click.echo(format_validation_errors(e), err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"\n✗ Błąd zapisu pliku: {e.strerror}", err=True)
        raise click.Abort()
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"\n✗ Nieoczekiwany błąd: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "-f",
    "--file",
    "xml_file",
    required=True,
    type=click.Path(exists=True),
    help="Plik XML do walidacji",
)
@click.option(
    "--schema",
    "schema_path",
    type=click.Path(exists=True),
    help="Ścieżka do lokalnego pliku XSD schematu (opcjonalnie)",
)
def validate(xml_file, schema_path):
    """Waliduje plik XML faktury KSeF względem schematu FA-3"""
    try:
        from lxml import etree

        from .validator import KSeFValidator

        validator = KSeFValidator(schema_path=schema_path)

        with open(xml_file, encoding="utf-8") as f:
            xml_content = f.read()

        is_valid, errors = validator.validate_xml(xml_content)

        if is_valid:
            click.echo(f"✓ Plik {xml_file} jest poprawny")
            # Show warnings if any
            warnings = [e for e in errors if e.error_type == "warning"]
            for w in warnings:
                click.echo(f"  ⚠ {w.message}", err=True)
        else:
            click.echo(f"✗ Plik {xml_file} zawiera błędy:", err=True)
            for error in errors:
                click.echo(f"  {error}", err=True)
            raise click.Abort()

    except click.Abort:
        raise
    except etree.XMLSyntaxError as e:
        click.echo(f"✗ Błąd składni XML w pliku '{xml_file}':", err=True)
        click.echo(f"  Linia {e.lineno}: {e.msg}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"✗ Błąd odczytu pliku '{xml_file}': {e.strerror}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Błąd walidacji: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "-i",
    "--input",
    "xml_file",
    required=True,
    type=click.Path(exists=True),
    help="Plik XML faktury KSeF",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    required=True,
    type=click.Path(),
    help="Plik wyjściowy PDF",
)
def visualize(xml_file, output_file):
    """Generuje wizualizację PDF faktury KSeF z pliku XML"""
    try:
        from lxml import etree

        from .pdf_generator import KSeFPDFGenerator

        generator = KSeFPDFGenerator()
        generator.generuj_z_pliku(xml_file, output_file)

        click.echo(f"✓ Wizualizacja PDF wygenerowana: {output_file}")

    except etree.XMLSyntaxError as e:
        click.echo(f"✗ Błąd składni XML w pliku '{xml_file}':", err=True)
        click.echo(f"  Linia {e.lineno}: {e.msg}", err=True)
        raise click.Abort()
    except FileNotFoundError:
        click.echo(f"✗ Nie znaleziono pliku: {xml_file}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"✗ Błąd operacji na pliku: {e.strerror}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Błąd generowania PDF: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "-i",
    "--input",
    "xml_file",
    required=True,
    type=click.Path(exists=True),
    help="Plik XML faktury KSeF",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    required=True,
    type=click.Path(),
    help="Plik wyjściowy HTML",
)
def html(xml_file, output_file):
    """Generuje wizualizację HTML faktury KSeF z pliku XML"""
    try:
        from lxml import etree

        from .html_generator import KSeFHTMLGenerator

        generator = KSeFHTMLGenerator()
        html_content = generator.generuj_html_z_pliku(xml_file)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        click.echo(f"✓ Wizualizacja HTML wygenerowana: {output_file}")

    except etree.XMLSyntaxError as e:
        click.echo(f"✗ Błąd składni XML w pliku '{xml_file}':", err=True)
        click.echo(f"  Linia {e.lineno}: {e.msg}", err=True)
        raise click.Abort()
    except FileNotFoundError:
        click.echo(f"✗ Nie znaleziono pliku: {xml_file}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"✗ Błąd operacji na pliku: {e.strerror}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Błąd generowania HTML: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
