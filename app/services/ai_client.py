# app/services/ai_client.py
import json
import re
from typing import Dict, Any
import time
from google import genai  # paquete google-genai (pip install google-genai)

# NOTA: Todas las llaves del JSON del prompt están ESCAPADAS con {{ }}
PROMPT_TEMPLATE = """\
Extrae la siguiente información del texto de la licencia de rayos X que te doy a continuación.
Formato de fechas: día/mes/año (dd/mm/aaaa). Respeta mayúsculas/acentos exactamente como se listan.

Alcance:
1) Metadatos de la licencia (una vez por documento).
2) Equipos asociados a la licencia (0..N) → devolver SIEMPRE una lista `EQUIPOS` con un objeto por equipo.
   - Si solo existe un equipo, `EQUIPOS` debe contener 1 objeto.
   - Cada objeto de `EQUIPOS` incluye la información del equipo y de su tubo.

Reglas de normalización:
- Abreviar “EMPRESA SOCIAL DEL ESTADO” → ESE; “Instituciones Prestadoras de Servicios de Salud” → IPS.
- Si un dato del tubo o de serie no aparece, usar exactamente "NO REGISTRA" (mayúsculas).
- Si no puedes identificar el ente de control de calidad, usar "REVISAR".
- Para `SUBREGIÓN`, `MUNICIPIO`, `TIPO DE SOLICITUD`, `TIPO DE EQUIPO`, `CATEGORÍA`, elegir estrictamente de las listas provistas.
- En control de calidad, prioriza la última fecha explícita si aparecen varias.
- En caso de no tener información sobre el tubo de RX, dejar como: NO REGISTRA, recordar que en caso de que el tipo de solicitud sea MODIFICACIÓN OPR/EPR
o MODIFICACIÓN RAZÓN SOCIAL O REPRESENTANTE, se deben dejar en blanco (null) los espacios de los equipos. También se deja en (null) CONTROL DE CALIDAD y FECHA CC
- Fecha CC hace referencia a la fecha en que se llevó a cabo el control de calidad. Normalmente viene dado por:
El control de calidad fue realizado por: [Nombre del ente] el [Fecha]
- En caso de que exista una sección de DATOS A MODIFICAR, revisar qué elemento se encuentran en esa sección, normalmente se encuentra el tubo de rayos x
y sus datos, para que sea más claro que en este caso se debe poner Modificación cambio tubo
- No llenar la información del radicado.
- Abreviar Radioprotección e Ingeniería SAS a REI
- Siempre has coincidir el municipio con su subregión respectiva, esto es vital.

Listas permitidas
SUBREGIÓN:
- BAJO CAUCA
- MAGDALENA MEDIO
- NORDESTE
- NORTE
- OCCIDENTE
- ORIENTE
- SUROESTE
- URABÁ
- VALLE DE ABURRÁ

MUNICIPIO:
- BAJO CAUCA: CÁCERES, CAUCASIA, EL BAGRE, NECHÍ, TARAZÁ, ZARAGOZA
- MAGDALENA MEDIO: CARACOLÍ, MACEO, PUERTO BERRÍO, PUERTO NARE, PUERTO TRIUNFO, YONDÓ
- NORDESTE: AMALFI, ANORÍ, CISNEROS, REMEDIOS, SAN ROQUE, SANTO DOMINGO, SEGOVIA, VEGACHÍ, YALÍ, YOLOMBÓ
- NORTE: ANGOSTURA, BELMIRA, BRICEÑO, CAMPAMENTO, CAROLINA, DON MATÍAS, ENTRERRÍOS, GÓMEZ PLATA, GUADALUPE, ITUANGO, SAN ANDRÉS, SAN JOSÉ DE LA MONTAÑA, SAN PEDRO, SANTA ROSA DE OSOS, TOLEDO, VALDIVIA, YARUMAL
- OCCIDENTE: ABRIAQUÍ, ANZÁ, ARMENIA, BURITICÁ, CAÑASGORDAS, DABEIBA, EBÉJICO, FRONTINO, GIRALDO, HELICONIA, LIBORINA, OLAYA, PEQUE, SABANALARGA, SAN JERÓNIMO, SANTAFÉ DE ANTIOQUIA, SOPETRÁN, URAMITA
- ORIENTE: ABEJORRAL, ALEJANDRÍA, ARGELIA, EL CARMEN DE VÍBORAL, COCORNÁ, CONCEPCIÓN, GRANADA, GUARNE, LA CEJA, LA UNIÓN, MARINILLA, EL PEÑOL, EL RETIRO, RIONEGRO, SAN CARLOS, SAN FRANCISCO, SAN LUIS, SAN RAFAEL, SAN VICENTE, EL SANTUARIO, SONSÓN
- SUROESTE: AMAGÁ, ANDES, ANGELÓPOLIS, BETANIA, BETULIA, CAICEDO, CARAMANTA, CIUDAD BOLÍVAR, CONCORDIA, FREDONIA, HISPANIA, JARDÍN, JERICÓ, LA PINTADA, MONTEBELLO, PUEBLORRICO, SALGAR, SANTA BÁRBARA, TÁMESIS, TARSO, TITIRIBÍ, URRAO, VALPARAISO, VENECIA
- URABÁ: APARTADÓ, ARBOLETES, CAREPA, CHIGORODÓ, MURINDÓ, MUTATA, NECOCLÍ, SAN JUAN DE URABÁ, SAN PEDRO DE URABÁ, TURBO, VIGÍA DEL FUERTE
- VALLE DE ABURRÁ: BARBOSA, BELLO, CALDAS, COPACABANA, ENVIGADO, GIRARDOTA, ITAGÜÍ, LA ESTRELLA, MEDELLÍN, SABANETA

TIPO DE SOLICITUD:
- Primera vez
- Modificación OPR/EPR
- Modificación cambio tubo
- Modificación Razón Social o Representante legal
- Renovación
- Corrección
- PSPRYCC (Prestación de Servicio de Protección Radiológica y Control de Calidad)

MARCAS (preferente; si no, transcribe la del texto):
- ACCURAY, AJEX MEDITECH, AMERICAN X RAY, AMERICOMP, AMRAD, ARDET, BELMONT,
  BIOMEDICAL INTERNATIONAL, BLUE X IMAGING, CANON, CARESTREAM, DENTAL SAN JUSTO,
  DENTAL XRAY, DRGEM, DÜRR DENTAL, EAGLE, ELEKTA, FIAD, FUJIFILM CORPORATION,
  GENDEX, GENERAL ELECTRIC, GENORAY, GNATUS, GÖTZEN, GTR LABS, CIAS, HITACHI,
  HOLOGIC, IAE S.p.A, IMAGING SCIENCES INTERNATIONAL LLC, IMS GIOTTO, INSTRUMENTARIUM DENTAL,
  J. MORITA, KODAK, L3 COMMUNICATIONS, LARDENT, LUNAR, METALTRÓNICA, MINXRAY,
  OLYMPIA, OXFORD, PANPASS, PHILIPS, PLANMECA, POSKOM, PROBIOMEDYC, QUANTUM MEDICAL IMAGING,
  RAPISCAN, RTR, SHIMADZU, SIEMENS, SIN DATO, SIRONA, SMITHS DETECTION, TOSHIBA,
  TROPHY, TXR TINGLE, UNIVERSAL, VAREX IMAGING, VARIAN, VATECH

Entes de control de calidad (preferente; si no, "REVISAR"):
- Pimédica S.A, Sievert SAS, Alara SAS, León Moncada, UNAL, PSO, Jairo Poveda, Rad Solutions,
  Ubaldo Nerio Reynel, REI, Gabriel Murcia, Germán Ramírez, Físico Médico, Control Calidad SA
(“REI” = Radioprotección e Ingeniería S.A.S.)
Debe existir una línea del tipo: “Control de calidad realizado por: <ente> el <fecha>”.

TIPO DE EQUIPO (lista cerrada):
- PERIAPICAL, PERIAPICAL PORTÁTIL, PANORÁMICO, TOMÓGRAFO ODONTOLÓGICO, DENSITÓMETRO,
  CONVENCIONAL, RX PORTÁTIL, ARCO EN C, MAMÓGRAFO, TOMÓGRAFO, MULTIPROPÓSITO, FLUOROSCOPIO,
  ANGIÓGRAFO, ACELERADOR LINEAL, PET-CT, SPECT-CT, RADIOCIRUGÍA ROBÓTICA, INDUSTRIAL BAJA COMPLEJIDAD,
  INDUSTRIAL ALTA COMPLEJIDAD, INVESTIGACIÓN, VETERINARIO

Categoría de licencia (lista cerrada):
- I ODONTOLÓGICO, II ODONTOLÓGICO, I MÉDICO, II MÉDICO, I INDUSTRIAL, II INDUSTRIAL, II INVESTIGACIÓN, II VETERINARIO

Salida obligatoria:
- Devuelve **exclusivamente** un JSON válido, sin texto adicional.
- Estructura:

{{
  "ELABORA": "VANESSA P.",
  "RADICADO": "",
  "FECHA": "",
  "NOMBRE O RAZÓN SOCIAL": "",
  "NIT O CC": "",
  "SEDE": "",
  "DIRECCIÓN": "",
  "SUBREGIÓN": "",
  "MUNICIPIO": "",
  "CORREO ELECTRÓNICO": "",
  "TIPO DE SOLICITUD": "",
  "CATEGORÍA": "",
  "OBSERVACIONES": "",
  "EQUIPOS": [
    {{
      "TIPO DE EQUIPO": "",
      "FECHA DE FABRICACIÓN": "",
      "MARCA": "",
      "MODELO": "",
      "SERIE": "",
      "MARCA TUBO RX": "",
      "MODELO TUBO RX": "",
      "SERIE TUBO RX": "",
      "FECHA FABRICACIÓN TUBO RX": "",
      "CONTROL CALIDAD": "",
      "FECHA CC": ""
    }}
  ]
}}

Texto de la licencia:
---
{texto}
---
"""


