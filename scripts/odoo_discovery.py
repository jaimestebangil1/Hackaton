import xmlrpc.client
import os
from dotenv import load_dotenv

# Hardcoded for initial test as requested, but normally would use .env
URL = "https://solenium-13-02-2026-28613487.dev.odoo.com/"
DB = "solenium-13-02-2026-28613487"
USER = "juliana@solenium.co"
API_KEY = "998c192c7e52f4934fce36802af40dd9f3d59fbe"

def run_discovery():
    try:
        print(f"Connecting to {URL}...")
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        version = common.version()
        print(f"Odoo Version: {version.get('server_version')}")

        uid = common.authenticate(DB, USER, API_KEY, {})
        if not uid:
            print("Authentication failed!")
            return

        print(f"Authenticated successfully. UID: {uid}")

        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        # 1. Sample product.template
        print("\n--- Sampling 100 product.template ---")
        products = models.execute_kw(DB, uid, API_KEY, 'product.template', 'search_read', 
                                    [[]], {'fields': ['id', 'name', 'default_code', 'list_price'], 'limit': 100})
        
        import json
        with open('product_samples.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=4)
        print(f"Dumped {len(products)} products to product_samples.json")

        # 2. Sample account.analytic.line
        print("\n--- Sampling 50 account.analytic.line ---")
        analytic_lines = models.execute_kw(DB, uid, API_KEY, 'account.analytic.line', 'search_read', 
                                          [[]], {'fields': ['id', 'name', 'account_id', 'product_id', 'amount', 'unit_amount', 'date'], 'limit': 50})
        with open('analytic_samples.json', 'w', encoding='utf-8') as f:
            json.dump(analytic_lines, f, ensure_ascii=False, indent=4)
        print(f"Dumped {len(analytic_lines)} analytic lines to analytic_samples.json")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_discovery()
