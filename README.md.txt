# Recetario Inteligente API

API REST desarrollada con **FastAPI**, **SQLite** y **Google GenAI (Gemini)** que permite gestionar un catálogo de recetas de cocina y ofrece un endpoint inteligente que sugiere recetas personalizadas a partir de los ingredientes disponibles en casa.

---

## Descripción del Problema

Muchas personas cuentan con diversos ingredientes en su cocina pero no saben qué platillos pueden preparar con ellos. Esta API resuelve esa problemática permitiendo administrar (crear, consultar, actualizar y eliminar) recetas tradicionales, además de integrar un modelo de Inteligencia Artificial que analiza los ingredientes ingresados por el usuario y genera una sugerencia culinaria rápida, práctica y detallada.

---

## Requisitos e Instalación

Este proyecto utiliza **`uv`** como gestor de paquetes y entornos de Python.

### 1. Clonar el repositorio
```bash
git clone [https://github.com/TU_USUARIO/TU_REPOSITORIO.git](https://github.com/TU_USUARIO/TU_REPOSITORIO.git)
cd MYAPI

## Para ejecutar la API
uv run uvicorn main:app --reload