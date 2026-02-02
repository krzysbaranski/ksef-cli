import click
import json
from pathlib import Path
from datetime import date
from .models import FakturaKSeF, Podmiot, Adres, Faktura, PozycjaFaktury, DodatkowyOpis
from .generator import KSeFGenerator


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """KSeF CLI - Generator faktur w formacie KSeF"""
    pass


@cli.command()
@click.option('-i', '--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Plik JSON z danymi faktury')
@click.option('-o', '--output', 'output_file', required=True, type=click.Path(),
              help='Plik wyjściowy XML')
def generate(input_file, output_file):
    """Generuje fakturę KSeF z pliku JSON"""
    try:
        # Wczytaj dane z JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Konwersja dat
        if isinstance(data['faktura']['data_wystawienia'], str):
            data['faktura']['data_wystawienia'] = date.fromisoformat(
                data['faktura']['data_wystawienia']
            )
        if isinstance(data['faktura']['data_sprzedazy'], str):
            data['faktura']['data_sprzedazy'] = date.fromisoformat(
                data['faktura']['data_sprzedazy']
            )

        # Stwórz model
        faktura_ksef = FakturaKSeF(**data)

        # Generuj XML
        generator = KSeFGenerator()
        xml = generator.generuj(faktura_ksef)

        # Zapisz do pliku
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml)

        click.echo(f"✓ Faktura wygenerowana: {output_file}")

    except Exception as e:
        click.echo(f"✗ Błąd: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
def interactive():
    """Tryb interaktywny - generuje fakturę krok po kroku"""
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
    data_wyst = click.prompt("Data wystawienia (RRRR-MM-DD)", type=click.DateTime(['%Y-%m-%d']))
    miejsce = click.prompt("Miejsce wystawienia")
    data_sprz = click.prompt("Data sprzedaży (RRRR-MM-DD)", type=click.DateTime(['%Y-%m-%d']))

    # Pozycje
    pozycje = []
    click.echo("\nPOZYCJE FAKTURY:")
    while True:
        nr_poz = len(pozycje) + 1
        click.echo(f"\nPozycja #{nr_poz}:")
        nazwa = click.prompt("Nazwa")
        jm = click.prompt("Jednostka miary", default="szt")
        ilosc = click.prompt("Ilość", type=float)
        cena = click.prompt("Cena netto", type=float)
        stawka = click.prompt("Stawka VAT (%)", type=int, default=23)

        wartosc_netto = round(ilosc * cena, 2)

        pozycje.append(PozycjaFaktury(
            nr=nr_poz,
            nazwa=nazwa,
            jm=jm,
            ilosc=ilosc,
            cena_netto=cena,
            wartosc_netto=wartosc_netto,
            stawka_vat=stawka
        ))

        if not click.confirm("Dodać kolejną pozycję?", default=False):
            break

    # Stwórz model
    faktura_ksef = FakturaKSeF(
        sprzedawca=Podmiot(
            nip=sprzedawca_nip,
            nazwa=sprzedawca_nazwa,
            adres=Adres(
                adres_l1=sprzedawca_adres_l1,
                adres_l2=sprzedawca_adres_l2 if sprzedawca_adres_l2 else None
            )
        ),
        nabywca=Podmiot(
            nip=nabywca_nip,
            nazwa=nabywca_nazwa,
            adres=Adres(adres_l1=nabywca_adres_l1)
        ),
        faktura=Faktura(
            numer=numer,
            data_wystawienia=data_wyst.date(),
            miejsce_wystawienia=miejsce,
            data_sprzedazy=data_sprz.date(),
            pozycje=pozycje
        )
    )

    # Generuj XML
    generator = KSeFGenerator()
    xml = generator.generuj(faktura_ksef)

    # Zapisz
    output_file = click.prompt("\nNazwa pliku wyjściowego", default=f"faktura_{numer}.xml")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml)

    click.echo(f"\n✓ Faktura wygenerowana: {output_file}")


@cli.command()
@click.option('-f', '--file', 'xml_file', required=True, type=click.Path(exists=True),
              help='Plik XML do walidacji')
def validate(xml_file):
    """Waliduje plik XML faktury KSeF"""
    try:
        from lxml import etree

        with open(xml_file, 'rb') as f:
            doc = etree.parse(f)

        click.echo(f"✓ Plik {xml_file} jest poprawnym XML")
        click.echo(f"  Element główny: {doc.getroot().tag}")

    except Exception as e:
        click.echo(f"✗ Błąd walidacji: {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()