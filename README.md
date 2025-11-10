# GobAnt_RX_Tools - Web App IA

Pipeline en Python que:

1. lista y lee `.docx` desde una carpeta de Google Drive,
2. extrae el **Radicado** (ID único por documento),
3. usa **Gemini** para resumir/extraer datos,
4. guarda un **JSON** por radicado, y
5. actualiza **Google Sheets** llenando **solo celdas vacías** (con trazabilidad en *Observaciones*).

---

## Requisitos

* Python 3.10+
* Credenciales de **Service Account** de Google Cloud (archivo JSON)
* APIs habilitadas en tu proyecto GCP:

  * Google Drive API
  * Google Sheets API
* Dependencias instaladas:

  ```bash
  pip install -r requirements.txt
  ```

---

## Variables de entorno (`.env` recomendado)

Crea un archivo `.env` en la raíz del proyecto con:

```dotenv
# Google Sheets
SPREADSHEET_ID=1AbCDEF...XYZ            # ID del archivo de Google Sheets
WORKSHEET_NAME=Base_Maestra             # Nombre de la pestaña dentro del archivo

# Google Drive
DRIVE_FOLDER_ID=0BxxYYzz...             # ID de la carpeta con .docx a procesar

# Credenciales GCP
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/tu/service_account.json

# Gemini
GEMINI_API_KEY=tu_api_key
GEMINI_MODEL=gemini-1.5-flash

# Salida local
OUT_DIR=out_json

# Columnas (ajusta si tu hoja usa otros nombres)
COL_RADICADO=Radicado
COL_OBS=Observaciones
COL_ARCHIVO=Archivo
COL_UPDATED=Última actualización
```

> Si usas Windows, coloca rutas tipo `C:\\ruta\\service_account.json`.

---

## ¿Cómo obtengo la **ID de la carpeta** de Google Drive?

### Método 1: desde la URL (más simple)

1. Abre la carpeta en drive.google.com
2. Copia el segmento después de `folders/` en la URL. Ejemplo:

   * URL: `https://drive.google.com/drive/folders/0BxxYYzzAbCdEfGhIj`
   * **DRIVE\_FOLDER\_ID** = `0BxxYYzzAbCdEfGhIj`

### Método 2: buscando por nombre y copiando ID

1. En Drive, busca la carpeta por su nombre.
2. Clic derecho → *Obtener enlace* → copia el enlace y extrae el ID igual que arriba.

### Importante: compartir permisos

* Comparte **la carpeta** con el **correo del Service Account** (el que aparece en tu JSON, termina en `...iam.gserviceaccount.com`).
* Permiso recomendado: *Lector* (suficiente para leer archivos `.docx`).

---

## ¿Dónde se descargan los archivos?

Los `.docx` **no se guardan en disco**. Se descargan **en memoria** (streaming) para extraer su texto y se descartan.
Lo único que se guarda localmente son los **JSON** generados en la carpeta indicada por `OUT_DIR` (por defecto `out_json/`).

---

## Estructura del proyecto

```
project/
  app/
    config.py
    models/
      schemas.py
    utils/
      radicado.py
    services/
      google_auth.py
      drive_client.py
      sheets_table.py
      ai_client.py
    pipeline/
      ingest.py
  main.py
  requirements.txt
  README.md
```

### Roles de cada módulo

* `config.py`: lee variables de entorno y centraliza configuración.
* `radicado.py`: extrae el número de radicado (texto o nombre del archivo).
* `google_auth.py`: carga credenciales y construye clientes Drive/Sheets.
* `drive_client.py`: lista y descarga (en memoria) archivos `.docx`.
* `ai_client.py`: llama a Gemini con un prompt y devuelve JSON.
* `sheets_table.py`: lee/actualiza filas en Sheets; política “**solo llenar vacíos**” y escribe *Observaciones*.
* `ingest.py`: orquesta el flujo Drive → IA → JSON → Sheets.
* `main.py`: punto de entrada que ejecuta el pipeline (sin definir funciones nuevas).

---

## Ejecución

Asegúrate de tener `.env` configurado y credenciales accesibles.

```bash
python main.py
```

Flujo para cada `.docx` en `DRIVE_FOLDER_ID`:

1. Descarga en memoria y extrae texto.
2. Detecta **Radicado** (por cabecera o nombre de archivo).
3. Pasa el texto a **Gemini** y obtiene JSON.
4. Guarda `out_json/{radicado}.json`.
5. Actualiza la fila correspondiente en Google Sheets:

   * Si la fila **no existe** (Radicado nuevo): crea una fila.
   * Si **existe**: rellena **solo celdas vacías** y deja constancia en *Observaciones*.

---

## Interfaz gráfica para licencias

