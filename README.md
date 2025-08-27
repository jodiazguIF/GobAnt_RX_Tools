# GobAnt RX Tools

MVP para análisis de datos de licenciamiento de equipos de rayos X. Incluye ETL desde Google Sheets, API con FastAPI, frontend en Next.js y consultas en lenguaje natural usando Gemini.

## Configuración

1. Copia `deploy/env.example` a `.env` y completa las variables.
2. Instala dependencias:

```bash
pip install -r requirements.txt
npm --prefix app/frontend install
```

## Comandos

| Comando | Descripción |
|---------|-------------|
| `make etl` | Ejecuta el ETL y genera `data/processed/licencias.parquet`. |
| `make run` | Inicia backend en `http://localhost:8000` y frontend en `http://localhost:3000`. |
| `make test` | Ejecuta pruebas unitarias. |

## Preguntas de ejemplo

En la página `/ask` se pueden realizar preguntas como:

* "Licencias odontológicas 2025 por subregión ordenadas desc"

## Catálogo y sinónimos

El catálogo de datos utilizado por el backend para generar SQL se encuentra en `catalog/data_catalog.json` e incluye sinónimos para los campos.
