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
            domain, {'fields': ['id', 'name', 'account_id', 'product_id', 'amount', 'unit_amount', 'date']}
        )

    def cluster_products(self, threshold: int = 85):
        """
        Group similar products based on their names.
        This is the 'CLEANING' part of the challenge.
        """
        products = self.get_all_products()
        names = [p['name'] for p in products]
        id_to_name = {p['id']: p['name'] for p in products}
        
        clusters = []
        visited = set()

        for p in products:
            if p['id'] in visited:
                continue
            
            # Simple clustering: find all products similar to this one
            current_name = p['name']
            cluster = [p['id']]
            visited.add(p['id'])
            
            # Find matches in remaining names
            for other in products:
                if other['id'] in visited:
                    continue
                
                score = fuzz.token_sort_ratio(current_name, other['name'])
                if score >= threshold:
                    cluster.append(other['id'])
                    visited.add(other['id'])
            
            clusters.append({
                'canonical_name': current_name,
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
            account_id, account_name = line['account_id']
            # line['product_id'] is [id, name]
            p_id = line['product_id'][0] if line['product_id'] else None
            
            if not p_id:
                continue
                
            logical_id = self.canonical_map.get(p_id)
            if logical_id is None:
                # If product wasn't in template scan, skip or handle as its own
                logical_name = line['product_id'][1]
            else:
                logical_name = self.logical_entities[logical_id]['canonical_name']

            if account_name not in comparison:
                comparison[account_name] = {}
            
            if logical_name not in comparison[account_name]:
                comparison[account_name][logical_name] = 0
            
            comparison[account_name][logical_name] += line['amount']

        return comparison

logic = BusinessLogic()