Además del pipeline por consola, el repositorio incluye una interfaz de escritorio basada en **PySide6** para generar licencias desde plantillas Word.

```bash
python gui_app.py
```

### Paso a paso

1. **Configura las plantillas la primera vez.**
   * En la sección *Plantillas de licencia* presiona **Seleccionar…** para cada combinación (Natural/Jurídica × Categoría I/II) y apunta al `.docx` con marcadores `{{CAMPO}}` en negrilla.
   * Guarda las rutas con **Guardar rutas de plantillas**. La configuración queda persistida en `~/.gobant_rx_tools_gui.json` para futuros usos.
2. **Carga la fuente o ingresa los datos manualmente.**
   * Usa **Cargar documento .docx** para leer un checklist estándar. La app detecta persona/categoría y rellena el formulario.
   * Si no tienes documento, elige **Ingresar datos manualmente** y llena cada campo directamente en la interfaz.
3. **Revisa y corrige la información.**
   * Todos los campos editables aparecen en el formulario central; cualquier edición se normaliza a mayúsculas/negrilla al guardar.
   * El bloque *Equipos a licenciar* muestra cuántos equipos se detectaron y te permite alternar el equipo activo, agregar registros adicionales o eliminar los que no apliquen antes de generar la licencia. Cada equipo incluye campos específicos para su categoría y radicado, de modo que puedas ajustarlos sin afectar al resto.
   * Marca si quieres **Actualizar documento origen** (reescribe el `.docx` original con los datos corregidos).
4. **Genera la licencia.**
   * Presiona **Generar licencia**. El archivo se crea junto al documento fuente (o en la carpeta elegida manualmente) con el patrón `RADICADO_SOLICITANTE_LICENCIA.docx`.
   * Activa la casilla **Incluir párrafo que deja sin efecto una resolución previa** si tu plantilla contiene ese texto y cuentas con los datos de resolución (`{{RESOLUCION}}`, `{{DIA}}`/`{{DIA_EMISION}}`, `{{MES}}`/`{{MES_EMISION}}`, `{{AÑO}}`/`{{AÑO_EMISION}}`). Si falta alguno, la aplicación omitirá automáticamente el párrafo aunque la casilla esté marcada.
   * En la plantilla, ubica el lugar exacto donde debe ir el texto y escribe únicamente el marcador `{{PARRAFO_RESOLUCION}}` en un párrafo independiente. Cuando la casilla esté activa, el marcador se reemplazará por “Este acto administrativo deja sin efecto la Resolución No {{RESOLUCION}}…” con los datos correspondientes; si la casilla está desactivada o los datos son incompletos, el párrafo se elimina por completo. El reemplazo conserva el formato en mayúsculas/minúsculas habitual y solo resalta en negrilla la sección “Resolución No {{RESOLUCION}} del {{DIA}} de {{MES}} de {{AÑO}}”.
   * Si manejas más de un equipo, reserva un párrafo que contenga únicamente `{{LISTA_EQUIPOS}}`. La aplicación insertará allí un bloque numerado con los equipos detectados, replicando el formato estándar del acta. Las plantillas que aún usen los marcadores individuales seguirán tomando los datos del primer equipo.
   * Cuando distintos equipos pertenecen a categorías o radicados diferentes, revisa los campos **Categoría del equipo** y **Radicado del equipo** para cada registro. Al generar la licencia se crearán archivos independientes por equipo, empleando la plantilla que corresponde a su categoría y nombrando cada archivo con el radicado específico (`RADICADO_EQUIPO_…`). Si dejas el radicado del equipo vacío se reutiliza el radicado principal del formulario.
   * Si cada equipo cuenta con una resolución previa distinta, utiliza los campos **Resolución del equipo** y **Fecha resolución del equipo** al revisar cada registro. En los archivos generados individualmente, esos valores reemplazan `{{RESOLUCION}}`, `{{FECHA_RESOLUCION}}` y sus componentes (`{{DIA}}`, `{{MES}}`, `{{AÑO}}`) al construir el párrafo opcional. Si la casilla está activa pero falta algún dato para un equipo concreto, la bitácora avisará y el párrafo se omitirá solo en ese documento.
   * Dentro de la línea “Tubo de rayos X …”, sustituye `Marca: {{MARCA_TUBO}} Modelo: {{MODELO_TUBO}} Número de serie: {{SERIE_TUBO}}` por el marcador `{{DATOS_TUBO}}`. Si las celdas del checklist contienen “NO REGISTRA” (o están vacías) el texto completo del tubo se omite sin dejar espacios dobles.
   * Si tu plantilla incluye la fecha de expedición del documento (`{{FECHA_HOY}}`), la interfaz la rellena automáticamente con la fecha del día en que generas la licencia (formato `dd-mm-aaaa`) y la aplica sin negrilla para respetar el estilo solicitado.
   * Al finalizar, la bitácora inferior muestra el resultado o posibles errores.
