"""Validasi parameter GET yang dipakai endpoint pencarian arsip."""

from flask import abort, request


def reject_duplicate_params(names):
    for name in names:
        if len(request.args.getlist(name)) > 1:
            abort(400, description=f"Parameter {name} hanya boleh diisi sekali.")


def optional_int(name, *, minimum, maximum=None, default=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    if raw == "":
        if name in ("limit", "offset"):
            abort(400, description=f"Parameter {name} harus berupa angka.")
        return default
    if len(raw) > 10 or not raw.isascii() or not raw.isdecimal():
        abort(400, description=f"Parameter {name} harus berupa angka.")
    value = int(raw)
    if value < minimum or (maximum is not None and value > maximum):
        abort(400, description=f"Parameter {name} di luar batas yang diizinkan.")
    return value
