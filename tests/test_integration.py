import sys
import os
# Add current dir to path
sys.path.append(os.getcwd())

from core.logic import logic
from core.odoo import odoo_client

def test_integration():
    try:
        print("Testing Odoo Connection...")
        uid = odoo_client.authenticate()
        print(f"Authenticated UID: {uid}")

        print("\nTesting Product Clustering...")
        clusters = logic.cluster_products()
        print(f"Found {len(clusters)} product clusters.")
        
        # Print a few clusters
        for i, (l_id, cluster) in enumerate(clusters.items()):
            if i > 5: break
            print(f"Cluster {l_id}: {cluster['canonical_name']} ({len(cluster['product_ids'])} items)")

        print("\nTesting Analytic Comparison...")
        # Use first two account IDs for testing if available
        accounts = odoo_client.execute_kw('account.analytic.account', 'search_read', [[]], {'limit': 2})
        if accounts:
            acc_ids = [a['id'] for a in accounts]
            comparison = logic.compare_costs(acc_ids)
            print(f"Comparison Result: {len(comparison)} accounts analyzed.")
            print(json.dumps(comparison, indent=2))

        print("\nIntegration test PASSED!")

    except Exception as e:
        print(f"Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import json
    test_integration()