5. **(Opcional) Sube a Drive y ejecuta el pipeline.**
   * Activa **Subir licencia a Drive y ejecutar pipeline** para reutilizar la configuración de `app/config.py` y disparar la ingesta automática tras la generación.
6. **Monitorea tareas del pipeline.**
   * Desde la pestaña *Carga automática (Drive/Sheets)* puedes lanzar los comandos `process_folder`, `process_folder_only_new` o `process_folder_only_pending` sin salir de la GUI.

> Consejo: si tu checklist cambia de estructura, ajusta los campos esperados en `app/gui/constants.py` antes de usar la aplicación para garantizar que el mapeo siga funcionando.

### Reportes de control de calidad (PDF → JSON)

La interfaz incluye una pestaña adicional para consolidar los reportes de control de calidad almacenados como PDF en una carpeta local.

1. Abre la pestaña **Reportes control de calidad** y pulsa **Seleccionar carpeta…** para elegir la ubicación con los PDFs.
   * Si ves un aviso indicando que falta `pdfplumber`, instala la dependencia opcional ejecutando `pip install pdfplumber` (o vuelve a correr `pip install -r requirements.txt`).
2. Presiona **Analizar PDFs**. Cada archivo se procesa en segundo plano y se extraen cuatro campos:
   * **Fecha de la evaluación** (`fecha_evaluacion` en el JSON)
   * **Tipo de equipo** (`tipo_equipo`)
   * **Nombre de la institución** (`nombre_de_la_institucion`)
   * **Identificador**, tomado del prefijo numérico del nombre del archivo (`XX_nombre.pdf → XX`).
3. Verifica los resultados en la tabla. Cualquier PDF sin texto o con campos faltantes se reporta en la bitácora de la pestaña.
4. Usa **Exportar JSON** para guardar el resumen en un archivo (`control_calidad.json` por defecto). Se incluye el nombre y ruta original de cada PDF para facilitar trazabilidad.

Para maximizar la detección automática, mantén etiquetas legibles en los PDFs (por ejemplo, «Fecha de la evaluación: …», «Tipo de equipo: …», «Nombre de la institución: …»). Si una etiqueta aparece en una línea y el valor en la siguiente, el lector también la interpretará correctamente.

#### Checklist: etiquetas recomendadas

Para que el lector de tablas reconozca cada dato automáticamente, asegúrate de que las celdas de la tabla contengan una de las siguientes etiquetas (negrilla y con dos puntos opcional). Es válido que la etiqueta esté seguida del valor en la misma celda o que el valor esté en la celda contigua.

| Campo en la app/plantilla (`{{CLAVE}}`) | Texto sugerido en el checklist |
| --- | --- |
| `{{NOMBRE_SOLICITANTE}}` | `NOMBRE O RAZÓN SOCIAL` / `RAZON SOCIAL` |
| `{{NIT_CC}}` | `NIT O CC` / `NIT` / `C.C` |
| `{{REPRESENTANTE_LEGAL}}` | `REPRESENTANTE LEGAL` / `NOMBRE REPRESENTANTE LEGAL` |
| `{{REPRESENTANTE_CC}}` | `CC REPRESENTANTE LEGAL` / `DOCUMENTO REPRESENTANTE LEGAL` |
| `{{OPR_NOMBRE}}` | `ENCARGADO/OPR NOMBRE COMPLETO` / `OFICIAL DE PROTECCIÓN RADIOLÓGICA` |
| `{{OPR_CC}}` | `CC OPR` / `DOCUMENTO OPR` |
| `{{EMPRESA_QC}}` | `EMPRESA CONTROL CALIDAD` / `EMPRESA QUE REALIZÓ EL CONTROL DE CALIDAD` *(o simplemente `EMPRESA` dentro de la sección «CONTROL DE CALIDAD»)* |
| `{{FECHA_QC}}` | `FECHA CONTROL CALIDAD` / `FECHA DEL CONTROL DE CALIDAD` *(o `FECHA` dentro de la sección «CONTROL DE CALIDAD»)* |
| `{{SERIE}}` | `SERIE` / `NÚMERO DE SERIE` |
| `{{CATEGORIA_EQUIPO}}` | `CATEGORÍA EQUIPO` / `CATEGORIA EQUIPO` |
| `{{RADICADO_EQUIPO}}` | `RADICADO EQUIPO` / `RADICADO DEL EQUIPO` |
| `{{CATEGORIA}}` | `CATEGORÍA` / `CATEGORÍA LICENCIA` |
| `{{RESOLUCION}}` | `RESOLUCIÓN` / `NÚMERO DE RESOLUCIÓN` |
| `{{FECHA_RESOLUCION}}` | `FECHA RESOLUCIÓN` / `FECHA DE LA RESOLUCIÓN` *(formato dd/mm/aaaa)* |
| `{{RESOLUCION_EQUIPO}}` | `RESOLUCIÓN EQUIPO` / `RESOLUCIÓN DEL EQUIPO` *(en la sección «EQUIPOS A LICENCIAR»)* |
| `{{FECHA_RESOLUCION_EQUIPO}}` | `FECHA RESOLUCIÓN EQUIPO` / `FECHA RESOLUCIÓN DEL EQUIPO` *(formato dd/mm/aaaa dentro de «EQUIPOS A LICENCIAR»)* |
| `{{FECHA_HOY}}` | Campo agregado manualmente en la plantilla para la fecha de expedición del documento. No se extrae del checklist; la app lo completa con la fecha actual en formato `dd-mm-aaaa` (sin aplicar negrilla). |
| `{{DATOS_TUBO}}` | Reemplaza el segmento “Marca/Modelo/Número de serie” del tubo; se omite automáticamente cuando las celdas del checklist dicen “NO REGISTRA”. |
| `{{LISTA_EQUIPOS}}` | Inserta la lista numerada de equipos en plantillas con múltiples dispositivos licenciados. Debe ubicarse en un párrafo independiente. |
| `{{DIA_EMISION}}` o `{{DIA}}` | `DÍA EMISIÓN` / `DÍA` |
| `{{MES_EMISION}}` o `{{MES}}` | `MES EMISIÓN` / `MES` |
| `{{AÑO_EMISION}}` o `{{AÑO}}` | `AÑO EMISIÓN` / `AÑO` |

