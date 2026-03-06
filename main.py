import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
from core.logic import logic
from core.odoo import odoo_client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Odoo-IA-Analytic-Assistant")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class ComparisonRequest(BaseModel):
    account_ids: List[int]

class ChatRequest(BaseModel):
    message: str
    context_accounts: List[int] = []

class DetailsRequest(BaseModel):
    account_ids: List[int]
    category_name: str

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

@app.post("/api/analysis/details")
async def get_details(req: DetailsRequest):
    """Fetch raw raw analytic lines that make up a logical category."""
    lines = logic.get_category_lines(req.account_ids, req.category_name)
    # Format dates and ensure safe serialization
    return {"lines": lines}

@app.post("/api/chat")
async def chat_interaction(req: ChatRequest):
    """
    Simulated AI assistant. It analyzes the comparative data to answer questions.
    """
    try:
        if not req.context_accounts:
            return {"response": "Por favor, selecciona al menos una cuenta analítica a la izquierda para poder analizar los costos."}
        
        data = logic.compare_costs(req.context_accounts)
        
        msg = req.message.lower()
        response = ""
        
        # Keywords for analysis
        if any(k in msg for k in ["compara", "diferencia", "costo", "más", "alto", "mayor"]):
            response = "He analizado los costos de las cuentas seleccionadas. Aquí tienes los hallazgos:\n\n"
            
            summary_parts = []
            all_items_summary = {}
            filtered_data = {}

            # Identify keywords in message to filter products
            # Strip punctuation and use lowercase
            import re
            words = re.findall(r'\b\w{4,}\b', msg.lower())
            
            ignore_words = {"compara", "diferencia", "costo", "costos", "cuenta", "sobre", "solo", "solamente", 
                            "muéstrame", "muesltra", "trae", "producto", "especifico", "específico", 
                            "totales", "consolidados", "actualizar", "análisis", "todos", "tabla", "ver"}
            
            keywords = [w for w in words if w not in ignore_words]

            for account, costs in data.items():
                filtered_account_costs = {}
                for item, amt in costs.items():
                    # If no keywords remain (generic search), include everything
                    # If keywords exist, strictly filter by finding ANY keyword in the product name
                    if not keywords or any(k in item.lower() for k in keywords):
                        filtered_account_costs[item] = amt
                        all_items_summary[item] = all_items_summary.get(item, 0) + abs(amt)
                
                filtered_data[account] = filtered_account_costs
                summary_parts.append(f"- **{account}**: {len(filtered_account_costs)} productos analizados")
            
            response += "\n".join(summary_parts) + "\n\n"
            
            if all_items_summary:
                top_item = max(all_items_summary, key=lambda k: all_items_summary[k])
                response += f"El componente con **mayor impacto económico** es **{top_item}**.\n"
                if keywords:
                    response += f"\n*Nota: Los datos mostrados abajo están filtrados por términos relacionados a tu consulta.*"
            else:
                response += "No se detectaron costos significativos en estas cuentas.\n"
                
            return {"response": response, "data": filtered_data}
        else:
            response = "¿En qué puedo ayudarte con el análisis de costos? Prueba preguntando: '¿Cuál es la diferencia de costos entre los proyectos?' o '¿Qué productos tienen más costo?'"
            # If no specific keywords for analysis, return original data or a default view
            # For now, let's return the original data if no specific filter was applied
            return {"response": response, "data": data}
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return {"response": f"Lo siento, ocurrió un error interno al procesar tu consulta: {str(e)}", "data": {}}

@app.get("/app", response_class=HTMLResponse)
async def get_app():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
