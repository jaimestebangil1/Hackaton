import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.odoo import odoo_client

# Fetch one analytic line to see its structure
line = odoo_client.execute_kw('account.analytic.line', 'search_read', [[]], {'limit': 1})
if line:
    print(line[0].keys())
    print("\nSample Data:")
    for k, v in line[0].items():
        if k in ['name', 'ref', 'move_id', 'move_line_id']:
            print(f"{k}: {v}")