> La aplicación toma la fecha `dd/mm/aaaa` detectada en el checklist y rellena automáticamente `{{DIA}}`, `{{MES}}` (nombre del mes en texto) y `{{AÑO}}`. Si borras la fecha en la interfaz, los tres campos se limpian para evitar información obsoleta.

> Nota: Los valores pueden incluir guiones (`-`) o diagonales sin afectar la detección. Si una etiqueta necesita abreviarse en el checklist (por ejemplo `EMPRESA` o `FECHA`), ubícala debajo del encabezado de tabla “CONTROL DE CALIDAD” para que la app la asocie con `EMPRESA_QC` o `FECHA_QC` respectivamente.

---

## Personalización

* **Encabezados de la hoja**: ajusta variables `COL_*` en `.env` o en `app/config.py`.
* **Modelo de IA**: `GEMINI_MODEL` (`gemini-1.5-flash` por defecto, puedes usar `gemini-1.5-pro` si tu cuota lo permite).
* **Prompt de IA**: edita `PROMPT_TEMPLATE` en `app/services/ai_client.py`.
* **Política de escritura**: lógica en `fill_from_json_only_empty()` (archivo `sheets_table.py`).
* **Carpeta de salida JSON**: cambia `OUT_DIR`.

---

## Troubleshooting (frecuentes)

* **403/404 al listar la carpeta**

  * Verifica `DRIVE_FOLDER_ID` y que la **carpeta esté compartida** con el correo del Service Account.
  * Revisa que la **Drive API** esté habilitada.

* **`PERMISSION_DENIED` en Sheets**

  * Comparte el **archivo de Google Sheets** con el Service Account (Editor para escribir).

* **`KeyError`/columnas faltantes**

  * Asegura que los encabezados en tu pestaña coinciden con las claves del JSON o usa un `field_map` en `fill_from_json_only_empty()`.

* **`No se encontró Radicado`**

  * Revisa el patrón: el radicado debe ser un número (≥6 dígitos) al inicio del doc o en el nombre del archivo.

* **Gemini quota**

  * Reduce el tamaño del texto (`[:25000]`), o usa un modelo más ligero (`gemini-1.5-flash`).

---

## Ejemplo de mapeo (si el JSON **no** coincide con encabezados)

En `ingest.py` (llamada a `fill_from_json_only_empty`) añade `field_map`:

```python
field_map={
  "resumen": "Resumen IA",
  "acciones": "Acciones",
  "responsable": "Responsable",
  "fecha": "Fecha",
}
```

---

## Roadmap sugerido

* Validaciones semánticas: pedir a la IA verificar coherencia con lo ya escrito antes de completar.
* Notificaciones (correo/Chat) si hubo cambios.
* Tests con `pytest` para cada servicio.
* Despliegue en Cloud Run/Jobs para ejecución programada.

---

## Licencia

Uso interno. Ajusta según tu organización.
