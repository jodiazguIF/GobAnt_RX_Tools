# app/services/ai_client.py
import json
import re
from typing import Dict, Any
import time
from google import genai  # paquete google-genai (pip install google-genai)

# NOTA: Todas las llaves del JSON del prompt están ESCAPADAS con {{ }}
PROMPT_TEMPLATE = """\
Extrae la siguiente información del texto de la licencia de rayos X que te doy a continuación:
- Radicado
- Fecha (Formato de las fechas: día/mes/año)
- Nombre o Razón Social
- Nit o CC
- Sede (si no hay, dejar en blanco)
- Dirección
- Subregión
- correo electrónico del solicitante
- tipo de solicitud
- tipo de equipo
- categoría de licencia
En cuanto a los equipos de rayos X:
Del equipo de rayos X:
- fecha de fabricación
- marca
- modelo
- serie
Del tubo de Rayos X
- marca
- modelo
- serie
- fecha de fabricación
Siguiendo con la información del texto:
- control calidad
- fecha de control calidad

En caso de que el nombre o razón social sea relativo a EMPRESA SOCIAL DEL ESTADO, se debe abreviar por ESE, de igual forma,
para Instituciones Prestadoras de Servicios de Salud, se debe abreviar por IPS

Ten en cuenta que para los siguientes apartados solo se puede escoger entre los siguientes valores:
SUBREGIÓN: Elige de la siguiente lista:
- BAJO CAUCA
- MAGDALENA MEDIO
- NORDESTE
- NORTE
- OCCIDENTE
- ORIENTE
- SUROESTE
- URABÁ
- VALLE DE ABURRÁ

MUNICIPIO: Elige de la siguiente lista:
- CÁCERES, CAUCASIA, EL BAGRE, NECHÍ, TARAZÁ, ZARAGOZA
- CARACOLÍ, MACEO, PUERTO BERRÍO, PUERTO NARE, PUERTO TRIUNFO, YONDÓ
- AMALFI, ANORÍ, CISNEROS, REMEDIOS, SAN ROQUE, SANTO DOMINGO, SEGOVIA, VEGACHÍ, YALÍ, YOLOMBÓ
- ANGOSTURA, BELMIRA, BRICEÑO, CAMPAMENTO, CAROLINA, DON MATÍAS, ENTRERRÍOS, GÓMEZ PLATA, GUADALUPE, ITUANGO, SAN ANDRÉS, SAN JOSÉ DE LA MONTAÑA, SAN PEDRO, SANTA ROSA DE OSOS, TOLEDO, VALDIVIA, YARUMAL
- ABRIAQUÍ, ANZÁ, ARMENIA, BURITICÁ, CAÑASGORDAS, DABEIBA, EBÉJICO, FRONTINO, GIRALDO, HELICONIA, LIBORINA, OLAYA, PEQUE, SABANALARGA, SAN JERÓNIMO, SANTAFÉ DE ANTIOQUIA, SOPETRÁN, URAMITA
- ABEJORRAL, ALEJANDRÍA, ARGELIA, EL CARMEN DE VÍBORAL, COCORNÁ, CONCEPCIÓN, GRANADA, GUARNE, LA CEJA, LA UNIÓN, MARINILLA, EL PEÑOL, EL RETIRO, RIONEGRO, SAN CARLOS, SAN FRANCISCO, SAN LUIS, SAN RAFAEL, SAN VICENTE, EL SANTUARIO, SONSÓN
- AMAGÁ, ANDES, ANGELÓPOLIS, BETANIA, BETULIA, CAICEDO, CARAMANTA, CIUDAD BOLÍVAR, CONCORDIA, FREDONIA, HISPANIA, JARDÍN, JERICÓ, LA PINTADA, MONTEBELLO, PUEBLORRICO, SALGAR, SANTA BÁRBARA, TÁMESIS, TARSO, TITIRIBÍ, URRAO, VALPARAISO, VENECIA
- APARTADÓ, ARBOLETES, CAREPA, CHIGORODÓ, MURINDÓ, MUTATA, NECOCLÍ, SAN JUAN DE URABÁ, SAN PEDRO DE URABÁ, TURBO, VIGÍA DEL FUERTE
- BARBOSA, BELLO, CALDAS, COPACABANA, ENVIGADO, GIRARDOTA, ITAGÜÍ, LA ESTRELLA, MEDELLÍN, SABANETA

TIPO DE SOLICITUD: Elige de la siguiente lista:
- Primera vez
- Modificación OPR/EPR
- Modificación cambio tubo
- Modificación Razón Social o Representante legal
- Renovación
- Corrección

En caso de que el tipo de solicitud sea Modificación Razón Social o Representante legal o de Modificación
de OPR/EPR, dejar los datos del equipo en blanco (null).

MARCAS: De ser posible elige de la siguiente lista:
- ACCURAY
- AJEX MEDITECH
- AMERICAN X RAY
- AMERICOMP
- AMRAD
- ARDET
- BELMONT
- BIOMEDICAL INTERNATIONAL
- BLUE X IMAGING
- CANON
- CARESTREAM
- DENTAL SAN JUSTO
- DENTAL XRAY
- DRGEM
- DÜRR DENTAL
- EAGLE
- ELEKTA
- FIAD
- FUJIFILM CORPORATION
- GENDEX
- GENERAL ELECTRIC
- GENORAY
- GNATUS
- GÖTZEN
- GTR LABS
- CIAS
- HITACHI
- HOLOGIC
- IAE S.p.A
- IMAGING SCIENCES INTERNATIONAL LLC
- IMS GIOTTO
- INSTRUMENTARIUM DENTAL
- J. MORITA
- KODAK
- L3 COMMUNICATIONS
- LARDENT
- LUNAR
- METALTRÓNICA
- MINXRAY
- OLYMPIA
- OXFORD
- PANPASS
- PHILIPS
- PLANMECA
- POSKOM
- PROBIOMEDYC
- QUANTUM MEDICAL IMAGING
- RAPISCAN
- RTR
- SHIMADZU
- SIEMENS
- SIN DATO
- SIRONA
- SMITHS DETECTION
- TOSHIBA
- TROPHY
- TXR TINGLE
- UNIVERSAL
- VAREX IMAGING
- VARIAN
- VATECH

En caso de no ser capaz de elegir, dejar como "REVISAR"

Encargado del control de calidad: De ser posible elige de la siguiente lista:
- Pimédica S.A
- Sievert SAS
- Alara SAS
- León Moncada
- UNAL
- RadProct
- PSO
- Jairo Poveda
- Rad Solutions
- Ubaldo Nerio Reynel
- REI
- Gabriel Murcia
- Germán Ramírez
- Físico Médico
- Control Calidad SA

En caso de no ser capaz de elegir, dejar como "REVISAR"

tipo de equipo: De ser posible elige de la siguiente lista:
- PERIAPICAL
- PERIAPICAL PORTÁTIL
- PANORÁMICO
- TOMÓGRAFO ODONTOLÓGICO
- DENSITÓMETRO
- CONVENCIONAL
- RX PORTÁTIL
- ARCO EN C
- MAMÓGRAFO
- TOMÓGRAFO
- MULTIPROPÓSITO
- FLUOROSCOPIO
- ANGIÓGRAFO
- ACELERADOR LINEAL
- PET-CT
- SPECT-CT
- RADIOCIRUGÍA ROBÓTICA
- INDUSTRIAL BAJA COMPLEJIDAD
- INDUSTRIAL ALTA COMPLEJIDAD
- INVESTIGACIÓN
- VETERINARIO

Categoría de licencia: Elige estrictamente uno de la siguiente lista:
- I ODONTOLÓGICO
- II ODONTOLÓGICO
- I MÉDICO
- II MÉDICO
- I INDUSTRIAL
- II INDUSTRIAL
- II INVESTIGACIÓN
- II VETERINARIO

No incluyas ningún texto fuera del JSON. 
Es estrictamente necesario incluir el tipo de equipo y la categoría de la licencia en el JSON,
estas claves deben ir en:
tipo de equipo -> "TIPO DE EQUIPO"
categoría de la licencia -> "CATEGORIA"
fecha del control de calidad -> "FECHA CC"
El tipo de equipo y la categoría deben ser coherentes.

Devuelve la respuesta estrictamente en formato JSON, sin ningún texto adicional, usando las siguientes claves:
{{
  "NOMBRE":"Vanessa P.",
  "RADICADO": "",
  "FECHA": "",
  "NOMBRE O RAZON SOCIAL": "",
  "NIT O CC": "",
  "SEDE": "",
  "DIRECCION": "",
  "SUBREGION": "",
  "MUNICIPIO": "",
  "CORREO ELECTRONICO": "",
  "TIPO DE SOLICITUD": "",
  "TIPO DE EQUIPO": "",
  "CATEGORIA": "",
  "FECHA DE FABRICACION": "",
  "MARCA": "",
  "MODELO": "",
  "SERIE": "",
  "MARCA TUBO RX": "",
  "MODELO TUBO RX": "",
  "SERIE TUBO RX": "",
  "CONTROL CALIDAD": "",
  "FECHA CC": "",
  "OBSERVACIONES": ""
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

