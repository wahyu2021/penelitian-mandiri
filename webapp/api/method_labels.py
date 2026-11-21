"""Label metode yang dipakai respons API untuk tampilan admin."""

from services.web_search import METHODS

METHOD_LABELS = {
    "like": "LIKE (pembanding)",
    "levenshtein": "Levenshtein",
    "jaro_winkler": "Jaro-Winkler",
    "token_set": "Token Set",
    "ngram": "N-gram Dice",
}


def method_options():
    return [{"name": name, "label": METHOD_LABELS[name]} for name in METHODS]
