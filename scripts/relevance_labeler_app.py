"""Aplikasi Web Interaktif untuk Pelabelan Relevansi (Relevance Assessment Tool).

Memungkinkan peneliti dan arsiparis menilai kandidat dokumen satu per satu
dengan mudah, cepat, dan nyaman menggunakan keyboard shortcut (1, 0, R, Panah, Ctrl+Z).
Menyimpan penilaian langsung ke berkas CSV di folder output/.
Dilengkapi feedback visual jelas, riwayat aksi terakhir, tombol batal (Undo), dan reset.
"""
import argparse
import csv
import json
import os
import shutil
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import Flask, jsonify, render_template_string, request

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
BACKUP_DIR = OUTPUT_DIR / ".labeler_backups"

DATASET_CONFIG = {
    "relevance_pool.csv": {
        "label": "Berkas Utama (relevance_pool.csv)",
        "notes_col": "auditor_notes",
        "description": "Seluruh 40 kueri hasil blind pooling untuk evaluasi utama.",
    },
    "relevance_pool_pilot_5.csv": {
        "label": "Sampel Pilot (relevance_pool_pilot_5.csv)",
        "notes_col": "auditor_notes",
        "description": "5 kueri awal (Q001–Q005) untuk uji coba dan kalibrasi waktu.",
    },
    "relevance_verification_sample.csv": {
        "label": "Verifikasi Arsiparis (relevance_verification_sample.csv)",
        "notes_col": "archivist_notes",
        "description": "120 sampel acak berstrata untuk verifikasi independen oleh arsiparis.",
    },
}

app = Flask(__name__)


def get_dataset_path(filename: str) -> Path:
    """Validasi dan dapatkan path berkas dataset."""
    if filename not in DATASET_CONFIG:
        filename = "relevance_pool.csv"
    return OUTPUT_DIR / filename


def backup_dataset(file_path: Path) -> None:
    """Buat cadangan berkas CSV sebelum ditimpa jika belum ada cadangan di sesi ini."""
    if not file_path.is_file():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    shutil.copy2(file_path, backup_file)


