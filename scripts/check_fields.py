import json
from core.odoo import odoo_client

def check_fields():
    try:
        print("Checking fields for account.analytic.line...")
        fields = odoo_client.execute_kw('account.analytic.line', 'fields_get', [], {'attributes': ['string', 'type', 'searchable']})
        
        # Look for fields related to 'Account' or 'Analytic'
        relevant_fields = {k: v for k, v in fields.items() if 'account' in k.lower()}
        print(f"Relevant fields: {json.dumps(relevant_fields, indent=2)}")
        
        # Also check if 'account_id' is specifically searchable
        if 'account_id' in fields:
            print(f"\n'account_id' details: {fields['account_id']}")
        else:
            print("\n'account_id' NOT FOUND in fields!")

    except Exception as e:
        print(f"Error checking fields: {e}")

if __name__ == "__main__":
    check_fields()
