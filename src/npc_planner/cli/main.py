import json
import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from npc_planner.ingest.build import build_database

app = typer.Typer(help="NPC Team Planner CLI")
data_app = typer.Typer(help="Data ingestion and database management commands.")
pokemon_app = typer.Typer(help="Pokémon query and display commands.")

app.add_typer(data_app, name="data")
app.add_typer(pokemon_app, name="pokemon")


@data_app.command("build")
def data_build(
    raw_dir: Annotated[
        str,
        typer.Option(
            "--raw-dir",
            "-r",
            help="Directory containing raw JSON dumps.",
        ),
    ] = "data/raw/gen3_official",
    db_out: Annotated[
        str,
        typer.Option(
            "--db-out",
            "-o",
            help="Output path for SQLite database file.",
        ),
    ] = "planner.db",
) -> None:
    """Build SQLite database from raw baseline dumps."""
    res_path = build_database(raw_dir, db_out)
    typer.echo(f"Successfully built database at {res_path}")


@pokemon_app.command("show")
def pokemon_show(
    identifier: Annotated[
        str,
        typer.Argument(
            help="Species slug or Form ID (e.g. 'skarmory').",
        ),
    ],
    db_path: Annotated[
        str,
        typer.Option(
            "--db",
            "-d",
            help="Path to SQLite database file.",
        ),
    ] = "planner.db",
) -> None:
    """Display information about a Pokémon species or form."""
    db_file = Path(db_path).resolve()
    if not db_file.exists():
        typer.echo(f"Error: Database file not found at {db_file}", err=True)
        raise typer.Exit(code=1)

    conn = sqlite3.connect(db_file)
    row = conn.execute(
        """
        SELECT form_id, species_slug, type_1, type_2,
               base_hp, base_atk, base_def, base_spa, base_spd, base_spe, bst
        FROM forms WHERE form_id = ? OR species_slug = ?
        """,
        (identifier.lower(), identifier.lower()),
    ).fetchone()

    if not row:
        # Check staging forms as fallback
        stg_row = conn.execute(
            "SELECT raw_payload FROM stg_forms WHERE form_id = ? OR species_slug = ?",
            (identifier.lower(), identifier.lower()),
        ).fetchone()
        if stg_row:
            data = json.loads(stg_row[0])
            typer.echo(f"Pokémon Form: {data.get('form_id')} (staging)")
            typer.echo(f"Types: {data.get('type_1')} / {data.get('type_2', 'none')}")
            typer.echo(
                f"Base Stats: HP {data.get('base_hp')} Atk {data.get('base_atk')} Def {data.get('base_def')} SpA {data.get('base_spa')} SpD {data.get('base_spd')} Spe {data.get('base_spe')}"
            )
            conn.close()
            return

        typer.echo(f"Error: Pokémon '{identifier}' not found in database.", err=True)
        conn.close()
        raise typer.Exit(code=1)

    form_id, species, t1, t2, hp, atk, df, spa, spd, spe, bst = row
    typer.echo(f"Pokémon Form: {form_id} (Species: {species})")
    typer.echo(f"Types: {t1} / {t2 or 'none'}")
    typer.echo(
        f"Base Stats: HP {hp} Atk {atk} Def {df} SpA {spa} SpD {spd} Spe {spe} (BST: {bst})"
    )
    conn.close()


if __name__ == "__main__":
    app()