def read_pool_csv(file_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Baca berkas CSV pool dengan encoding utf-8-sig."""
    if not file_path.is_file():
        return [], []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def write_pool_csv(file_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    """Tulis berkas CSV pool dengan encoding utf-8-sig secara aman."""
    temp_file = file_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temp_file.replace(file_path)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pelabel Relevansi Temu Kembali Arsip</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        brand: {
                            50: '#eef2ff',
                            100: '#e0e7ff',
                            500: '#6366f1',
                            600: '#4f46e5',
                            700: '#4338ca',
                            900: '#312e81',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        .highlight-kw {
            background-color: #fef08a;
            color: #854d0e;
            padding: 1px 4px;
            border-radius: 4px;
            font-weight: 600;
        }
        .kbd-badge {
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            box-shadow: 0 1px 0 #94a3b8;
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 0.75rem;
            font-family: monospace;
            color: #334155;
            font-weight: 700;
        }
        @keyframes flashGreen {
            0% { background-color: rgba(16, 185, 129, 0.25); border-color: rgba(16, 185, 129, 0.8); }
            100% { background-color: #ffffff; border-color: #e2e8f0; }
        }
        @keyframes flashRed {
            0% { background-color: rgba(244, 63, 94, 0.25); border-color: rgba(244, 63, 94, 0.8); }
            100% { background-color: #ffffff; border-color: #e2e8f0; }
        }
        .flash-emerald {
            animation: flashGreen 0.28s ease-out;
        }
        .flash-rose {
            animation: flashRed 0.28s ease-out;
        }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col font-sans">

    <!-- FLOATING TOP NOTIFICATION TOAST (FEEDBACK UTAMA) -->
    <div id="floatingToast" class="fixed top-5 left-1/2 -translate-x-1/2 z-50 transition-all duration-200 transform -translate-y-12 opacity-0 pointer-events-none">
        <div id="floatingToastInner" class="flex items-center space-x-2.5 px-5 py-2.5 rounded-full shadow-xl text-xs sm:text-sm font-bold border">
            <span id="toastIcon" class="text-base">✓</span>
            <span id="toastMessage">Tersimpan di CSV</span>
        </div>
    </div>

    <!-- Top Navigation Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
        <div class="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-xl bg-brand-600 text-white flex items-center justify-center font-bold shadow-md shadow-brand-500/20">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                </div>
                <div>
                    <h1 class="text-base font-bold text-slate-900 leading-tight">Pelabel Relevansi Temu Kembali Arsip</h1>
                    <p class="text-xs text-slate-500">Dinas Perpustakaan dan Kearsipan Kota Palembang</p>
                </div>
            </div>

            <!-- Dataset Selector, Sound Toggle & Modal Triggers -->
            <div class="flex items-center space-x-2">
                <select id="datasetSelect" onchange="changeDataset()" class="text-xs bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg px-3 py-2 font-medium text-slate-700 outline-none focus:ring-2 focus:ring-brand-500 transition-all cursor-pointer">
                    {% for key, cfg in datasets.items() %}
                    <option value="{{ key }}" {% if key == active_dataset %}selected{% endif %}>{{ cfg.label }}</option>
                    {% endfor %}
                </select>

                <!-- Sound Toggle -->
                <button id="soundToggleBtn" onclick="toggleSound()" title="Aktif/Nonaktifkan Suara Efek" class="inline-flex items-center space-x-1 px-2.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-semibold border border-slate-300 transition-all cursor-pointer">
                    <span id="soundIcon">🔊</span>
                </button>

                <!-- Pedoman Trigger -->
                <button onclick="toggleModal('guideModal')" class="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-300 transition-all cursor-pointer">
                    <svg class="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                    </svg>
                    <span>Pedoman</span>
                    <span class="kbd-badge">?</span>
                </button>

                <!-- Pintasan Trigger -->
                <button onclick="toggleModal('shortcutModal')" class="inline-flex items-center space-x-1 px-2.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-semibold border border-slate-300 transition-all cursor-pointer">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"></path>
                    </svg>
                    <span>Pintasan</span>
                </button>
            </div>
        </div>
    </header>

    <!-- Main Content Container -->
    <main class="max-w-4xl w-full mx-auto px-4 py-6 flex-1 flex flex-col space-y-4">

        <!-- Progress Overview Bar -->
        <div class="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div class="flex-1">
                <div class="flex items-center justify-between text-xs font-semibold text-slate-600 mb-1.5">
                    <span class="flex items-center gap-1.5">
                        <span class="inline-block w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse"></span>
                        Kemajuan Penilaian: <strong id="progressText" class="text-slate-900 font-bold">0 / 0</strong>
                    </span>
                    <span id="percentText" class="text-brand-600 font-bold">0%</span>
                </div>
                <div class="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden flex">
                    <div id="progressBar" class="bg-brand-500 h-full transition-all duration-300" style="width: 0%"></div>
                </div>
            </div>

            <!-- Stats Badge Group -->
            <div class="flex items-center space-x-2 text-xs font-semibold shrink-0">
                <span class="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Relevan:</span>
                    <strong id="countRelevant" class="font-bold">0</strong>
                </span>
                <span class="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200">
                    <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                    <span>Tidak Relevan:</span>
                    <strong id="countIrrelevant" class="font-bold">0</strong>
                </span>
                <span class="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
                    <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                    <span>Ragu:</span>
                    <strong id="countRagu" class="font-bold">0</strong>
                </span>
            </div>
        </div>

        <!-- Filter & Jump Control -->
        <div class="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div class="flex items-center space-x-2">
                <span class="font-semibold text-slate-500">Kueri:</span>
                <select id="queryJumpSelect" onchange="jumpToSelectedQuery()" class="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-brand-500 transition-all cursor-pointer shadow-2xs">
                    <!-- Populated via JS -->
                </select>
                <button onclick="jumpToFirstUnjudged()" class="px-3 py-1.5 rounded-lg bg-white border border-brand-300 text-brand-700 hover:bg-brand-50 font-semibold transition-all shadow-2xs cursor-pointer flex items-center space-x-1">
                    <span>Lompat ke Belum Dinilai</span>
                    <span class="kbd-badge">U</span>
                </button>
            </div>

            <div class="flex items-center space-x-2">
                <label class="inline-flex items-center space-x-1.5 text-slate-600 font-medium cursor-pointer select-none">
                    <input type="checkbox" id="unjudgedOnlyCheck" onchange="toggleUnjudgedOnly()" class="rounded border-slate-300 text-brand-600 focus:ring-brand-500">
                    <span>Hanya tampilkan yang belum dinilai</span>
                </label>
            </div>
        </div>

        <!-- Flashcard Penilaian Utama -->
        <div id="mainCard" class="bg-white rounded-2xl border border-slate-200 shadow-md p-6 sm:p-8 flex flex-col space-y-5 relative transition-all">
            
            <!-- Card Header: Kueri Info & Navigasi Baris -->
            <div>
                <div class="flex items-center justify-between text-xs mb-2">
                    <span class="text-slate-500 font-semibold tracking-wide uppercase flex items-center gap-2">
                        <span id="cardQueryId" class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-800 font-mono font-bold">Q001</span>
                        <span id="cardItemPosition">Item 1 dari 1077</span>
                    </span>
                    <div class="flex items-center space-x-2">
                        <span id="badgeQueryType" class="px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 font-semibold border border-brand-200 text-2xs">topik</span>
                        <span id="badgeNoiseType" class="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold border border-slate-200 text-2xs">tanpa_gangguan</span>
                    </div>
                </div>

                <!-- Teks Kueri Pencarian -->
                <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start space-x-3">
                    <div class="mt-0.5 text-brand-600">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                        </svg>
                    </div>
                    <div>
                        <div class="text-2xs font-bold uppercase tracking-wider text-slate-400">Kata Kunci Kueri Pencarian:</div>
                        <div id="cardQueryText" class="text-lg sm:text-xl font-extrabold text-slate-900 mt-0.5 font-mono select-all">
                            ...
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card Body: Ringkasan Arsip Kandidat -->
            <div class="flex flex-col space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Teks Dokumen Arsip Hasil Temu Kembali:</span>
                    <span id="cardPoolOrder" class="text-2xs font-semibold text-slate-400">Peringkat Pool: #1</span>
                </div>

                <div class="bg-white border-2 border-slate-100 rounded-xl p-5 shadow-2xs hover:border-slate-200 transition-colors">
                    <div id="cardSummaryRaw" class="text-base text-slate-800 leading-relaxed font-normal">
                        Memuat data arsip...
                    </div>
                </div>

                <!-- Metadata Ekstraksi Dokumen -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                    <div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                        <div class="text-2xs font-semibold text-slate-400 uppercase">Nomor SPM</div>
                        <div id="cardSpmNumber" class="text-xs font-bold text-slate-800 mt-0.5 font-mono truncate">-</div>
                    </div>
                    <div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                        <div class="text-2xs font-semibold text-slate-400 uppercase">Pihak / Rekanan</div>
                        <div id="cardPartyName" class="text-xs font-bold text-slate-800 mt-0.5 truncate">-</div>
                    </div>
                    <div class="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
                        <div class="text-2xs font-semibold text-slate-400 uppercase">ID Arsip (Database)</div>
                        <div id="cardArchiveId" class="text-xs font-bold text-slate-800 mt-0.5 font-mono">#0</div>
                    </div>
                </div>
            </div>

            <!-- Catatan Auditor / Arsiparis Opsional -->
            <div class="pt-1">
                <div class="flex items-center justify-between mb-1">
                    <label for="cardNotes" class="text-xs font-semibold text-slate-600 flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                        </svg>
                        <span>Catatan Khusus (Opsional):</span>
                    </label>
                </div>
                <input type="text" id="cardNotes" placeholder="Tuliskan catatan jika ada hal khusus..." onchange="saveNotesOnly()" class="w-full text-xs bg-slate-50 border border-slate-200 focus:bg-white focus:border-brand-500 rounded-lg px-3 py-2 outline-none transition-all">
            </div>

            <!-- Current Judgment Status Indicator & Quick Toggles -->
            <div class="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                <div class="text-xs text-slate-500 flex items-center space-x-2">
                    <span>Status Saat Ini:</span>
                    <span id="currentStatusBadge" class="px-2.5 py-1 rounded-md font-bold text-xs bg-slate-100 text-slate-600">
                        Belum Dinilai
                    </span>
                    <span id="currentRaguBadge" class="hidden px-2.5 py-1 rounded-md font-bold text-xs bg-amber-100 text-amber-800 border border-amber-200">
                        Ragu
                    </span>
                </div>

                <div class="flex items-center space-x-2">
                    <!-- Reset / Kosongkan Nilai -->
                    <button id="btnResetVerdict" onclick="resetCurrentVerdict()" title="Kosongkan kembali nilai item ini" class="px-2.5 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100 text-xs font-semibold transition-all flex items-center space-x-1 cursor-pointer">
                        <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                        <span>Kosongkan Nilai</span>
                        <span class="kbd-badge">Del</span>
                    </button>

                    <!-- Toggle Ragu -->
                    <button id="btnToggleRagu" onclick="toggleRagu()" class="px-3 py-1.5 rounded-lg border border-amber-300 text-amber-800 hover:bg-amber-50 text-xs font-semibold transition-all flex items-center space-x-1.5 cursor-pointer">
                        <svg class="w-3.5 h-3.5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                        </svg>
                        <span>Tandai Ragu</span>
                        <span class="kbd-badge">R</span>
                    </button>
                </div>
            </div>

            <!-- Big Action Buttons (1 & 0) -->
            <div class="grid grid-cols-2 gap-4 pt-1">
                <!-- Button Relevan (1) -->
                <button id="btnRelevant" onclick="setVerdict(1)" class="group flex flex-col items-center justify-center py-4 sm:py-5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-md shadow-emerald-600/20 active:scale-98 transition-all cursor-pointer">
                    <div class="flex items-center space-x-2">
                        <svg class="w-6 h-6 stroke-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
                        </svg>
                        <span class="text-base sm:text-lg">RELEVAN</span>
                        <span class="kbd-badge bg-emerald-700 text-white border-emerald-500 shadow-none">1</span>
                    </div>
                    <span class="text-2xs text-emerald-100 font-normal mt-0.5">Sesuai dengan kueri pencarian</span>
                </button>

                <!-- Button Tidak Relevan (0) -->
                <button id="btnIrrelevant" onclick="setVerdict(0)" class="group flex flex-col items-center justify-center py-4 sm:py-5 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-md shadow-rose-600/20 active:scale-98 transition-all cursor-pointer">
                    <div class="flex items-center space-x-2">
                        <svg class="w-6 h-6 stroke-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                        <span class="text-base sm:text-lg">TIDAK RELEVAN</span>
                        <span class="kbd-badge bg-rose-700 text-white border-rose-500 shadow-none">0</span>
                    </div>
                    <span class="text-2xs text-rose-100 font-normal mt-0.5">Tidak sesuai dengan kueri</span>
                </button>
            </div>

            <!-- Navigation Controls (Prev / Next) -->
            <div class="flex items-center justify-between border-t border-slate-100 pt-4">
                <button onclick="navigate(-1)" class="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold text-xs transition-all cursor-pointer">
                    <span class="kbd-badge">←</span>
                    <span>Sebelumnya (Koreksi)</span>
                </button>

                <div class="text-xs text-slate-400 font-mono hidden sm:block">
                    Tekan <span class="font-bold text-slate-600">1</span>, <span class="font-bold text-slate-600">0</span>, <span class="font-bold text-slate-600">R</span>, atau <span class="font-bold text-slate-600">←</span> / <span class="font-bold text-slate-600">→</span>
                </div>

                <button onclick="navigate(1)" class="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold text-xs transition-all cursor-pointer">
                    <span>Selanjutnya</span>
                    <span class="kbd-badge">→</span>
                </button>
            </div>
        </div>

        <!-- RIWAYAT AKSI TERAKHIR & TOMBOL BATALKAN (UNDO) -->
        <div id="lastActionBar" class="bg-slate-100 border border-slate-200 rounded-xl p-3 flex items-center justify-between text-xs text-slate-600 transition-all opacity-0 pointer-events-none">
            <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>Tindakan Terakhir: <strong id="lastActionText" class="text-slate-900">-</strong></span>
            </div>
            <button onclick="undoLastAction()" class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-200 font-bold text-brand-700 shadow-2xs transition-all cursor-pointer">
                <span>↩ Batalkan (Undo)</span>
                <span class="kbd-badge">Ctrl+Z</span>
            </button>
        </div>

        <!-- Tips Singkat Koreksi -->
        <div class="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-800 flex items-start space-x-2">
            <span class="text-base">💡</span>
            <div>
                <strong>Cara Memperbaiki Jika Salah Isi:</strong> Tekan tombol panah kiri <strong>[ ← ]</strong> untuk kembali ke baris sebelumnya, lalu langsung tekan nilai yang benar (<strong>1</strong> atau <strong>0</strong>). Anda juga bisa menekan tombol <strong>[ Ctrl + Z ]</strong> untuk membatalkan tindakan terakhir, atau tombol <strong>[ Kosongkan Nilai ]</strong> jika ingin membatalkan penilaian pada baris tersebut.
            </div>
        </div>

    </main>

    <!-- Modal Pedoman Penilaian Relevansi -->
    <div id="guideModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 hidden">
        <div class="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
            <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <h3 class="text-base font-bold text-slate-900 flex items-center gap-2">
                    <svg class="w-5 h-5 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                    </svg>
                    <span>Ringkasan Pedoman Penilaian Relevansi</span>
                </h3>
                <button onclick="toggleModal('guideModal')" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-all cursor-pointer">✕</button>
            </div>
            <div class="p-6 overflow-y-auto space-y-4 text-xs text-slate-700 leading-relaxed">
                <div class="p-3 bg-brand-50 border border-brand-200 rounded-xl">
                    <h4 class="font-bold text-brand-900 mb-1">Prinsip Dasar:</h4>
                    <p>Nilai berdasarkan teks deskripsi asli (<code class="bg-white px-1.5 py-0.5 rounded text-brand-800 font-mono font-bold">summary_raw</code>), bukan metadata komputer. Penilaian bersifat buta (tanpa skor/metode).</p>
                </div>

                <div class="space-y-3">
                    <div class="border-b border-slate-100 pb-2">
                        <h5 class="font-bold text-slate-900">1. Kueri Nomor SPM (<code>nomor_spm</code>)</h5>
                        <p class="text-slate-600">Relevan hanya jika merujuk pada nomor SPM yang sama persis (termasuk variasi spasi/garis miring, atau ejaan varian seperti <code>L.S</code> / dua digit tahun <code>02</code>). Berbeda nomor = Tidak Relevan.</p>
                    </div>

                    <div class="border-b border-slate-100 pb-2">
                        <h5 class="font-bold text-slate-900">2. Kueri Topik / Pekerjaan (<code>topik</code>)</h5>
                        <p class="text-slate-600">Relevan jika memuat pekerjaan atau transaksi pembayaran yang sama. <em>Catatan Termin:</em> Jika kueri menyebut termin secara spesifik (misal "termin I"), jangan samakan dengan termin lain (termin II).</p>
                    </div>

                    <div class="border-b border-slate-100 pb-2">
                        <h5 class="font-bold text-slate-900">3. Kueri Rekanan / Pihak Ketiga (<code>pihak</code>)</h5>
                        <p class="text-slate-600">Relevan jika melibatkan badan usaha / CV / PT yang sama persis. Nama perusahaan berbeda = Tidak Relevan.</p>
                    </div>

                    <div class="border-b border-slate-100 pb-2">
                        <h5 class="font-bold text-slate-900">4. Kueri Campuran (<code>campuran</code>)</h5>
                        <p class="text-slate-600">Wajib memenuhi seluruh unsur secara bersamaan (misal pekerjaan + tahun, atau pihak + tahun). Hanya memenuhi salah satu = Tidak Relevan.</p>
                    </div>

                    <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                        <h5 class="font-bold text-amber-900 mb-1">5. Aturan Khusus Kueri Kata Hilang (<code>kata_hilang</code>):</h5>
                        <ul class="list-disc list-inside space-y-1 text-amber-800">
                            <li>Semua komponen yang <strong>masih tertulis</strong> dalam kueri wajib cocok persis dengan data arsip.</li>
                            <li>Bila ada <strong>lebih dari satu arsip</strong> yang cocok dengan komponen tertulis tersebut, <strong>semua arsip yang cocok dinilai RELEVAN (1)</strong> dan wajib ditandai <strong>RAGU = 1</strong>.</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="px-6 py-3 bg-slate-50 border-t border-slate-200 text-right">
                <button onclick="toggleModal('guideModal')" class="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-all cursor-pointer">Tutup Pedoman</button>
            </div>
        </div>
    </div>

    <!-- Modal Daftar Pintasan Keyboard -->
    <div id="shortcutModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 hidden">
        <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-base font-bold text-slate-900">Pintasan Keyboard</h3>
                <button onclick="toggleModal('shortcutModal')" class="text-slate-400 hover:text-slate-700 cursor-pointer">✕</button>
            </div>
            <div class="space-y-2.5 text-xs">
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Nilai Relevan (1) & Lanjut</span>
                    <span class="kbd-badge">1</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Nilai Tidak Relevan (0) & Lanjut</span>
                    <span class="kbd-badge">0</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Tandai / Hapus Ragu</span>
                    <span class="kbd-badge">R</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Batalkan Tindakan Terakhir (Undo)</span>
                    <span class="kbd-badge">Ctrl + Z</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Kosongkan Nilai Kartu Saat Ini</span>
                    <span class="kbd-badge">Del / Backspace</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Koreksi / Arsip Sebelumnya</span>
                    <span class="kbd-badge">←</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Arsip Selanjutnya</span>
                    <span class="kbd-badge">→</span>
                </div>
                <div class="flex items-center justify-between py-1.5 border-b border-slate-100">
                    <span class="text-slate-600">Lompat ke Item Belum Dinilai</span>
                    <span class="kbd-badge">U</span>
                </div>
                <div class="flex items-center justify-between py-1.5">
                    <span class="text-slate-600">Buka Pedoman Relevansi</span>
                    <span class="kbd-badge">?</span>
                </div>
            </div>
            <button onclick="toggleModal('shortcutModal')" class="w-full mt-5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-all cursor-pointer">Tutup</button>
        </div>
    </div>

    <!-- Application Script -->
    <script>
        let allItems = [];
        let currentIndex = 0;
        let activeDataset = "{{ active_dataset }}";
        let isSaving = false;
        let soundEnabled = true;
        let lastAction = null; // Menyimpan state untuk Undo

        document.addEventListener("DOMContentLoaded", () => {
            loadDatasetData();
            setupKeyboardShortcuts();
        });

        // Suara Efek Sintetis (Web Audio API)
        function playSound(type) {
            if (!soundEnabled) return;
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);

                if (type === 'relevant') {
                    // Ding ceria naik
                    osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
                    osc.frequency.exponentialRampToValueAtTime(783.99, ctx.currentTime + 0.1); // G5
                } else if (type === 'irrelevant') {
                    // Nada turun lembut
                    osc.frequency.setValueAtTime(440, ctx.currentTime); // A4
                    osc.frequency.exponentialRampToValueAtTime(329.63, ctx.currentTime + 0.1); // E4
                } else if (type === 'undo' || type === 'reset') {
                    // Nada netral
                    osc.frequency.setValueAtTime(392, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(493.88, ctx.currentTime + 0.08);
                }

                gain.gain.setValueAtTime(0.09, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
                osc.start();
                osc.stop(ctx.currentTime + 0.12);
            } catch(e) {}
        }

        function toggleSound() {
            soundEnabled = !soundEnabled;
            document.getElementById("soundIcon").textContent = soundEnabled ? "🔊" : "🔇";
            showFloatingToast(soundEnabled ? "Suara Efek Aktif" : "Suara Efek Dimatikan", "info");
        }

        async function loadDatasetData() {
            try {
                const res = await fetch(`/api/data?dataset=${activeDataset}`);
                const data = await res.json();
                allItems = data.items || [];
                
                updateStats(data.stats);
                populateQueryDropdown();
                
                const firstUnjudged = allItems.findIndex(item => item.is_relevant === "" || item.is_relevant === null);
                currentIndex = firstUnjudged !== -1 ? firstUnjudged : 0;
                
                renderCurrentCard();
            } catch (err) {
                console.error("Gagal memuat dataset:", err);
                alert("Gagal memuat data dataset. Pastikan berkas CSV tersedia di folder output/.");
            }
        }

        function updateStats(stats) {
            if (!stats) return;
            document.getElementById("progressText").textContent = `${stats.judged} / ${stats.total}`;
            const pct = stats.total > 0 ? Math.round((stats.judged / stats.total) * 100) : 0;
            document.getElementById("percentText").textContent = `${pct}%`;
            document.getElementById("progressBar").style.width = `${pct}%`;
            document.getElementById("countRelevant").textContent = stats.relevant;
            document.getElementById("countIrrelevant").textContent = stats.irrelevant;
            document.getElementById("countRagu").textContent = stats.ragu;
        }

        function populateQueryDropdown() {
            const select = document.getElementById("queryJumpSelect");
            select.innerHTML = "";
            
            const queriesMap = {};
            allItems.forEach((it, idx) => {
                const qid = it.query_id;
                if (!queriesMap[qid]) {
                    queriesMap[qid] = { firstIdx: idx, count: 0, judged: 0 };
                }
                queriesMap[qid].count++;
                if (it.is_relevant !== "" && it.is_relevant !== null) {
                    queriesMap[qid].judged++;
                }
            });

            for (const [qid, info] of Object.entries(queriesMap)) {
                const opt = document.createElement("option");
                opt.value = info.firstIdx;
                const doneMark = info.judged === info.count ? "✓" : "";
                opt.textContent = `${qid} (${info.judged}/${info.count}) ${doneMark}`;
                select.appendChild(opt);
            }
        }

        function renderCurrentCard() {
            if (allItems.length === 0) return;
            const item = allItems[currentIndex];
            if (!item) return;

            document.getElementById("cardQueryId").textContent = item.query_id;
            document.getElementById("cardItemPosition").textContent = `Item ${currentIndex + 1} dari ${allItems.length}`;
            document.getElementById("badgeQueryType").textContent = item.query_type || "topik";
            document.getElementById("badgeNoiseType").textContent = item.noise_type || "tanpa_gangguan";
            document.getElementById("cardQueryText").textContent = item.query_text;
            document.getElementById("cardPoolOrder").textContent = `Peringkat Pool: #${item.pool_order || (currentIndex + 1)}`;
            
            document.getElementById("cardSummaryRaw").innerHTML = highlightKeywords(item.summary_raw, item.query_text);
            document.getElementById("cardSpmNumber").textContent = item.spm_number || "-";
            document.getElementById("cardPartyName").textContent = item.party_name || "-";
            document.getElementById("cardArchiveId").textContent = `#${item.archive_id}`;
            document.getElementById("cardNotes").value = item.auditor_notes || item.archivist_notes || "";

            const statusBadge = document.getElementById("currentStatusBadge");
            const btnRel = document.getElementById("btnRelevant");
            const btnIrrel = document.getElementById("btnIrrelevant");

            btnRel.classList.remove("ring-4", "ring-emerald-300");
            btnIrrel.classList.remove("ring-4", "ring-rose-300");

            if (item.is_relevant === "1" || item.is_relevant === 1) {
                statusBadge.textContent = "RELEVAN (1)";
                statusBadge.className = "px-2.5 py-1 rounded-md font-bold text-xs bg-emerald-100 text-emerald-800 border border-emerald-300";
                btnRel.classList.add("ring-4", "ring-emerald-300");
            } else if (item.is_relevant === "0" || item.is_relevant === 0) {
                statusBadge.textContent = "TIDAK RELEVAN (0)";
                statusBadge.className = "px-2.5 py-1 rounded-md font-bold text-xs bg-rose-100 text-rose-800 border border-rose-300";
                btnIrrel.classList.add("ring-4", "ring-rose-300");
            } else {
                statusBadge.textContent = "Belum Dinilai";
                statusBadge.className = "px-2.5 py-1 rounded-md font-bold text-xs bg-slate-100 text-slate-600";
            }

            const raguBadge = document.getElementById("currentRaguBadge");
            const btnToggleRagu = document.getElementById("btnToggleRagu");
            if (item.ragu === "1" || item.ragu === 1) {
                raguBadge.classList.remove("hidden");
                btnToggleRagu.classList.add("bg-amber-100", "font-bold");
            } else {
                raguBadge.classList.add("hidden");
                btnToggleRagu.classList.remove("bg-amber-100", "font-bold");
            }

            syncQueryDropdownSelection(item.query_id);
        }

        function highlightKeywords(text, query) {
            if (!text || !query) return text || "";
            const tokens = query.split(/[\s/,.\-_]+/).filter(t => t.length >= 2);
            if (tokens.length === 0) return escapeHtml(text);

            let escaped = escapeHtml(text);
            tokens.sort((a, b) => b.length - a.length);

            tokens.forEach(tok => {
                const regex = new RegExp(`(${escapeRegex(tok)})`, 'gi');
                escaped = escaped.replace(regex, '<span class="highlight-kw">$1</span>');
            });
            return escaped;
        }

        function escapeHtml(str) {
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        function escapeRegex(string) {
            return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }

        async function setVerdict(verdict) {
            if (allItems.length === 0) return;
            const item = allItems[currentIndex];
            
            // Rekam state sebelum diubah untuk fitur UNDO
            lastAction = {
                index: currentIndex,
                query_id: item.query_id,
                item_pos: currentIndex + 1,
                prev_is_relevant: item.is_relevant,
                prev_ragu: item.ragu,
                prev_notes: item.auditor_notes || "",
                new_verdict: verdict,
            };

            item.is_relevant = String(verdict);

            // Efek Flash & Suara Seketika
            triggerCardFlash(verdict === 1 ? 'emerald' : 'rose');
            playSound(verdict === 1 ? 'relevant' : 'irrelevant');

            // Tampilkan Floating Feedback yang sangat jelas
            const verdictLabel = verdict === 1 ? "RELEVAN (1)" : "TIDAK RELEVAN (0)";
            showFloatingToast(`✓ Tersimpan: [${item.query_id} #${item.pool_order || (currentIndex+1)}] → ${verdictLabel}`, verdict === 1 ? "relevant" : "irrelevant");

            // Update Last Action Bar
            updateLastActionBar(`[${item.query_id} #${item.pool_order || (currentIndex+1)}] dinilai ${verdictLabel}`);

            // Simpan ke CSV
            await saveItemToServer(item);

            // Lanjut ke arsip berikutnya setelah delay singkat untuk transisi halus
            setTimeout(() => {
                navigate(1);
            }, 140);
        }

        async function toggleRagu() {
            if (allItems.length === 0) return;
            const item = allItems[currentIndex];
            item.ragu = (item.ragu === "1" || item.ragu === 1) ? "0" : "1";
            
            playSound('undo');
            const statusStr = (item.ragu === "1") ? "Ditandai RAGU (1)" : "Status Ragu Dihapus (0)";
            showFloatingToast(`⚠ ${statusStr} untuk [${item.query_id}]`, "warning");

            await saveItemToServer(item);
            renderCurrentCard();
        }

        async function resetCurrentVerdict() {
            if (allItems.length === 0) return;
            const item = allItems[currentIndex];
            
            // Rekam state untuk undo
            lastAction = {
                index: currentIndex,
                query_id: item.query_id,
                item_pos: currentIndex + 1,
                prev_is_relevant: item.is_relevant,
                prev_ragu: item.ragu,
                prev_notes: item.auditor_notes || "",
                new_verdict: "",
            };

            item.is_relevant = "";
            item.ragu = "";
            playSound('reset');
            showFloatingToast(`Status [${item.query_id}] dikembalikan ke BELUM DINILAI`, "info");
            updateLastActionBar(`[${item.query_id} #${item.pool_order || (currentIndex+1)}] di-reset (kosong)`);

            await saveItemToServer(item);
            renderCurrentCard();
        }

        async function undoLastAction() {
            if (!lastAction) {
                showFloatingToast("Tidak ada tindakan yang dapat dibatalkan", "info");
                return;
            }

            const action = lastAction;
            currentIndex = action.index;
            const item = allItems[currentIndex];
            
            item.is_relevant = action.prev_is_relevant;
            item.ragu = action.prev_ragu;
            item.auditor_notes = action.prev_notes;
            if (item.archivist_notes !== undefined) {
                item.archivist_notes = action.prev_notes;
            }

            playSound('undo');
            showFloatingToast(`↩ Berhasil dibatalkan! Kembali ke item #${action.item_pos}`, "info");
            
            // Sembunyikan bar undo setelah dibatalkan
            hideLastActionBar();
            lastAction = null;

            await saveItemToServer(item);
            renderCurrentCard();
        }

        async function saveNotesOnly() {
            if (allItems.length === 0) return;
            const item = allItems[currentIndex];
            item.auditor_notes = document.getElementById("cardNotes").value.trim();
            if (item.archivist_notes !== undefined) {
                item.archivist_notes = item.auditor_notes;
            }
            await saveItemToServer(item);
            showFloatingToast("Catatan tersimpan", "info");
        }

        async function saveItemToServer(item) {
            isSaving = true;
            try {
                const res = await fetch("/api/save", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        dataset: activeDataset,
                        index: currentIndex,
                        query_id: item.query_id,
                        archive_id: item.archive_id,
                        is_relevant: item.is_relevant,
                        ragu: item.ragu,
                        notes: item.auditor_notes || "",
                    })
                });
                const result = await res.json();
                if (result.success) {
                    updateStats(result.stats);
                    populateQueryDropdown();
                }
            } catch (err) {
                console.error("Gagal menyimpan ke server:", err);
                showFloatingToast("⚠️ Gagal menyimpan ke server!", "error");
            } finally {
                isSaving = false;
            }
        }

        function triggerCardFlash(type) {
            const card = document.getElementById("mainCard");
            card.classList.remove("flash-emerald", "flash-rose");
            void card.offsetWidth; // Force reflow
            card.classList.add(type === 'emerald' ? 'flash-emerald' : 'flash-rose');
        }

        function showFloatingToast(message, type = 'info') {
            const toast = document.getElementById("floatingToast");
            const toastInner = document.getElementById("floatingToastInner");
            const toastIcon = document.getElementById("toastIcon");
            const toastMessage = document.getElementById("toastMessage");

            toastMessage.textContent = message;

            if (type === 'relevant') {
                toastInner.className = "flex items-center space-x-2.5 px-5 py-2.5 rounded-full shadow-2xl text-xs sm:text-sm font-bold bg-emerald-600 text-white border-emerald-400";
                toastIcon.textContent = "✓";
            } else if (type === 'irrelevant') {
                toastInner.className = "flex items-center space-x-2.5 px-5 py-2.5 rounded-full shadow-2xl text-xs sm:text-sm font-bold bg-rose-600 text-white border-rose-400";
                toastIcon.textContent = "✗";
            } else if (type === 'warning') {
                toastInner.className = "flex items-center space-x-2.5 px-5 py-2.5 rounded-full shadow-2xl text-xs sm:text-sm font-bold bg-amber-500 text-slate-900 border-amber-300";
                toastIcon.textContent = "⚠";
            } else if (type === 'error') {
                toastInner.className = "flex items-center space-x-2.5 px-5 py-2.5 rounded-full shadow-2xl text-xs sm:text-sm font-bold bg-red-700 text-white border-red-500";
                toastIcon.textContent = "🚨";
            } else {
                toastInner.className = "flex items-center space-x-2.5 px-5 py-2.5 rounded-full shadow-2xl text-xs sm:text-sm font-bold bg-slate-800 text-white border-slate-600";
                toastIcon.textContent = "ℹ️";
            }

            toast.classList.remove("-translate-y-12", "opacity-0");
            toast.classList.add("translate-y-0", "opacity-100");

            if (window._toastTimer) clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => {
                toast.classList.remove("translate-y-0", "opacity-100");
                toast.classList.add("-translate-y-12", "opacity-0");
            }, 1800);
        }

        function updateLastActionBar(text) {
            const bar = document.getElementById("lastActionBar");
            const label = document.getElementById("lastActionText");
            label.textContent = text;
            bar.classList.remove("opacity-0", "pointer-events-none");
            bar.classList.add("opacity-100", "pointer-events-auto");
        }

        function hideLastActionBar() {
            const bar = document.getElementById("lastActionBar");
            bar.classList.remove("opacity-100", "pointer-events-auto");
            bar.classList.add("opacity-0", "pointer-events-none");
        }

        function navigate(step) {
            if (allItems.length === 0) return;
            const unjudgedOnly = document.getElementById("unjudgedOnlyCheck").checked;

            if (unjudgedOnly) {
                let nextIdx = currentIndex + step;
                while (nextIdx >= 0 && nextIdx < allItems.length) {
                    if (allItems[nextIdx].is_relevant === "" || allItems[nextIdx].is_relevant === null) {
                        currentIndex = nextIdx;
                        renderCurrentCard();
                        return;
                    }
                    nextIdx += step;
                }
                if (step > 0) {
                    showFloatingToast("Seluruh item yang belum dinilai sudah selesai!", "relevant");
                }
                return;
            }

            const targetIdx = currentIndex + step;
            if (targetIdx >= 0 && targetIdx < allItems.length) {
                currentIndex = targetIdx;
                renderCurrentCard();
            }
        }

        function jumpToFirstUnjudged() {
            const idx = allItems.findIndex(it => it.is_relevant === "" || it.is_relevant === null);
            if (idx !== -1) {
                currentIndex = idx;
                renderCurrentCard();
                showFloatingToast(`Lompat ke item #${idx + 1} (belum dinilai)`, "info");
            } else {
                showFloatingToast("Semua item pada dataset ini sudah dinilai!", "relevant");
            }
        }

        function jumpToSelectedQuery() {
            const select = document.getElementById("queryJumpSelect");
            const idx = parseInt(select.value, 10);
            if (!isNaN(idx) && idx >= 0 && idx < allItems.length) {
                currentIndex = idx;
                renderCurrentCard();
            }
        }

        function syncQueryDropdownSelection(currentQid) {
            const select = document.getElementById("queryJumpSelect");
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].textContent.startsWith(currentQid)) {
                    select.selectedIndex = i;
                    break;
                }
            }
        }

        function toggleUnjudgedOnly() {
            const unjudgedOnly = document.getElementById("unjudgedOnlyCheck").checked;
            if (unjudgedOnly) {
                if (allItems[currentIndex].is_relevant !== "" && allItems[currentIndex].is_relevant !== null) {
                    navigate(1);
                }
            }
        }

        function changeDataset() {
            const select = document.getElementById("datasetSelect");
            activeDataset = select.value;
            lastAction = null;
            hideLastActionBar();
            loadDatasetData();
        }

        function toggleModal(modalId) {
            const el = document.getElementById(modalId);
            el.classList.toggle("hidden");
        }

        function setupKeyboardShortcuts() {
            window.addEventListener("keydown", (e) => {
                if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") {
                    return;
                }

                // Ctrl+Z untuk Undo
                if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z")) {
                    e.preventDefault();
                    undoLastAction();
                    return;
                }

                if (e.key === "1") {
                    e.preventDefault();
                    setVerdict(1);
                } else if (e.key === "0") {
                    e.preventDefault();
                    setVerdict(0);
                } else if (e.key === "r" || e.key === "R") {
                    e.preventDefault();
                    toggleRagu();
                } else if (e.key === "Backspace" || e.key === "Delete") {
                    e.preventDefault();
                    resetCurrentVerdict();
                } else if (e.key === "z" || e.key === "Z") {
                    e.preventDefault();
                    undoLastAction();
                } else if (e.key === "m" || e.key === "M") {
                    e.preventDefault();
                    toggleSound();
                } else if (e.key === "ArrowLeft" || e.key === "[") {
                    e.preventDefault();
                    navigate(-1);
                } else if (e.key === "ArrowRight" || e.key === "]") {
                    e.preventDefault();
                    navigate(1);
                } else if (e.key === "u" || e.key === "U") {
                    e.preventDefault();
                    jumpToFirstUnjudged();
                } else if (e.key === "?") {
                    e.preventDefault();
                    toggleModal("guideModal");
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Halaman utama pelabel relevansi."""
    active_dataset = request.args.get("dataset", "relevance_pool.csv")
    if active_dataset not in DATASET_CONFIG:
        active_dataset = "relevance_pool.csv"
    return render_template_string(
        HTML_TEMPLATE,
        datasets=DATASET_CONFIG,
        active_dataset=active_dataset,
    )


@app.route("/api/data")
def api_get_data():
    """Ambil data item dari berkas CSV yang dipilih beserta statistik."""
    dataset_name = request.args.get("dataset", "relevance_pool.csv")
    file_path = get_dataset_path(dataset_name)

    if not file_path.is_file():
        return jsonify({"error": f"Berkas tidak ditemukan: {file_path.name}"}), 404

    fieldnames, rows = read_pool_csv(file_path)

    judged = 0
    relevant = 0
    irrelevant = 0
    ragu = 0

    for r in rows:
        val = str(r.get("is_relevant", "")).strip()
        rg = str(r.get("ragu", "")).strip()
        if val in ["1", "0"]:
            judged += 1
            if val == "1":
                relevant += 1
            elif val == "0":
                irrelevant += 1
        if rg == "1":
            ragu += 1

    return jsonify({
        "dataset": dataset_name,
        "items": rows,
        "stats": {
            "total": len(rows),
            "judged": judged,
            "relevant": relevant,
            "irrelevant": irrelevant,
            "ragu": ragu,
        }
    })


@app.route("/api/save", methods=["POST"])
def api_save_item():
    """Simpan keputusan penilaian (is_relevant, ragu, notes) langsung ke berkas CSV."""
    payload = request.get_json() or {}
    dataset_name = payload.get("dataset", "relevance_pool.csv")
    file_path = get_dataset_path(dataset_name)

    if not file_path.is_file():
        return jsonify({"success": False, "error": "Berkas tidak ditemukan"}), 404

    index = payload.get("index")
    query_id = payload.get("query_id")
    archive_id = payload.get("archive_id")
    is_relevant = str(payload.get("is_relevant", "")).strip()
    ragu = str(payload.get("ragu", "")).strip()
    notes = str(payload.get("notes", "")).strip()

    fieldnames, rows = read_pool_csv(file_path)

    matched_row: Optional[Dict[str, str]] = None
    if index is not None and 0 <= int(index) < len(rows):
        r = rows[int(index)]
        if r.get("query_id") == query_id and str(r.get("archive_id")) == str(archive_id):
            matched_row = r

    if not matched_row:
        for r in rows:
            if r.get("query_id") == query_id and str(r.get("archive_id")) == str(archive_id):
                matched_row = r
                break

    if not matched_row:
        return jsonify({"success": False, "error": "Baris item tidak ditemukan dalam berkas"}), 404

    # Update nilai baris
    matched_row["is_relevant"] = is_relevant
    matched_row["ragu"] = ragu

    notes_col = DATASET_CONFIG.get(dataset_name, {}).get("notes_col", "auditor_notes")
    if notes_col in matched_row:
        matched_row[notes_col] = notes
    elif "auditor_notes" in matched_row:
        matched_row["auditor_notes"] = notes
    elif "archivist_notes" in matched_row:
        matched_row["archivist_notes"] = notes

    write_pool_csv(file_path, fieldnames, rows)

    judged = sum(1 for r in rows if str(r.get("is_relevant", "")).strip() in ["1", "0"])
    relevant = sum(1 for r in rows if str(r.get("is_relevant", "")).strip() == "1")
    irrelevant = sum(1 for r in rows if str(r.get("is_relevant", "")).strip() == "0")
    ragu_count = sum(1 for r in rows if str(r.get("ragu", "")).strip() == "1")

    return jsonify({
        "success": True,
        "stats": {
            "total": len(rows),
            "judged": judged,
            "relevant": relevant,
            "irrelevant": irrelevant,
            "ragu": ragu_count,
        }
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Jalankan server aplikasi pelabel relevansi.")
    parser.add_argument("--port", type=int, default=5000, help="Port server web (default: 5000)")
    parser.add_argument("--host", default="127.0.0.1", help="Host server web (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Jangan buka browser otomatis")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print("=" * 65)
    print("  APLIKASI PELABEL RELEVANSI TEMU KEMBALI ARSIP")
    print("=" * 65)
    print(f"[*] Server berjalan di: {url}")
    print("[*] Berkas aktif default: output/relevance_pool.csv")
    print("[*] Tekan Ctrl + C di terminal untuk menghentikan server.")
    print("=" * 65)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
