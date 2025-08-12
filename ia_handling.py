import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from drive_implementations import *

# --- CONFIGURACIÓN Y AUTENTICACIÓN DE GENAI ---
# Carga las variables de entorno para la clave de la API de Gemini
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada. Asegúrate de tenerla en tu archivo .env.")

# Inicializa el cliente de GenAI
client = genai.Client(api_key=GEMINI_API_KEY)

def extraer_datos_con_genai(texto_licencia):
    """
    Usa la API de Gemini para extraer información estructurada de un texto.

    Args:
        texto_licencia (str): El texto completo de la licencia de Word.

    Returns:
        dict: Un Json
    """
    # El prompt es la clave. Le pedimos que nos devuelva un JSON.   
    prompt_template = """
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
    En cuánto a las categorías de licencia, busca información sobre para qué se va a usar el equipo en el artículo 1°,
    Después de la descripción de a quién se le concede la licencia, se enumeran los equipos y el uso
    que se les va a dar:
    Equipo de rayos x para práctica (médica, odontológica, industrial, veterinaria o investigación)
    y posteriormente aparece el texte de la categoría de licencia correspondiente:
    Ej: Categoría II Veterinario

    No incluyas ningún texto fuera del JSON. 
    Es estrictamente necesario incluir el tipo de equipo y la categoría de la licencia en el JSON,
    estas claves deben ir en:
    tipo de equipo -> "TIPO DE EQUIPO"
    categoría de la licencia -> "CATEGORIA"
    fecha del control de calidad -> "FECHA CC"
    Tener en cuenta que el tipo de equipo y la categoría deben ir de la mano, es inadmisible, por ejemplo:
    Categoría: II VETERINARIO
    Tipo de equipo: INDUSTRIAL BAJA COMPLEJIDAD
    Está mal hecho, pues el tipo de equipo y la categoría no coinciden.
    El tipo de equipo y la categorían deben coincidir.

    Devuelve la respuesta estrictamente en formato JSON, sin ningún texto adicional, usando las siguientes claves:
    {{
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
      "TUBO DE RX": {{
        "MARCA": "",
        "MODELO": "",
        "SERIE": "",
        "FECHA FABR": ""
      }},
      "CONTROL CALIDAD": "",
      "FECHA CC": "",
    }}

    Texto de la licencia:
    ---
    {}
    ---
    
    """
    
    prompt = prompt_template.format(texto_licencia)
    try:
        response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[prompt]
        )
                # --- LÓGICA DE LIMPIEZA CLAVE ---
        raw_response_text = response.text.strip()
        
        # 1. Elimina el bloque de código de markdown si existe
        if raw_response_text.startswith("```json"):
            # Elimina los primeros 7 caracteres (`json) y los 3 últimos (```)
            cleaned_response = raw_response_text[7:-3].strip()
        else:
            cleaned_response = raw_response_text

        # 2. Intenta decodificar el JSON limpio
        extracted_data = json.loads(cleaned_response)
        return extracted_data
        extracted_data = json.loads(response.text.strip())
        return extracted_data
    except Exception as e:
        print(f"Error al extraer datos con GenAI: {e}")
        return None

if __name__ == '__main__':
    # Este bloque solo se ejecuta si corres este archivo directamente
    # Puedes poner aquí un texto de ejemplo para probar la función
    path = "C:\\Users\\Jose A. Diaz\\Documents\\GitHub\\GobAnt_RX_Tools\\Revision_Licencias\\2025010317348_UNIVERSIDAD DE ANTIOQUIA.docx"
    texto_licencia = leer_y_extraer_texto(path)

    datos_extraidos = extraer_datos_con_genai(texto_licencia)
    if datos_extraidos:
        print("--- Datos extraídos con GenAI ---")
        print(json.dumps(datos_extraidos, indent=2, ensure_ascii=False))
        with open("datos_extraidos.json", "w", encoding="utf-8") as f:
            json.dump(datos_extraidos, f, ensure_ascii=False, indent=2)
    else:
        print("No se pudieron extraer los datos del texto de ejemplo.")
