import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from thefuzz import fuzz, process
from core.odoo import odoo_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessLogic:
    RULES = {
        'Paneles': ['mgs', 'mgs_0040', 'panel', 'modulo', 'módulo', 'monocristalino', 'policristalino'],
        'Seguros / Pólizas': ['poliza', 'póliza', 'seguro'],
        'Transporte / Fletes': ['flete', 'transporte', 'envio', 'envío', 'acarreo'],
        'Inversores': ['inversor', 'inverter'],
        'Cables': ['cable', 'solar dc', 'solar ac', 'conductor', 'awg'],
        'Estructura': ['estructura', 'perfil', 'soporte', 'riel', 'clamp', 'esparrago', 'esparragos', 'espárrago'],
        'Protecciones': ['breaker', 'fusible', 'dps', 'proteccion', 'protección', 'tablero', 'terminal'],
        'Transformadores': ['transformador', 'trafo'],
        'Medición': ['medidor', 'analizador', 'meter']
    }


    def get_analytic_lines(self, account_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Fetch analytic lines, optionally filtered by accounts."""
        domain = []
        if account_ids:
            domain = [['account_id', 'in', account_ids]]
        
        return odoo_client.execute_kw(
            'account.analytic.line', 'search_read',
            [domain],
            {'fields': ['id', 'name', 'account_id', 'product_id', 'amount', 'unit_amount', 'date', 'partner_id', 'move_line_id', 'ref'], 'limit': 0}
        )

    def get_category_manual(self, name: str) -> str:
        """Categorize a name based on manual rules."""
        name_lower = name.lower()
        for cat, keywords in self.RULES.items():
            if any(k in name_lower for k in keywords):
                return cat
        return ""

    def compare_costs(self, account_ids: List[int]):
        """
        Compare costs between multiple analytical accounts using normalized products.
        """
        lines = self.get_analytic_lines(account_ids)
        comparison = {}
        
        for line in lines:
            if not line.get('account_id'):
                continue
                
            account_id, account_name = line['account_id']
            p_id = line['product_id'][0] if line.get('product_id') else None
            
            if not p_id:
                logical_name = "Otro"
            else:
                display_name = line['product_id'][1]
                cat = self.get_category_manual(display_name)
                logical_name = cat if cat else display_name

            if account_name not in comparison:
                comparison[account_name] = {}
            
            if logical_name not in comparison[account_name]:
                comparison[account_name][logical_name] = 0
            
            comparison[account_name][logical_name] += (line.get('amount') or 0)

        return comparison

    def get_category_lines(self, account_ids: List[int], category_name: str) -> List[Dict[str, Any]]:
        """
        Return the raw analytic lines that belong to a specific standardized category name.
        """
        lines = self.get_analytic_lines(account_ids)
        filtered_lines = []
        
        for line in lines:
            if not line.get('account_id'):
                continue
                
            p_id = line['product_id'][0] if line.get('product_id') else None
            
            if not p_id:
                logical_name = "Otro"
            else:
                display_name = line['product_id'][1]
                cat = self.get_category_manual(display_name)
                logical_name = cat if cat else display_name
                    
            if logical_name == category_name:
                filtered_lines.append(line)
                
        return filtered_lines

logic = BusinessLogic()
