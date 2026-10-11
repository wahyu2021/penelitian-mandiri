import os
import sys

# Pastikan paket `core` dapat diimpor saat pytest dijalankan dari mana pun.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