def _clean_quotes(s: str) -> str:
    # comillas “inteligentes” → ascii
    return (s.replace("“", '"').replace("”", '"')
             .replace("‘", "'").replace("’", "'"))

def _strip_md_fences(s: str) -> str:
    # si viene en ```json ... ``` o ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, flags=re.IGNORECASE)
    return m.group(1).strip() if m else s

def _balanced_json_slice(s: str) -> str | None:
    # encuentra el primer bloque {...} con llaves balanceadas
    start = s.find("{")
    if start == -1: 
        return None
    depth = 0
    for i in range(start, len(s)):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def _fix_trailing_commas(s: str) -> str:
    # elimina comas colgantes antes de } o ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s

def _parse_json_loose(raw: str) -> dict:
    if not raw:
        raise ValueError("Respuesta vacía del modelo")
    txt = _clean_quotes(raw).strip()
    txt = _strip_md_fences(txt)
    # intentar tal cual
    try:
        return json.loads(txt)
    except Exception:
        pass
    # intentar bloque balanceado
    block = _balanced_json_slice(txt)
    if block:
        try:
            return json.loads(block)
        except Exception:
            # arreglar comas colgantes y reintentar
            block2 = _fix_trailing_commas(block)
            return json.loads(block2)
    # último intento: quitar comas colgantes globalmente
    txt2 = _fix_trailing_commas(txt)
    return json.loads(txt2)

