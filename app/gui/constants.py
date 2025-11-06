"""Constantes y definiciones de campos para la interfaz de licencias."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

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
    FieldDefinition("TIPO_SOLICITANTE", "Tipo de solicitante", required=True),
    FieldDefinition("CATEGORIA", "Categoría", required=True),
    FieldDefinition("NOMBRE_SOLICITANTE", "Nombre o razón social", required=True),
    FieldDefinition("NIT_CC", "NIT o C.C.", required=True),
    FieldDefinition("REPRESENTANTE_LEGAL", "Representante legal"),
    FieldDefinition("REPRESENTANTE_CC", "C.C. representante legal"),
    FieldDefinition("SEDE", "Nombre de la sede", required=True),
    FieldDefinition("DIRECCION", "Dirección del establecimiento", required=True),
    FieldDefinition("MUNICIPIO", "Municipio"),
    FieldDefinition("SUBREGION", "Subregión"),
    FieldDefinition("TIPO_DE_SOLICITUD", "Tipo de solicitud"),
    FieldDefinition("EMAIL_NOTIFICACION", "Email de notificación"),
    FieldDefinition("TIPO_DE_EQUIPO", "Tipo de equipo", required=True),
    FieldDefinition("PRACTICA", "Práctica"),
    FieldDefinition("MARCA", "Marca"),
    FieldDefinition("MODELO", "Modelo"),
    FieldDefinition("SERIE", "Serie"),
    FieldDefinition("FECHA_FABRICACION", "Fecha de fabricación"),
    FieldDefinition("MARCA_TUBO", "Marca tubo RX"),
    FieldDefinition("MODELO_TUBO", "Modelo tubo RX"),
    FieldDefinition("SERIE_TUBO", "Serie tubo RX"),
    FieldDefinition("FECHA_FABRICACION_TUBO", "Fecha fabricación tubo RX"),
    FieldDefinition("CONTROL_CALIDAD", "Control de calidad"),
    FieldDefinition("FECHA_CC", "Fecha control de calidad"),
    FieldDefinition("OPR_NOMBRE", "Encargado/OPR nombre completo", required=True),
    FieldDefinition("OPR_CC", "C.C. Encargado/OPR", required=True),
    FieldDefinition("UBICACION_EQUIPO", "Ubicación del equipo"),
    FieldDefinition("OBSERVACIONES", "Observaciones", multiline=True),
]


# Mapeo de etiquetas encontradas en los documentos fuente hacia las claves estándar.
LABEL_TO_FIELD: Dict[str, str] = {
    "RADICADO": "RADICADO",
    "NO. RADICADO": "RADICADO",
    "NÚMERO DE RADICADO": "RADICADO",
    "TIPO DE SOLICITANTE": "TIPO_SOLICITANTE",
    "SOLICITANTE": "TIPO_SOLICITANTE",
    "NOMBRE O RAZON SOCIAL": "NOMBRE_SOLICITANTE",
    "NOMBRE O RAZÓN SOCIAL": "NOMBRE_SOLICITANTE",
    "RAZON SOCIAL": "NOMBRE_SOLICITANTE",
    "RAZÓN SOCIAL": "NOMBRE_SOLICITANTE",
    "NOMBRE COMPLETO": "NOMBRE_SOLICITANTE",
    "NIT": "NIT_CC",
    "NIT O CC": "NIT_CC",
    "NIT CC": "NIT_CC",
    "CEDULA": "NIT_CC",
    "C.C": "NIT_CC",
    "CC": "NIT_CC",
    "REPRESENTANTE LEGAL": "REPRESENTANTE_LEGAL",
    "NOMBRE REPRESENTANTE LEGAL": "REPRESENTANTE_LEGAL",
    "DOCUMENTO REPRESENTANTE LEGAL": "REPRESENTANTE_CC",
    "CC REPRESENTANTE": "REPRESENTANTE_CC",
    "CC R": "REPRESENTANTE_CC",
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
    "CATEGORIA": "CATEGORIA",
    "CATEGORÍA": "CATEGORIA",
    "CATEGORIA LICENCIA": "CATEGORIA",
    "MARCA": "MARCA",
    "MARCA E": "MARCA",
    "MODELO": "MODELO",
    "MODELO E": "MODELO",
    "SERIE": "SERIE",
    "SERIE E": "SERIE",
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
    "CONTROL CALIDAD": "CONTROL_CALIDAD",
    "FECHA CC": "FECHA_CC",
    "OFICIAL DE PROTECCION RADIOLOGICA": "OPR_NOMBRE",
    "OFICIAL DE PROTECCIÓN RADIOLÓGICA": "OPR_NOMBRE",
    "ENCARGADO PROTECCION RADIOLOGICA": "OPR_NOMBRE",
    "ENCARGADO PROTECCIÓN RADIOLÓGICA": "OPR_NOMBRE",
    "DOCUMENTO OPR": "OPR_CC",
    "CC OPR": "OPR_CC",
    "CEDULA OPR": "OPR_CC",
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
    "OBSERVACIONES": "OBSERVACIONES",
    "COMENTARIOS": "OBSERVACIONES",
}
