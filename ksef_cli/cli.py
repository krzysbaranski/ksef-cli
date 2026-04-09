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
def interactive():
    """Tryb interaktywny - generuje fakturę z szablonu lub od zera"""
    try:
        from .interactive_template import InteractiveTemplate
        from .template_loader import TemplateLoader

        # Ask about template
        use_template = click.confirm("Czy masz plik szablonu faktury?", default=False)

        if use_template:
            # Load template from XML
            template_file = click.prompt("Ścieżka do pliku szablonu (XML)")

            try:
                loader = TemplateLoader()
                template = loader.load_from_xml(template_file)
                click.echo(f"✓ Szablon załadowany z: {template_file}\n")

                # Process template with user interactions
                processor = InteractiveTemplate()
                faktura_ksef = processor.process_template(template)

            except FileNotFoundError as e:
                click.echo(f"✗ {e}", err=True)
                raise click.Abort()
            except ValueError as e:
                click.echo(f"✗ Błąd ładowania szablonu: {e}", err=True)
                raise click.Abort()

        else:
            # Original interactive mode - create from scratch
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
            data_wyst = click.prompt(
                "Data wystawienia (RRRR-MM-DD)", type=click.DateTime(["%Y-%m-%d"])
            )
            miejsce = click.prompt("Miejsce wystawienia")
            data_sprz = click.prompt(
                "Data sprzedaży (RRRR-MM-DD)", type=click.DateTime(["%Y-%m-%d"])
            )

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
                    nip=nabywca_nip,
                    nazwa=nabywca_nazwa,
                    adres=Adres(adres_l1=nabywca_adres_l1),
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
        numer = faktura_ksef.faktura.numer
        output_file = click.prompt("\nNazwa pliku wyjściowego", default=f"faktura_{numer}.xml")

        # Create directory if it doesn't exist
        import os

        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(xml)

        click.echo(f"\n✓ Faktura wygenerowana: {output_file}")

        # Offer visualization
        if click.confirm("\nCzy chcesz wygenerować wizualizację PDF?", default=True):
            pdf_file = click.prompt("Nazwa pliku PDF", default=output_file.replace(".xml", ".pdf"))
            try:
                from .pdf_generator import KSeFPDFGenerator

                pdf_gen = KSeFPDFGenerator()
                pdf_gen.generuj_z_pliku(output_file, pdf_file)
                click.echo(f"✓ Wizualizacja PDF: {pdf_file}")
            except Exception as e:
                click.echo(f"⚠ Nie udało się wygenerować PDF: {e}", err=True)

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
@click.option(
    "-k",
    "--ksef-number",
    "numer_ksef",
    default=None,
    help="Numer KSeF faktury (do wygenerowania kodu QR weryfikacji)",
)
def visualize(xml_file, output_file, numer_ksef):
    """Generuje wizualizację PDF faktury KSeF z pliku XML"""
    try:
        from lxml import etree

        from .pdf_generator import KSeFPDFGenerator

        generator = KSeFPDFGenerator()
        generator.generuj_z_pliku(xml_file, output_file, numer_ksef)

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
@click.option(
    "-k",
    "--ksef-number",
    "numer_ksef",
    default=None,
    help="Numer KSeF faktury (do wygenerowania kodu QR weryfikacji)",
)
def html(xml_file, output_file, numer_ksef):
    """Generuje wizualizację HTML faktury KSeF z pliku XML"""
    try:
        from lxml import etree

        from .html_generator import KSeFHTMLGenerator

        generator = KSeFHTMLGenerator()
        html_content = generator.generuj_html_z_pliku(xml_file, numer_ksef)

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


