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

# Mapeo de columnas del CSV de flota (AppSheet) → campos internos
# Las claves están en mayúscula SIN acentos (tras limpieza de headers).
FLOTA_COLUMN_MAP: dict[str, str] = {
    "ESTADO": "estado",
    "GERENCIA": "gerencia",
    "UNIDAD USUARIA": "unidad_usuaria",
    "EMPLAZAMIENTO": "emplazamiento",
    "NUMERO DE UNIDAD": "numero_unidad",
    "NUMERO DE ACTIVO SAP": "numero_economico",
    "PLACA": "placa",
    "PLACA INSTITUCIONAL": "placa",
    "PLACA CORPORATIVA": "placa",
    "PLACA CORPORACION ELECTRICA": "placa",
    "COLOR DE PLACA": "color_placa",
    "COLOR DE PLACA INSTITUCIONAL": "color_placa",
    "COLOR DE PLACA CORPORATIVA": "color_placa",
    "COLOR DE PLACA CORPORACION ELECTRICA": "color_placa",
    "PLACA INTT": "placa_intt",
    "SERIAL DE CARROCERIA": "vin",
    "SERIAL MOTOR": "serial_motor",
    "MARCA": "marca",
    "MODELO": "modelo",
    "CLASE": "clase",
    "DENOMINACION DEL ACTIVO FIJO": "categoria",
    "ANO": "anio",
    "COLOR ACTUAL PREDOMINANTE": "color",
    "TIPO COMBUSTIBLE": "tipo_combustible",
    "TIPO ACEITE": "tipo_aceite",
    "LITROS ACEITE": "litros_aceite",
    "SITUACION": "estatus",
    "TIPO DE ADSCRIPCION": "tipo_uso",
    "KILOMETRAJE": "kilometraje",
    "NOMBRES": "nombres",
    "APELLIDOS": "apellidos",
    "CEDULA DE IDENTIDAD": "cedula_identidad",
    "NUMERO DE PERSONAL": "numero_personal",
    "CARGO": "cargo",
    "TELEFONO": "telefono",
    "CORREO": "correo_institucional",
    "CORREO ELECTRONICO": "correo_institucional",
    "CORREO INSTITUCIONAL": "correo_institucional",
    "CORREO CORPORATIVO": "correo_institucional",
    "CORREO CORPORACION ELECTRICA": "correo_institucional",
    "OBSERVACIONES": "observaciones",
    "OBSERVACION CAMBIO DE ESTATUS": "observacion_estatus",
}

# Valores que indican "sin dato" en los CSVs de flota
FLOTA_NA_PATTERNS: set[str] = {"S/P", "S/N", "S/I", "N/A"}

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