class AIClient:
    def __init__(self, api_key: str, model_name: str = "models/gemini-2.0-flash-lite"):
        if not api_key:
            raise RuntimeError("Falta GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def summarize(self, text: str) -> Dict[str, Any]:
        prompt = PROMPT_TEMPLATE.format(texto=text[:25000])  # usa tu PROMPT_TEMPLATE con {{ }} escapadas
        last_err = None
        for attempt in range(3):  # hasta 3 intentos con pequeñas variaciones
            if attempt == 1:
                # 2º intento: reforzar instrucción de salida única
                prompt_try = prompt + "\n\nDevuelve únicamente un bloque JSON válido, sin comentarios, sin Markdown."
            elif attempt == 2:
                # 3º intento: recortar un poco más el texto por si hay límite de tokens
                prompt_try = PROMPT_TEMPLATE.format(texto=text[:18000])
            else:
                prompt_try = prompt

            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt_try],
            )

            raw = getattr(resp, "text", None)
            if not raw and getattr(resp, "candidates", None):
                try:
                    raw = "".join(
                        getattr(p, "text", "") for p in resp.candidates[0].content.parts
                    )
                except Exception as e:
                    last_err = e
                    raw = ""

            raw = (raw or "").strip()
            try:
                payload = _parse_json_loose(raw)
                # normalizaciones ligeras
                if isinstance(payload.get("CORREO ELECTRONICO"), str):
                    payload["CORREO ELECTRONICO"] = payload["CORREO ELECTRONICO"].strip().lower()
                return payload
            except Exception as e:
                last_err = e
                # pequeño backoff por si el servicio respondió incompleto
                time.sleep(0.6)

        # si llegamos aquí, fallaron los 3 intentos → exponemos parte de la salida para depuración
        raise RuntimeError(f"No se pudo parsear JSON del modelo: {last_err}")