@cli.command("list-invoices")
@click.option(
    "-n",
    "--nip",
    required=True,
    help="NIP firmy (10 cyfr)",
)
@click.option(
    "-t",
    "--token",
    required=True,
    help="Token autoryzacyjny KSeF",
)
@click.option(
    "--date-from",
    "date_from",
    required=True,
    help="Data początkowa (ISO-8601, np. 2023-01-01T00:00:00.000Z)",
)
@click.option(
    "--date-to",
    "date_to",
    required=True,
    help="Data końcowa (ISO-8601, np. 2023-12-31T23:59:59.999Z)",
)
@click.option(
    "--test",
    "use_test_env",
    is_flag=True,
    default=False,
    help="Użyj środowiska testowego KSeF",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    default=None,
    type=click.Path(),
    help="Plik wyjściowy JSON (domyślnie: wyświetla na ekranie)",
)
@click.option(
    "--subject-type",
    "subject_type",
    default="Subject1",
    type=click.Choice(
        ["Subject1", "Subject2", "Subject3", "SubjectAuthorized"], case_sensitive=True
    ),
    help="Typ podmiotu (Subject1=sprzedawca, Subject2=nabywca, Subject3, SubjectAuthorized)",
)
@click.option(
    "--date-type",
    "date_type",
    default="PermanentStorage",
    type=click.Choice(["Issue", "Invoicing", "PermanentStorage"], case_sensitive=True),
    help="Typ daty do filtrowania (Issue=wystawienia, Invoicing=przyjęcia, PermanentStorage=zapisu)",
)
@click.option(
    "--invoicing-mode",
    "invoicing_mode",
    default=None,
    help="Tryb fakturowania (np. Online, Offline)",
)
@click.option(
    "--form-type",
    "form_type",
    default=None,
    help="Typ formularza (np. FA, FVAt, RO, ZO)",
)
@click.option(
    "--amount-type",
    "amount_type",
    default=None,
    type=click.Choice(["Netto", "Brutto"], case_sensitive=True),
    help="Typ kwoty do filtrowania (Netto=netto, Brutto=brutto)",
)
@click.option(
    "--amount-from",
    "amount_from",
    default=None,
    type=float,
    help="Minimalna kwota",
)
@click.option(
    "--amount-to",
    "amount_to",
    default=None,
    type=float,
    help="Maksymalna kwota",
)
@click.option(
    "--currency",
    "currencies",
    multiple=True,
    help="Kody walut (np. PLN, EUR, USD). Można podać wiele razy.",
)
@click.option(
    "--invoice-type",
    "invoice_types",
    multiple=True,
    help="Typy faktur (np. Vat, Margin, etc.). Można podać wiele razy.",
)
@click.option(
    "--has-attachment",
    "has_attachment",
    is_flag=True,
    default=False,
    help="Tylko faktury z załącznikami",
)
@click.option(
    "--page-offset",
    "page_offset",
    default=0,
    type=int,
    help="Numer strony (offset) - domyślnie 0",
)
@click.option(
    "--page-size",
    "page_size",
    default=100,
    type=int,
    help="Rozmiar strony (liczba wyników) - domyślnie 100",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Włącz tryb debug (wyświetl URL, request i response)",
)
def list_invoices(
    nip,
    token,
    date_from,
    date_to,
    use_test_env,
    output_file,
    subject_type,
    date_type,
    invoicing_mode,
    form_type,
    amount_type,
    amount_from,
    amount_to,
    currencies,
    invoice_types,
    has_attachment,
    page_offset,
    page_size,
    debug,
):
    """Pobiera listę faktur z API KSeF (autoryzacja tokenem)"""
    from .ksef_api import KSeFAPIError, KSeFAuthError, KSeFClient

    try:
        client = KSeFClient(nip=nip, token=token, test=use_test_env, debug=debug)
        invoices = client.list_invoices(
            date_from=date_from,
            date_to=date_to,
            subject_type=subject_type,
            date_type=date_type,
            invoicing_mode=invoicing_mode,
            form_type=form_type,
            amount_type=amount_type,
            amount_from=amount_from,
            amount_to=amount_to,
            currencies=list(currencies) if currencies else None,
            invoice_types=list(invoice_types) if invoice_types else None,
            has_attachment=has_attachment,
            page_offset=page_offset,
            page_size=page_size,
        )

        result = json.dumps(invoices, ensure_ascii=False, indent=2)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)
            click.echo(f"✓ Lista faktur zapisana do: {output_file} ({len(invoices)} faktur)")
        else:
            click.echo(result)
            click.echo(f"\n✓ Pobrano {len(invoices)} faktur", err=True)

    except KSeFAuthError as e:
        click.echo(f"✗ Błąd autoryzacji KSeF: {e}", err=True)
        raise click.Abort()
    except KSeFAPIError as e:
        click.echo(f"✗ Błąd API KSeF: {e}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"✗ Błąd zapisu pliku '{output_file}': {e.strerror}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Nieoczekiwany błąd: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


@cli.command("get-invoice")
@click.option(
    "-n",
    "--nip",
    required=True,
    type=str,
    help="NIP podmiotu (10 cyfr)",
)
@click.option(
    "-t",
    "--token",
    required=True,
    type=str,
    help="Token autoryzacyjny z portalu KSeF",
)
@click.option(
    "-k",
    "--ksef-number",
    "ksef_number",
    required=True,
    type=str,
    help="Numer KSeF faktury (35-36 znaków)",
)
@click.option(
    "--test",
    "use_test_env",
    is_flag=True,
    default=False,
    help="Użyj testowego środowiska KSeF",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    type=click.Path(),
    default=None,
    help="Zapisz wynik do pliku XML (domyślnie: stdout)",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Włącz tryb debug (wyświetl URL, request i response)",
)
def get_invoice(nip, token, ksef_number, use_test_env, output_file, debug):
    """Pobiera konkretną fakturę z API KSeF po numerze KSeF (XML)"""
    from .ksef_api import KSeFAPIError, KSeFAuthError, KSeFClient

    try:
        client = KSeFClient(nip=nip, token=token, test=use_test_env, debug=debug)
        invoice_xml = client.get_invoice(ksef_number=ksef_number)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(invoice_xml)
            click.echo(f"✓ Faktura zapisana do: {output_file}")
        else:
            click.echo(invoice_xml)

    except KSeFAuthError as e:
        click.echo(f"✗ Błąd autoryzacji KSeF: {e}", err=True)
        raise click.Abort()
    except KSeFAPIError as e:
        click.echo(f"✗ Błąd API KSeF: {e}", err=True)
        raise click.Abort()
    except OSError as e:
        click.echo(f"✗ Błąd zapisu pliku '{output_file}': {e.strerror}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"✗ Nieoczekiwany błąd: {type(e).__name__}: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
