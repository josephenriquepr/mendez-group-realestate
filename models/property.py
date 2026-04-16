from pydantic import BaseModel
from typing import Optional, List


class PropertyData(BaseModel):
    tipo_propiedad: str
    operacion: str
    direccion: str
    pueblo: str
    precio: float
    habitaciones: Optional[int] = None
    banos: Optional[float] = None
    pies_cuadrados_construccion: Optional[int] = None
    metros_o_cuerdas_terreno: Optional[str] = None
    estacionamientos: Optional[int] = None
    amenidades: List[str] = []
    descripcion_agente: str
    nombre_agente: str
    licencia_agente: str
    telefono_agente: str
    email_agente: str
