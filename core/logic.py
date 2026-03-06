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

    def get_all_products(self, limit: int = 2000) -> List[Dict[str, Any]]:
        """Fetch all products from Odoo."""
        return odoo_client.execute_kw(
            'product.template', 'search_read',
            [[]], {'fields': ['id', 'name', 'default_code'], 'limit': limit}
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

    def get_category_manual(self, name: str) -> str:
        """Categorize a name based on manual rules."""
        RULES = {
            'Paneles': ['panel', 'modulo', 'módulo', 'monocristalino', 'policristalino'],
            'Inversores': ['inversor', 'inverter'],
            'Cables': ['cable', 'solar dc', 'solar ac', 'conductor', 'awg'],
            'Estructura': ['estructura', 'perfil', 'soporte', 'riel', 'clamp'],
            'Protecciones': ['breaker', 'fusible', 'dps', 'proteccion', 'protección', 'tablero', 'terminal'],
            'Transformadores': ['transformador', 'trafo'],
            'Medición': ['medidor', 'analizador', 'meter']
        }
        name_lower = name.lower()
        for cat, keywords in RULES.items():
            if any(k in name_lower for k in keywords):
                return cat
        return None

    def cluster_products(self, threshold: int = 80):
        """
        Group similar products based on their names.
        Aggressively consolidates key solar equipment into broad categories.
        """
        self.logical_entities = {}
        self.canonical_map = {}
        
        products = self.get_all_products()
        
        # Pre-process names and categorize
        processed_products = []
        for p in products:
            processed_name = p['name'].lower().strip()
            if processed_name.startswith('['):
                parts = processed_name.split(']', 1)
                if len(parts) > 1:
                    processed_name = parts[1].strip()
            
            category = self.get_category_manual(processed_name)
            processed_products.append({
                'id': p['id'], 
                'name': p['name'], 
                'p_name': processed_name,
                'category': category
            })

        clusters = []
        visited = set()

        # Step 1: Cluster by Category
        categories = ['Paneles', 'Inversores', 'Cables', 'Estructura', 'Protecciones', 'Transformadores', 'Medición']
        for cat in categories:
            cat_ids = [p['id'] for p in processed_products if p['category'] == cat]
            if cat_ids:
                clusters.append({
                    'canonical_name': cat,
                    'product_ids': cat_ids
                })
                visited.update(cat_ids)

        # Step 2: Cluster remaining products by Fuzzy matching
        for p in processed_products:
            if p['id'] in visited:
                continue
            
            current_p_name = p['p_name']
            cluster = [p['id']]
            visited.add(p['id'])
            
            for other in processed_products:
                if other['id'] in visited:
                    continue
                
                score = fuzz.token_sort_ratio(current_p_name, other['p_name'])
                if score >= threshold:
                    cluster.append(other['id'])
                    visited.add(other['id'])
            
            clusters.append({
                'canonical_name': p['name'],
                'product_ids': cluster
            })

        # Step 3: Populate Maps
        for i, cluster_data in enumerate(clusters):
            logical_id = i
            self.logical_entities[logical_id] = {
                'canonical_name': cluster_data['canonical_name'],
                'product_ids': cluster_data['product_ids']
            }
            for p_id in cluster_data['product_ids']:
                self.canonical_map[p_id] = logical_id

        return self.logical_entities

    def compare_costs(self, account_ids: List[int]):
        """
        Compare costs between multiple analytical accounts using normalized products.
        """
        if not self.logical_entities:
            self.cluster_products()

        lines = self.get_analytic_lines(account_ids)
        comparison = {}
        
        for line in lines:
            if not line.get('account_id'):
                continue
                
            account_id, account_name = line['account_id']
            p_id = line['product_id'][0] if line.get('product_id') else None
            
            if not p_id:
                logical_name = "Otros / Gastos Generales"
            else:
                logical_id = self.canonical_map.get(p_id)
                if logical_id is None:
                    # Fallback: Try manual categorization
                    display_name = line['product_id'][1]
                    cat = self.get_category_manual(display_name)
                    logical_name = cat if cat else display_name
                else:
                    logical_name = self.logical_entities[logical_id]['canonical_name']

            if account_name not in comparison:
                comparison[account_name] = {}
            
            if logical_name not in comparison[account_name]:
                comparison[account_name][logical_name] = 0
            
            comparison[account_name][logical_name] += (line.get('amount') or 0)

        return comparison

logic = BusinessLogic()
