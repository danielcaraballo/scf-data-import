from typing import Any

# ATENCIÓN: CATALOG_MODELS se itera en orden de definición.
# Las entidades con FK (modelo→marca, tipo_falla→sistema_afectado)
# deben aparecer DESPUÉS de su dependencia para que el builder
# resuelva las claves foráneas correctamente.

CATALOG_MODELS: dict[str, Any] = {
    "marca": {
        "model": "catalogos.marca",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "modelo": {
        "model": "catalogos.modelo",
        "fields": ["nombre", "marca"],
        "fk_map": {"marca": {"field": "marca", "lookup": "marca"}},
    },
    "color": {
        "model": "catalogos.color",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "tipo_vehiculo": {
        "model": "catalogos.tipovehiculo",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "tipo_uso": {
        "model": "catalogos.tipouso",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "estatus_vehiculo": {
        "model": "catalogos.estatusvehiculo",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "color_placa": {
        "model": "catalogos.colorplaca",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "clase_vehiculo": {
        "model": "catalogos.clasevehiculo",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "tipo_combustible": {
        "model": "catalogos.tipocombustible",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "sistema_afectado": {
        "model": "catalogos.sistemaafectado",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "tipo_falla": {
        "model": "catalogos.tipofalla",
        "fields": ["descripcion", "sistema_afectado"],
        "fk_map": {"sistema": {"field": "sistema_afectado", "lookup": "sistema_afectado"}},
    },
}

ORGANIZACION_MODELS: dict[str, Any] = {
    "estado": {
        "model": "organizacion.estado",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "gerencia": {
        "model": "organizacion.gerencia",
        "fields": ["nombre"],
        "fk_map": {},
    },
    "centro_servicio": {
        "model": "organizacion.centrodeservicio",
        "fields": ["nombre", "estado"],
        "fk_map": {"estado": "estado"},
    },
}

VEHICULO_COLUMN_MAP: dict[str, str] = {
    "numero_economico": "numero_economico",
    "vin": "vin",
    "placa": "placa",
    "color_placa": "color_placa",
    "placa_intt": "placa_intt",
    "serial_motor": "serial_motor",
    "numero_unidad": "numero_unidad",
    "marca": "marca",
    "modelo": "modelo",
    "anio": "anio",
    "color": "color",
    "tipo_uso": "tipo_uso",
    "clase": "clase",
    "tipo_combustible": "tipo_combustible",
    "estatus": "estatus",
    "estado": "estado",
    "gerencia": "gerencia",
    "unidad_usuaria": "unidad_usuaria",
    "emplazamiento": "emplazamiento",
    "categoria": "categoria",
}

VEHICULO_FK_MAP: dict[str, Any] = {
    "marca": {"field": "marca", "lookup": "marca"},
    "modelo": {"field": "modelo", "lookup": "modelo"},
    "color": {"field": "color", "lookup": "color"},
    "tipo_uso": {"field": "tipo_uso", "lookup": "tipo_uso"},
    "clase": {"field": "clase", "lookup": "clase_vehiculo"},
    "tipo_combustible": {"field": "tipo_combustible", "lookup": "tipo_combustible"},
    "estatus": {"field": "estatus", "lookup": "estatus_vehiculo"},
    "color_placa": {"field": "color_placa", "lookup": "color_placa"},
    "estado": {"field": "estado", "lookup": "estado"},
    "gerencia": {"field": "gerencia", "lookup": "gerencia"},
    "unidad_usuaria": {"field": "unidad_usuaria", "lookup": "gerencia"},
    "emplazamiento": {"field": "emplazamiento", "lookup": "centro_servicio"},
    "categoria": {"field": "categoria", "lookup": "tipo_vehiculo"},
}
