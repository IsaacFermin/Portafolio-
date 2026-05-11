"""
================================================================================
  PAAR-SV — Servidor Python (FastAPI)
  ────────────────────────────────────────────────────────────────────────────
================================================================================
"""
#Versión sin Keys

import os
import sys
import threading
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from supabase import create_client, Client

# Motor analítico — importación lazy
try:
    from paar_sv_motor_analitico import MotorAnaliticoPAARSV
    MOTOR_DISPONIBLE = True
except ImportError:
    MOTOR_DISPONIBLE = False

# ── Configuración Supabase ────────────────────────────────────────────────────
SUPABASE_URL = "https://dduxtzvxvyipfblsnrwr.supabase.co"
SUPABASE_KEY = (
    "k"
)

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── HTML a servir ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "paar-sv-python.html")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="PAAR-SV API",
    description="Backend Python para la Plataforma Analítica de Atención de Reclamaciones",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # En producción restringir al dominio de la app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# SERVIR EL HTML
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Sirve el HTML leyendo el archivo en cada request — sin caché."""
    if not os.path.exists(HTML_FILE):
        return JSONResponse(
            status_code=404,
            content={"error": f"No se encontró {HTML_FILE}"}
        )
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        contenido = f.read()
    return HTMLResponse(
        content=contenido,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma":        "no-cache",
            "Expires":       "0",
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL: Ejecutor de queries genérico
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/query")
async def handle_query(request: Request):
    """
    Recibe un descriptor de query JSON desde el shim JS y lo ejecuta
    en Supabase usando el cliente Python.

    Formato del payload (enviado por el QueryBuilder del shim):
    {
        "table":   "casos",
        "op":      "select" | "insert" | "update" | "upsert",
        "select":  "id, nombre, *",
        "filters": [
            {"op": "eq",    "col": "estado",    "val": "pendiente"},
            {"op": "gte",   "col": "dias",      "val": 30},
            {"op": "not",   "col": "estado",    "filter_op": "eq", "val": "cerrado"},
            {"op": "or",    "expr": "id_caso.eq.X,cedula.eq.X"},
            {"op": "ilike", "col": "nombre",    "val": "%juan%"}
        ],
        "order":   {"col": "fecha_hora", "ascending": false},
        "limit":   10,
        "single":  true,
        "count":   "exact",
        "head":    true,
        "data":    {... objeto a insertar/actualizar ...}
    }

    Respuesta (mismo formato que Supabase JS):
    {
        "data":  {...} | [{...}] | null,
        "error": null | {"message": "..."},
        "count": null | int
    }
    """
    try:
        payload = await request.json()
        result = _ejecutar_query(payload)
        return result
    except Exception as e:
        print(f"[PAAR-SV /api/query] Error inesperado: {e}")
        return {"data": None, "error": {"message": str(e)}, "count": None}


def _ejecutar_query(payload: dict) -> dict:
    """
    Traduce el descriptor JSON a llamadas del cliente supabase-py.

    Maneja todas las operaciones que usa el HTML:
      SELECT  — con filtros, orden, límite, single, count
      INSERT  — con o sin returning
      UPDATE  — con filtros
      UPSERT  — para storage-like operations
    """
    table   = payload["table"]
    op      = payload.get("op", "select")
    select  = payload.get("select", "*")
    filters = payload.get("filters", [])
    order   = payload.get("order")
    limit   = payload.get("limit")
    single  = payload.get("single", False)
    count   = payload.get("count")          # "exact" | None
    data    = payload.get("data")           # para insert / update

    # ── Construir query base ──────────────────────────────────────
    if op == "insert":
        qb = db.table(table).insert(data)

    elif op == "update":
        qb = db.table(table).update(data)

    elif op == "upsert":
        qb = db.table(table).upsert(data)

    else:  # "select" (default)
        if count == "exact":
            qb = db.table(table).select(select, count="exact")
        else:
            qb = db.table(table).select(select)

    # ── Aplicar filtros ───────────────────────────────────────────
    for f in filters:
        fop = f.get("op")
        col = f.get("col", "")
        val = f.get("val")

        if fop == "eq":
            qb = qb.eq(col, val)
        elif fop == "neq":
            qb = qb.neq(col, val)
        elif fop == "gt":
            qb = qb.gt(col, val)
        elif fop == "gte":
            qb = qb.gte(col, val)
        elif fop == "lt":
            qb = qb.lt(col, val)
        elif fop == "lte":
            qb = qb.lte(col, val)
        elif fop == "ilike":
            qb = qb.ilike(col, val)
        elif fop == "or":
            # Ej: "id_caso.eq.X,cedula.eq.X" → OR filter de PostgREST
            qb = qb.or_(f["expr"])
        elif fop == "not":
            # .not('estado', 'eq', 'cerrado') → PostgREST: not.eq
            filter_op = f.get("filter_op", "eq")
            qb = qb.filter(col, f"not.{filter_op}", val)

    # ── Orden (solo para SELECT) ──────────────────────────────────
    if order and op not in ("insert", "update", "upsert"):
        qb = qb.order(order["col"], desc=not order.get("ascending", True))

    # ── Límite (solo para SELECT) ─────────────────────────────────
    if limit and op not in ("insert", "update", "upsert"):
        qb = qb.limit(limit)

    # ── Ejecutar ──────────────────────────────────────────────────
    result = qb.execute()
    rows   = result.data or []
    cnt    = getattr(result, "count", None)

    # ── Normalizar respuesta ──────────────────────────────────────
    if op in ("insert", "update", "upsert"):
        # Siempre retorna la fila modificada como lista
        out_data = rows[0] if (single and rows) else rows

    elif single:
        out_data = rows[0] if rows else None

    else:
        out_data = rows

    return {
        "data":  out_data,
        "error": None,
        "count": cnt,
    }


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE: Subida de evidencias fotográficas
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/storage/upload")
async def upload_file(
    file:   UploadFile = File(...),
    bucket: str        = Form(...),
    path:   str        = Form(...),
):
    """
    Recibe un archivo desde el formulario del Panel 2 y lo sube
    al bucket de Supabase Storage.

    Equivale al bloque JS:
        await db.storage.from('evidencias').upload(ruta, archivo, { upsert: true })
    """
    try:
        contenido = await file.read()
        # supabase-py Storage upload
        db.storage.from_(bucket).upload(
            path,
            contenido,
            file_options={"content-type": file.content_type or "application/octet-stream",
                          "upsert": "true"}
        )
        # Construir URL pública
        url_info  = db.storage.from_(bucket).get_public_url(path)
        # supabase-py puede retornar str o dict según la versión
        public_url = url_info if isinstance(url_info, str) else url_info.get("publicUrl", "")

        return {"data": {"path": path, "publicUrl": public_url}, "error": None}

    except Exception as e:
        print(f"[PAAR-SV Storage] Error: {e}")
        return {"data": None, "error": {"message": str(e)}}


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# ANALÍTICA: Motor estadístico por lotes
# ══════════════════════════════════════════════════════════════════════════════

_analitica_lock = threading.Lock()
_analitica_en_curso = False


@app.get("/api/analitica/ultimo")
async def analitica_ultimo():
    """Retorna las 3 hipótesis del análisis más reciente."""
    try:
        result = db.table("v_ultimo_analisis").select("*").execute()
        rows = result.data or []
        if not rows:
            return {
                "data": [], "error": None, "hint": "sin_datos",
                "mensaje": "No hay análisis guardados. Ejecuta: python paar_sv_motor_analitico.py",
            }
        return {"data": rows, "error": None}
    except Exception as e:
        err_str = str(e)
        print(f"[PAAR-SV /api/analitica/ultimo] Error: {err_str}")
        if any(k in err_str for k in ["v_ultimo_analisis", "does not exist", "relation"]):
            return JSONResponse(status_code=503, content={
                "data": [],
                "error": {
                    "code": "MIGRACION_PENDIENTE",
                    "message": (
                        "La vista v_ultimo_analisis no existe. "
                        "Ejecuta paar_sv_analitico.sql en el editor SQL de Supabase."
                    ),
                },
            })
        return JSONResponse(status_code=500, content={"data": [], "error": {"message": err_str}})


@app.post("/api/analitica/ejecutar")
async def analitica_ejecutar(background_tasks: BackgroundTasks):
    """Dispara el motor analítico en un hilo de fondo."""
    global _analitica_en_curso

    if not MOTOR_DISPONIBLE:
        return JSONResponse(status_code=503, content={
            "status": "error",
            "message": "Motor no disponible. Instala: pip install supabase pandas scipy numpy python-dotenv",
        })
    if _analitica_lock.locked():
        return JSONResponse(status_code=409, content={
            "status": "en_curso",
            "message": "Ya hay un análisis en ejecución. Espera a que termine.",
        })

    def _run_motor():
        global _analitica_en_curso
        with _analitica_lock:
            _analitica_en_curso = True
            try:
                print("[PAAR-SV Motor] Iniciando análisis…")
                motor = MotorAnaliticoPAARSV(dry_run=False)
                motor.ejecutar()
                print("[PAAR-SV Motor] Análisis completado.")
            except Exception as exc:
                print(f"[PAAR-SV Motor] Error: {exc}")
            finally:
                _analitica_en_curso = False

    background_tasks.add_task(_run_motor)
    return {
        "status": "iniciado",
        "message": "Análisis en segundo plano. Consulta /api/analitica/ultimo en ~20 segundos.",
    }


@app.get("/api/analitica/estado")
async def analitica_estado():
    """Indica si hay un análisis en curso."""
    return {
        "en_curso": _analitica_lock.locked(),
        "motor_disponible": MOTOR_DISPONIBLE,
    }


# HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Verifica que el servidor y la conexión a Supabase están activos."""
    try:
        result = db.table("aseguradoras").select("id").limit(1).execute()
        return {
            "status":           "ok",
            "supabase":         "conectado",
            "registros_prueba": len(result.data),
            "motor_analitico":  "disponible" if MOTOR_DISPONIBLE else "no instalado",
        }
    except Exception as e:
        return {"status": "error", "supabase": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# ARRANQUE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  PAAR-SV — Servidor Python")
    print("=" * 60)
    print(f"  HTML:   {HTML_FILE}")
    print(f"  URL:    http://localhost:8000")
    print(f"  Docs:   http://localhost:8000/docs")
    print("=" * 60)

    if not os.path.exists(HTML_FILE):
        print(f"\nAVISO: No se encontró '{HTML_FILE}'.")
        

    uvicorn.run(
        "paar_sv_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          
        reload_includes=["*.py", "*.html"],
    )
