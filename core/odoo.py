import os
import xmlrpc.client
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

class OdooClient:
    def __init__(self):
        self.url = os.getenv('ODOO_URL')
        self.db = os.getenv('ODOO_DB')
        self.username = os.getenv('ODOO_USERNAME')
        # In Odoo XML-RPC, password can be the API Key
        self.password = os.getenv('ODOO_API_KEY') or os.getenv('ODOO_PASSWORD')
        self._uid = None

    def get_common(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    def get_object(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def authenticate(self):
        if self._uid:
            return self._uid
        
        common = self.get_common()
        try:
            self._uid = common.authenticate(self.db, self.username, self.password, {})
            if not self._uid:
                raise HTTPException(status_code=401, detail="Odoo authentication failed")
            return self._uid
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error connecting to Odoo: {str(e)}")

    def execute_kw(self, model, method, args, kwargs={}):
        uid = self.authenticate()
        models = self.get_object()
        try:
            return models.execute_kw(self.db, uid, self.password, model, method, args, kwargs)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Odoo error in {model}.{method}: {str(e)}")

odoo_client = OdooClient()
