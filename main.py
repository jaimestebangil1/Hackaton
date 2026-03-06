import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
from core.logic import logic
from core.odoo import odoo_client

app = FastAPI(title="Odoo-IA-Analytic-Assistant")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class ComparisonRequest(BaseModel):
    account_ids: List[int]

class ChatRequest(BaseModel):
    message: str
    context_accounts: List[int] = []

@app.get("/")
async def root():
    return {"status": "ok", "message": "Odoo-IA-Analytic-Assistant is running"}

@app.get("/api/products")
async def get_products():
    return logic.get_all_products()

@app.get("/api/accounts")
async def get_accounts():
    """Fetch analytic accounts for the frontend selector."""
    return odoo_client.execute_kw(
        'account.analytic.account', 'search_read',
        [[]], {'fields': ['id', 'name']}
    )

@app.post("/api/analysis/compare")
async def compare_costs(req: ComparisonRequest):
    return logic.compare_costs(req.account_ids)

@app.post("/api/chat")
async def chat_interaction(req: ChatRequest):
    """
    Simulated AI assistant. It analyzes the comparative data to answer questions.
    """
    if not req.context_accounts:
        return {"response": "Por favor, selecciona al menos una cuenta analítica para analizar."}
    
    data = logic.compare_costs(req.context_accounts)
    
    # Simple logic-based "AI" response
    # In a real scenario, this would go to an LLM with the 'data' as context.
    response = ""
    if "compara" in req.message.lower() or "diferencia" in req.message.lower():
        response = "Analizando la comparativa de costos...\n\n"
        for account, costs in data.items():
            total = sum(costs.values())
            response += f"- **{account}**: Total acumulado de {total:,.2f} COP.\n"
        
        # Find the most expensive common item
        items = {}
        for account, costs in data.items():
            for item, amt in costs.items():
                if item not in items: items[item] = 0
                items[item] += abs(amt)
        
        top_item = max(items, key=items.get) if items else "N/A"
        response += f"\nEl costo más significativo detectado es **{top_item}**."
    else:
        response = "¿En qué puedo ayudarte con el análisis de costos? Puedo comparar cuentas analíticas y detectar desviaciones en productos normalizados."

    return {"response": response, "data": data}

@app.get("/app", response_class=HTMLResponse)
async def get_app():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
