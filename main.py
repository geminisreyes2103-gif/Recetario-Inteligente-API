import os
import sqlite3
from typing import Literal
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from google import genai
from google.genai.errors import APIError
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- CONFIGURACIÓN DE LA BASE DE DATOS SQLITE ---
DB_NAME = "recetas.db"

def init_db():
    """Crea la tabla de recetas si no existe al iniciar la aplicación."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            ingredientes TEXT NOT NULL,
            tiempo_preparacion INTEGER NOT NULL,
            dificultad TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- MODELOS PYDANTIC CON VALIDACIONES ---
class RecetaBase(BaseModel):
    nombre: str = Field(..., min_length=3, description="Nombre de la receta") 
    ingredientes: str = Field(..., min_length=5, description="Lista de ingredientes") 
    tiempo_preparacion: int = Field(..., gt=0, description="Tiempo de preparación en minutos") 
    dificultad: Literal["Fácil", "Media", "Difícil"] = Field(..., description="Nivel de dificultad")

class RecetaCreate(RecetaBase):
    pass

class RecetaResponse(RecetaBase):
    id: int

class ConsultaIA(BaseModel):
    ingredientes_disponibles: str = Field(..., min_length=3, description="Ingredientes que tienes en casa")


# --- INICIALIZACIÓN DE FASTAPI ---
app = FastAPI(title="Recetario Inteligente API", version="1.0.0")


# --- ENDPOINTS CRUD ---

@app.post("/recetas", response_model=RecetaResponse, status_code=status.HTTP_201_CREATED)
def crear_receta(receta: RecetaCreate):
    """Crea una nueva receta en la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recetas (nombre, ingredientes, tiempo_preparacion, dificultad) VALUES (?, ?, ?, ?)",
        (receta.nombre, receta.ingredientes, receta.tiempo_preparacion, receta.dificultad)
    )
    receta_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {**receta.model_dump(), "id": receta_id}


@app.get("/recetas", response_model=list[RecetaResponse])
def listar_recetas():
    """Lista todas las recetas guardadas."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, ingredientes, tiempo_preparacion, dificultad FROM recetas")
    filas = cursor.fetchall()
    conn.close()
    
    return [dict(fila) for fila in filas]


@app.get("/recetas/{receta_id}", response_model=RecetaResponse)
def obtener_receta(receta_id: int):
    """Obtiene una receta específica por su ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, ingredientes, tiempo_preparacion, dificultad FROM recetas WHERE id = ?", (receta_id,))
    fila = cursor.fetchone()
    conn.close()
    
    if not fila:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Receta con ID {receta_id} no encontrada")
    
    return dict(fila)


@app.put("/recetas/{receta_id}", response_model=RecetaResponse)
def actualizar_receta(receta_id: int, receta: RecetaCreate):
    """Actualiza una receta existente."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM recetas WHERE id = ?", (receta_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Receta con ID {receta_id} no encontrada")
    
    cursor.execute(
        """
        UPDATE recetas 
        SET nombre = ?, ingredientes = ?, tiempo_preparacion = ?, dificultad = ?
        WHERE id = ?
        """,
        (receta.nombre, receta.ingredientes, receta.tiempo_preparacion, receta.dificultad, receta_id)
    )
    conn.commit()
    conn.close()
    
    return {**receta.model_dump(), "id": receta_id}


@app.delete("/recetas/{receta_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_receta(receta_id: int):
    """Elimina una receta por su ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM recetas WHERE id = ?", (receta_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Receta con ID {receta_id} no encontrada")
    
    cursor.execute("DELETE FROM recetas WHERE id = ?", (receta_id,))
    conn.commit()
    conn.close()
    return None


# --- ENDPOINT INTELIGENTE CON IA ---

@app.post("/recetas/sugerir-ia")
def sugerir_receta_ia(consulta: ConsultaIA):
    """
    Recibe una lista de ingredientes en casa y utiliza gemini-3.8-flash
    para sugerir una receta rápida y práctica.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La variable GEMINI_API_KEY no se encontró en el archivo .env o en el entorno."
        )

    # Crear el cliente con la API key cargada
    ai_client = genai.Client(api_key=api_key)

    prompt = (
        f"Tengo los siguientes ingredientes disponibles en casa: {consulta.ingredientes_disponibles}.\n"
        "Por favor, sugiere una receta sencilla indicando:\n"
        "1. Nombre del plato\n"
        "2. Pasos de preparación breves\n"
        "3. Tiempo estimado y nivel de dificultad."
    )
    
    try:
        response = ai_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        return {
            "ingredientes_ingresados": consulta.ingredientes_disponibles,
            "sugerencia_ia": response.text
        }
    except APIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al comunicarse con la IA de Google: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado al procesar la sugerencia: {str(e)}"
        )