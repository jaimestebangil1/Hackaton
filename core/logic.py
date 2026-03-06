import json
import logging
from typing import List, Dict, Any, Tuple
from thefuzz import fuzz, process
from core.odoo import odoo_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessLogic:
    def __init__(self):
        self.canonical_map = {} # productId -> logicalId
        self.logical_entities = {} # logicalId -> {name, productIds}

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Fetch all products from Odoo."""
        return odoo_client.execute_kw(
            'product.template', 'search_read',
            [[]], {'fields': ['id', 'name', 'default_code']}
        )

    def get_analytic_lines(self, account_ids: List[int] = None) -> List[Dict[str, Any]]:
        """Fetch analytic lines, optionally filtered by accounts."""
        domain = []
        if account_ids:
            domain = [['account_id', 'in', account_ids]]
        
        return odoo_client.execute_kw(
            'account.analytic.line', 'search_read',
            [domain], # Must be a list of positional args, where the first is the domain list
            {'fields': ['id', 'name', 'account_id', 'product_id', 'amount', 'unit_amount', 'date']}
        )

    def cluster_products(self, threshold: int = 80):
        """
        Group similar products based on their names.
        Improved to handle 'panel solar' and similar equipment variations.
        """
        products = self.get_all_products()
        # Pre-process names for better matching
        processed_products = []
        for p in products:
            processed_name = p['name'].lower().strip()
            # Remove common prefixes like [P0001]
            if processed_name.startswith('['):
                parts = processed_name.split(']', 1)
                if len(parts) > 1:
                    processed_name = parts[1].strip()
            processed_products.append({'id': p['id'], 'name': p['name'], 'p_name': processed_name})

        clusters = []
        visited = set()

        for p in processed_products:
            if p['id'] in visited:
                continue
            
            current_p_name = p['p_name']
            cluster = [p['id']]
            visited.add(p['id'])
            
            for other in processed_products:
                if other['id'] in visited:
                    continue
                
                # Check for direct inclusion for important keywords
                is_manual_match = False
                if 'panel' in current_p_name and 'panel' in other['p_name']:
                    # If both have 'panel' and 'solar', higher chance of matching
                    if 'solar' in current_p_name and 'solar' in other['p_name']:
                        is_manual_match = True
                
                score = fuzz.token_sort_ratio(current_p_name, other['p_name'])
                if score >= threshold or is_manual_match:
                    cluster.append(other['id'])
                    visited.add(other['id'])
            
            clusters.append({
                'canonical_name': p['name'], # Keep original for display
                'product_ids': cluster
            })

        # Build mapping for later use
        self.logical_entities = {i: c for i, c in enumerate(clusters)}
        self.canonical_map = {}
        for logical_id, cluster in self.logical_entities.items():
            for product_id in cluster['product_ids']:
                self.canonical_map[product_id] = logical_id
        
        return self.logical_entities

    def compare_costs(self, account_ids: List[int]):
        """
        Compare costs between multiple analytical accounts using normalized products.
        """
        if not self.logical_entities:
            self.cluster_products()

        lines = self.get_analytic_lines(account_ids)
        
        # Result structure: { account_name: { logical_name: total_amount } }
        comparison = {}
        
        for line in lines:
            # line['account_id'] can be [id, name] or False
            if not line.get('account_id'):
                continue
                
            account_id, account_name = line['account_id']
            # line['product_id'] is [id, name] or False
            p_id = line['product_id'][0] if line.get('product_id') else None
            
            if not p_id:
                # Use a generic name for costs without a specific product
                logical_name = "Otros / Gastos Generales"
            else:
                logical_id = self.canonical_map.get(p_id)
                if logical_id is None:
                    # If product wasn't in template scan, use its display name from the line
                    logical_name = line['product_id'][1]
                else:
                    logical_name = self.logical_entities[logical_id]['canonical_name']

            if account_name not in comparison:
                comparison[account_name] = {}
            
            if logical_name not in comparison[account_name]:
                comparison[account_name][logical_name] = 0
            
            comparison[account_name][logical_name] += (line.get('amount') or 0)

        return comparison

logic = BusinessLogic()
