from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class FileInfo:
    id: str
    name: str
    modified_time: Optional[str] = None

@dataclass
class IAExtraction:
    resumen: str
    acciones: Optional[str] = None
    responsable: Optional[str] = None
    fecha: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Resumen IA": self.resumen,
            "Acciones": self.acciones or "",
            "Responsable": self.responsable or "",
            "Fecha": self.fecha or "",
        }