"""Constantes y definiciones de campos para la interfaz de licencias."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set

from .text_utils import normalize_label


class PersonaTipo(str, Enum):
    """Tipo de solicitante admitido por la aplicación."""

    NATURAL = "PERSONA NATURAL"
    JURIDICA = "PERSONA JURIDICA"

    @classmethod
    def from_text(cls, value: str) -> "PersonaTipo | None":
        normalized = normalize_label(value)
        for member in cls:
            if member.value == normalized:
                return member
        if "NAT" in normalized:
            return cls.NATURAL
        if "JUR" in normalized:
            return cls.JURIDICA
        return None


class CategoriaTipo(str, Enum):
    """Categorías de licencia soportadas."""

    CAT_1 = "CATEGORIA 1"
    CAT_2 = "CATEGORIA 2"

    @classmethod
    def from_text(cls, value: str) -> "CategoriaTipo | None":
        normalized = normalize_label(value)
        if "1" in normalized and "CAT" in normalized:
            return cls.CAT_1
        if "II" in normalized or ("2" in normalized and "CAT" in normalized):
            return cls.CAT_2
        if "PERIAP" in normalized:
            return cls.CAT_1
        if "PANOR" in normalized or "TOMOG" in normalized:
            return cls.CAT_2
        return None


@dataclass(frozen=True)
class FieldDefinition:
    """Configuración de cada campo editable en la interfaz."""

    key: str
    label: str
    required: bool = False
    multiline: bool = False


FIELDS: List[FieldDefinition] = [
    FieldDefinition("RADICADO", "Radicado", required=True),
    FieldDefinition("FECHA_RADICACION", "Fecha de radicación"),
    FieldDefinition("RESOLUCION", "Número de resolución"),
    FieldDefinition("FECHA_RESOLUCION", "Fecha de resolución"),
    FieldDefinition("FECHA_HOY", "Fecha de generación"),
    FieldDefinition("DIA_EMISION", "Día de emisión de la resolución"),
    FieldDefinition("MES_EMISION", "Mes de emisión de la resolución"),
    FieldDefinition("ANO_EMISION", "Año de emisión de la resolución"),
    FieldDefinition("TIPO_SOLICITANTE", "Tipo de solicitante", required=True),
    FieldDefinition("CATEGORIA", "Categoría de licencia", required=True),
    FieldDefinition("NOMBRE_SOLICITANTE", "Nombre o razón social", required=True),
    FieldDefinition("NIT_CC", "NIT o C.C.", required=True),
    FieldDefinition("REPRESENTANTE_LEGAL", "Representante legal"),
    FieldDefinition("REPRESENTANTE_CC", "C.C. representante legal"),
    FieldDefinition("SEDE", "Nombre de la sede", required=True),
    FieldDefinition("DIRECCION", "Dirección del establecimiento", required=True),
    FieldDefinition("MUNICIPIO", "Municipio"),
    FieldDefinition("TIPO_DE_SOLICITUD", "Tipo de solicitud"),
    FieldDefinition("EMAIL_NOTIFICACION", "Email de notificación"),
    FieldDefinition("TIPO_DE_EQUIPO", "Tipo de equipo", required=True),
    FieldDefinition("PRACTICA", "Práctica"),
    FieldDefinition("KV", "Tensión (kV)"),
    FieldDefinition("MA", "Corriente (mA)"),
    FieldDefinition("W", "Potencia (W)"),
    FieldDefinition("MARCA", "Marca"),
    FieldDefinition("MODELO", "Modelo"),
    FieldDefinition("SERIE", "Serie"),
    FieldDefinition("FECHA_FABRICACION", "Fecha de fabricación"),
    FieldDefinition("MARCA_TUBO", "Marca tubo RX"),
    FieldDefinition("MODELO_TUBO", "Modelo tubo RX"),
    FieldDefinition("SERIE_TUBO", "Serie tubo RX"),
    FieldDefinition("FECHA_FABRICACION_TUBO", "Fecha fabricación tubo RX"),
    FieldDefinition("EMPRESA_QC", "Empresa control de calidad"),
    FieldDefinition("FECHA_QC", "Fecha control de calidad"),
    FieldDefinition("OPR_NOMBRE", "Encargado/OPR nombre completo", required=True),
    FieldDefinition("OPR_CC", "C.C. Encargado/OPR", required=True),
    FieldDefinition("UBICACION_EQUIPO", "Ubicación del equipo"),
    FieldDefinition("OBSERVACIONES", "Observaciones", multiline=True),
]


HIDDEN_KEYS: Set[str] = {"SUBREGION", "PARRAFO_RESOLUCION"}


EQUIPMENT_FIELD_KEYS: Set[str] = {
    "TIPO_DE_EQUIPO",
    "PRACTICA",
    "MARCA",
    "MODELO",
    "SERIE",
    "FECHA_FABRICACION",
    "MARCA_TUBO",
    "MODELO_TUBO",
    "SERIE_TUBO",
    "FECHA_FABRICACION_TUBO",
    "KV",
    "MA",
    "W",
    "UBICACION_EQUIPO",
    "EMPRESA_QC",
    "FECHA_QC",
}


TUBE_FIELD_KEYS: Set[str] = {"MARCA_TUBO", "MODELO_TUBO", "SERIE_TUBO"}


# Mapeo de etiquetas encontradas en los documentos fuente hacia las claves estándar.
LABEL_TO_FIELD: Dict[str, str] = {
    "RADICADO": "RADICADO",
    "NO. RADICADO": "RADICADO",
    "NÚMERO DE RADICADO": "RADICADO",
    "TIPO DE SOLICITANTE": "TIPO_SOLICITANTE",
    "SOLICITANTE": "TIPO_SOLICITANTE",
    "NOMBRE O RAZON SOCIAL": "NOMBRE_SOLICITANTE",
    "NOMBRE O RAZÓN SOCIAL": "NOMBRE_SOLICITANTE",
    "NOMBRE O RAZON SOCIAL DEL SOLICITANTE": "NOMBRE_SOLICITANTE",
    "NOMBRE O RAZÓN SOCIAL DEL SOLICITANTE": "NOMBRE_SOLICITANTE",
    "RAZON SOCIAL": "NOMBRE_SOLICITANTE",
    "RAZÓN SOCIAL": "NOMBRE_SOLICITANTE",
    "NOMBRE COMPLETO": "NOMBRE_SOLICITANTE",
    "NIT": "NIT_CC",
    "NIT O CC": "NIT_CC",
    "NIT O C C": "NIT_CC",
    "NIT CC": "NIT_CC",
    "NIT O CEDULA": "NIT_CC",
    "NIT O CÉDULA": "NIT_CC",
    "CEDULA": "NIT_CC",
    "C.C": "NIT_CC",
    "CC": "NIT_CC",
    "REPRESENTANTE LEGAL": "REPRESENTANTE_LEGAL",
    "NOMBRE REPRESENTANTE LEGAL": "REPRESENTANTE_LEGAL",
    "NOMBRE COMPLETO REPRESENTANTE LEGAL": "REPRESENTANTE_LEGAL",
    "DOCUMENTO REPRESENTANTE LEGAL": "REPRESENTANTE_CC",
    "CC REPRESENTANTE": "REPRESENTANTE_CC",
    "CC REPRESENTANTE LEGAL": "REPRESENTANTE_CC",
    "CC R": "REPRESENTANTE_CC",
    "CC DEL REPRESENTANTE LEGAL": "REPRESENTANTE_CC",
    "CEDULA REPRESENTANTE LEGAL": "REPRESENTANTE_CC",
    "NOMBRE SEDE": "SEDE",
    "SEDE": "SEDE",
    "NOMBRE SEDE O CONSULTORIO": "SEDE",
    "NOMBRE DEL ESTABLECIMIENTO": "SEDE",
    "DIRECCION": "DIRECCION",
    "DIRECCIÓN": "DIRECCION",
    "DIRECCION ESTABLECIMIENTO": "DIRECCION",
    "MUNICIPIO": "MUNICIPIO",
    "SUBREGION": "SUBREGION",
    "SUBREGIÓN": "SUBREGION",
    "TIPO DE SOLICITUD": "TIPO_DE_SOLICITUD",
    "EMAIL NOTIFICACION": "EMAIL_NOTIFICACION",
    "TIPO DE EQUIPO": "TIPO_DE_EQUIPO",
    "PRACTICA": "PRACTICA",
    "PRACTICA SOLICITADA": "PRACTICA",
    "CATEGORIA": "CATEGORIA",
    "CATEGORÍA": "CATEGORIA",
    "CATEGORIA LICENCIA": "CATEGORIA",
    "CATEGORIA DEL EQUIPO": "CATEGORIA",
    "MARCA": "MARCA",
    "MARCA E": "MARCA",
    "MODELO": "MODELO",
    "MODELO E": "MODELO",
    "SERIE": "SERIE",
    "SERIE E": "SERIE",
    "NUMERO DE SERIE": "SERIE",
    "NUMERO SERIE": "SERIE",
    "NRO DE SERIE": "SERIE",
    "NRO SERIE": "SERIE",
    "N° SERIE": "SERIE",
    "KV": "KV",
    "K V": "KV",
    "MA": "MA",
    "M A": "MA",
    "W": "W",
    "POTENCIA": "W",
    "FECHA DE FABRICACION": "FECHA_FABRICACION",
    "FECHA DE FABRICACIÓN": "FECHA_FABRICACION",
    "FECHA FABRICACION E": "FECHA_FABRICACION",
    "MARCA TUBO RX": "MARCA_TUBO",
    "MARCA T": "MARCA_TUBO",
    "MODELO TUBO RX": "MODELO_TUBO",
    "MODELO T": "MODELO_TUBO",
    "SERIE TUBO RX": "SERIE_TUBO",
    "SERIE T": "SERIE_TUBO",
    "FECHA FABRICACION TUBO RX": "FECHA_FABRICACION_TUBO",
    "FECHA FABRICACIÓN TUBO RX": "FECHA_FABRICACION_TUBO",
    "FECHA FABRICACION T": "FECHA_FABRICACION_TUBO",
    "FECHA FABRICACIÓN T": "FECHA_FABRICACION_TUBO",
    "FECHA CC": "FECHA_QC",
    "FECHA CONTROL CALIDAD": "FECHA_QC",
    "OFICIAL DE PROTECCION RADIOLOGICA": "OPR_NOMBRE",
    "OFICIAL DE PROTECCIÓN RADIOLÓGICA": "OPR_NOMBRE",
    "ENCARGADO PROTECCION RADIOLOGICA": "OPR_NOMBRE",
    "ENCARGADO PROTECCIÓN RADIOLÓGICA": "OPR_NOMBRE",
    "ENCARGADO OPR NOMBRE COMPLETO": "OPR_NOMBRE",
    "ENCARGADO OPR": "OPR_NOMBRE",
    "ENCARGADO/OPR NOMBRE COMPLETO": "OPR_NOMBRE",
    "NOMBRE ENCARGADO OPR": "OPR_NOMBRE",
    "NOMBRE ENCARGADO": "OPR_NOMBRE",
    "ENCARGADO OFICIAL DE PROTECCION RADIOLOGICA": "OPR_NOMBRE",
    "ENCARGADO OFICIAL DE PROTECCIÓN RADIOLÓGICA": "OPR_NOMBRE",
    "OFICIAL DE PROTECCION RADIOLOGICA NOMBRE": "OPR_NOMBRE",
    "OFICIAL DE PROTECCIÓN RADIOLÓGICA NOMBRE": "OPR_NOMBRE",
    "OPR NOMBRE": "OPR_NOMBRE",
    "DOCUMENTO OPR": "OPR_CC",
    "CC OPR": "OPR_CC",
    "CEDULA OPR": "OPR_CC",
    "CEDULA DEL OPR": "OPR_CC",
    "CEDULA ENCARGADO OPR": "OPR_CC",
    "CEDULA ENCARGADO": "OPR_CC",
    "CEDULA DEL ENCARGADO": "OPR_CC",
    "CC ENCARGADO": "OPR_CC",
    "CC DEL ENCARGADO": "OPR_CC",
    "UBICACION": "UBICACION_EQUIPO",
    "UBICACION E": "UBICACION_EQUIPO",
    "UBICACIÓN": "UBICACION_EQUIPO",
    "UBICACIÓN E": "UBICACION_EQUIPO",
    "FECHA RADICACION": "FECHA_RADICACION",
    "FECHA RADICACIÓN": "FECHA_RADICACION",
    "RESOLUCION": "RESOLUCION",
    "RESOLUCIÓN": "RESOLUCION",
    "FECHA RESOLUCION": "FECHA_RESOLUCION",
    "FECHA RESOLUCIÓN": "FECHA_RESOLUCION",
    "FECHA HOY": "FECHA_HOY",
    "DIA EMISION": "DIA_EMISION",
    "DÍA EMISION": "DIA_EMISION",
    "DIA EMISIÓN": "DIA_EMISION",
    "DÍA EMISIÓN": "DIA_EMISION",
    "DIA": "DIA_EMISION",
    "MES EMISION": "MES_EMISION",
    "MES EMISIÓN": "MES_EMISION",
    "MES": "MES_EMISION",
    "ANO EMISION": "ANO_EMISION",
    "AÑO EMISION": "ANO_EMISION",
    "ANO EMISIÓN": "ANO_EMISION",
    "AÑO EMISIÓN": "ANO_EMISION",
    "ANO": "ANO_EMISION",
    "AÑO": "ANO_EMISION",
    "OBSERVACIONES": "OBSERVACIONES",
    "COMENTARIOS": "OBSERVACIONES",
    "EMPRESA CONTROL CALIDAD": "EMPRESA_QC",
    "EMPRESA CONTROL DE CALIDAD": "EMPRESA_QC",
    "EMPRESA QUE REALIZO EL CONTROL DE CALIDAD": "EMPRESA_QC",
    "EMPRESA QUE REALIZÓ EL CONTROL DE CALIDAD": "EMPRESA_QC",
    "FECHA CONTROL CALIDAD": "FECHA_QC",
    "FECHA DEL CONTROL DE CALIDAD": "FECHA_QC",
    "FECHA QUE SE REALIZO EL CONTROL DE CALIDAD": "FECHA_QC",
    "FECHA QUE SE REALIZÓ EL CONTROL DE CALIDAD": "FECHA_QC",
}


SECTION_LABEL_TO_FIELD: Dict[str, Dict[str, str]] = {
    "CONTROL DE CALIDAD": {
        "EMPRESA": "EMPRESA_QC",
        "EMPRESA DEL CC": "EMPRESA_QC",
        "EMPRESA CC": "EMPRESA_QC",
        "EMPRESA QC": "EMPRESA_QC",
        "EMPRESA QUE REALIZA CC": "EMPRESA_QC",
        "EMPRESA CONTROL CALIDAD": "EMPRESA_QC",
        "FECHA": "FECHA_QC",
        "FECHA CC": "FECHA_QC",
        "FECHA QC": "FECHA_QC",
        "FECHA CONTROL CALIDAD": "FECHA_QC",
    },
    "INFORMACION CONTROL CALIDAD": {
        "EMPRESA": "EMPRESA_QC",
        "EMPRESA DEL CC": "EMPRESA_QC",
        "EMPRESA CC": "EMPRESA_QC",
        "EMPRESA QC": "EMPRESA_QC",
        "EMPRESA QUE REALIZA CC": "EMPRESA_QC",
        "EMPRESA CONTROL CALIDAD": "EMPRESA_QC",
        "FECHA": "FECHA_QC",
        "FECHA CC": "FECHA_QC",
        "FECHA QC": "FECHA_QC",
        "FECHA CONTROL CALIDAD": "FECHA_QC",
    },
    "EQUIPOS A LICENCIAR": {
        "KV": "KV",
        "K V": "KV",
        "MA": "MA",
        "M A": "MA",
        "W": "W",
        "POTENCIA": "W",
    },
}
