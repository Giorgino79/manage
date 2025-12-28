#!/usr/bin/env python
"""
Test rapido per verificare che l'export Excel funzioni
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'management.settings')
django.setup()

print("Testing Excel Export...")

from core.excel_generator import generate_excel_from_data, ExcelConfig

# Dati di test
data = [
    {'Nome': 'Mario Rossi', 'Età': 30, 'Stipendio': 2500.50},
    {'Nome': 'Luigi Verdi', 'Età': 25, 'Stipendio': 2200.00},
    {'Nome': 'Anna Bianchi', 'Età': 35, 'Stipendio': 3000.75},
]

config = ExcelConfig(
    filename='test_export.xlsx',
    sheet_name='Test',
    auto_fit_columns=True,
    add_filters=True
)

try:
    # Test export to file
    result = generate_excel_from_data(
        data=data,
        config=config,
        output_type='file',
        output_path='/tmp/test_export.xlsx'
    )

    print(f"✓ Excel file created: {result}")

    # Verifica che il file esista
    if os.path.exists(result):
        file_size = os.path.getsize(result)
        print(f"✓ File size: {file_size} bytes")

        # Rimuovi file di test
        os.remove(result)
        print("✓ Test file cleaned up")
    else:
        print("✗ File not found!")
        sys.exit(1)

    print("\n✓ Excel export test PASSED!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
