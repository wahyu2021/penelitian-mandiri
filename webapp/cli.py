"""Perintah terminal untuk akun dan laporan."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import current_app
from werkzeug.security import generate_password_hash

from services.db import init_db


def register_commands(app):
    @app.cli.group("db")
    def db_group():
        """Inisialisasi atau perbarui skema SQLite lokal."""

    @db_group.command("upgrade")
    def upgrade_db_command():
        connection = init_db(current_app.config["DATABASE"])
        connection.close()
        click.echo("Skema SQLite lokal siap.")

    @app.cli.group("report")
    def report_group():
        """Perintah pelaporan dan ekspor evaluasi."""

    @report_group.command("export-bundle")
    @click.option("--output-dir", type=click.Path(path_type=Path), default=Path("output/colab_bundle"))
    @click.option("--db-path", type=click.Path(path_type=Path), default=None)
    def export_bundle_command(output_dir, db_path):
        from scripts.export_colab_bundle import export_bundle
        click.echo(f"Memulai ekspor bundle ke: {output_dir}")
        export_bundle(output_dir=output_dir, db_path=db_path or current_app.config["DATABASE"])
        click.echo("Ekspor bundle selesai.")

    @app.cli.group("user")
    def user_group():
        """Kelola akun lokal aplikasi."""

    @user_group.command("create")
    @click.option("--username", prompt=True)
    @click.option("--role", type=click.Choice(["admin", "petugas"]), default="admin", show_default=True)
    @click.password_option(confirmation_prompt=True)
    def create_user(username, role, password):
        username = username.strip()
        if not username or len(username) > 80 or len(password) < 10:
            raise click.ClickException("Nama pengguna wajib diisi dan kata sandi minimal 10 karakter.")
        connection = init_db(current_app.config["DATABASE"])
        try:
            with connection:
                connection.execute(
                    "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                    (username, generate_password_hash(password), role, datetime.now(timezone.utc).isoformat()),
                )
        except sqlite3.IntegrityError as exc:
            raise click.ClickException("Nama pengguna sudah dipakai.") from exc
        finally:
            connection.close()
        click.echo(f"Akun {role} dibuat: {username}")
