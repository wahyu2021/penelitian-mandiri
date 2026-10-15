"""Entry point aplikasi Flask dan CLI manajemen laporan penelitian."""
from pathlib import Path
import click
from flask import Flask
from services.db import DEFAULT_DB_PATH

app = Flask(__name__)


@app.cli.group("report")
def report_group():
    """Grup perintah pelaporan dan ekspor evaluasi."""
    pass


@report_group.command("export-bundle")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("output/colab_bundle"),
    help="Direktori tujuan berkas bundle Colab.",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=DEFAULT_DB_PATH,
    help="Path database SQLite arsip.",
)
def export_bundle_command(output_dir: Path, db_path: Path):
    """Ekspor bundle evaluasi teragregasi tanpa data teks arsip untuk Colab."""
    from scripts.export_colab_bundle import export_bundle

    click.echo(f"Memulai ekspor bundle ke: {output_dir}")
    export_bundle(output_dir=output_dir, db_path=db_path)
    click.echo("Ekspor bundle selesai dan terverifikasi aman!")


if __name__ == "__main__":
    app.run(debug=True)
