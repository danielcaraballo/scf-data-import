# SCF Data Import - ETL de Normalización de Flota

Pipeline ETL modular, idempotente y extensible para la ingestión, normalización, validación y reporte del inventario de flota vehicular de la Corporación de Energía / SCF.

---

## 🏗 Arquitectura del Proyecto

```
scf-data-import/
├── config/
│   ├── mappings/             # Archivos CSV editables para canonicalización de catálogos
│   │   ├── adscripcion.csv
│   │   ├── clases.csv
│   │   ├── colores.csv
│   │   ├── colores_placa.csv
│   │   ├── combustibles.csv
│   │   ├── emplazamientos.csv
│   │   ├── estados.csv
│   │   ├── estatus.csv
│   │   ├── gerencias.csv
│   │   ├── marcas.csv
│   │   ├── modelos.csv
│   │   └── tipos.csv
│   └── rules.toml            # Umbrales, campos requeridos, rangos de año y patrones N/A
├── src/
│   └── scf_import/
│       ├── __main__.py       # Orquestador CLI principal (argparse)
│       ├── config.py         # Mapeos de columnas y definiciones de modelos
│       ├── derived.py        # Derivación de catálogos y organización para fixtures
│       ├── extract.py        # Extracción robusta: autodetección de separador, BOM, headers
│       ├── load.py           # Generación de CSV maestro, CSV de revisión y fixtures Django
│       ├── report.py         # Generación de resumen de calidad e identificadores
│       ├── validate.py       # Deduplicación por claves de negocio y reglas de calidad
│       ├── transform/
│       │   ├── text.py       # Normalización de texto, NFKD, números VE, códigos
│       │   ├── canonical.py  # Motor de mapeos: alias → canónico
│       │   ├── fields.py     # Reglas de campo: VIN, SAP, Placa, Año, Km, Unidad
│       │   └── row.py        # Transformación de fila cruda → NormalizedRow
│       └── builders/         # Constructores de fixtures Django (opcional)
└── tests/
    ├── data/
    │   └── flota_sucia.csv   # Dataset sintético realista para golden tests
    ├── test_canonical.py     # Pruebas del motor de mapeos
    ├── test_extract.py       # Pruebas de extracción y autodetección
    ├── test_fields.py        # Pruebas de reglas de campo
    ├── test_golden_flota.py  # Golden end-to-end integration test
    ├── test_text.py          # Pruebas de utilidades de texto
    └── test_validate.py      # Pruebas de validación y deduplicación
```

---

## 🚀 Ejecución del Pipeline

### 1. Menú Interactivo (Recomendado)
Ejecute el lanzador interactivo para seleccionar archivos y opciones con un menú guiado:

* **En Windows (Doble clic o terminal)**:
  ```cmd
  run.bat
  ```
* **En Linux / macOS**:
  ```bash
  ./run.sh
  # o: python run.py
  ```

---

## 💻 Uso Avanzado por Línea de Comandos (CLI)

### 1. Ejecución con archivo específico
```bash
python -m scf_import --flota data/flota.2026-07-16.csv --output output/
```

### 2. Ejecución automatizada en Cron (toma el archivo más reciente)
```bash
python -m scf_import --dir data/ --output output/
```

### 3. Generación opcional de Fixtures para Django y Excel
```bash
python -m scf_import --flota data/flota.2026-07-16.csv --fixtures --excel
```

### 4. Modo Dry-Run (Validación sin escribir en disco)
```bash
python -m scf_import --flota data/flota.2026-07-16.csv --dry-run -v
```

### 5. Opciones avanzadas de configuración
```bash
python -m scf_import --flota data/flota.2026-07-16.csv \
    --mappings config/mappings \
    --rules config/rules.toml \
    --output output/ \
    --fixtures \
    --excel \
    --verbose
```

---

## 📊 Salidas del Pipeline

Cada ejecución genera salidas idempotentes y fechadas en la carpeta de salida (`output/`):

1. **`flota_normalizada.<fecha>.csv`** (CSV Maestro - 30 columnas):
   - Una fila por vehículo.
   - Columnas canónicas normalizadas (`marca`, `modelo`, `vin`, `placa`, `numero_economico`, `kilometraje`, `tipo_aceite`, `litros_aceite`, `observacion_estatus`, `estado`, `emplazamiento`, etc.).
   - Metadatos de calidad y auditoría técnica: `calidad` (`OK`, `ADVERTENCIA`, `INVALIDO`), `flags`, `errores`, `advertencias`.

2. **`flota_normalizada.<fecha>.xlsx`** (Excel Maestro - 26 columnas, con `--excel`):
   - 26 columnas limpias con toda la información técnica y operativa real (incluyendo aceites, diagnósticos de taller y kilometraje).
   - **Excluye deliberadamente las columnas de calidad/auditoría y URLs de imágenes** para brindar una tabla limpia optimizada para tablas dinámicas, filtros y manipulación manual.

3. **`revision.<fecha>.csv`** (CSV de Revisión Humana):
   - Detalla cada anomalía detectada para alimentar los mappings o corregir en origen.
   - Columnas: `fila_origen`, `campo_afectado`, `tipo_problema`, `valor_original`, `valor_normalizado`, `sugerencia_o_detalle`, `sap`, `vin`, `placa`.

4. **Fixtures Django** (`output/fixtures/`, opcional con `--fixtures`):
   - `01_catalogos.json`
   - `02_organizacion.json`
   - `03_vehiculos.json`

---

## ⚙️ Configuración y Mappings Editables

Los mappings viven en `config/mappings/*.csv` y pueden ser editados directamente:
- **`marcas.csv`**: Mapea alias (`CHEVY`, `GENERAL MOTOR`, `NEW HOLLANDO`) a marcas canónicas (`CHEVROLET`, `NEW HOLLAND`).
- **`modelos.csv`**: Mapea variantes (`300-816`, `HINO 300 (816)`, `F-350 UNICESTA`) a modelos canónicos (`300 (816)`, `F-350`).
- **`estados.csv`**: Normaliza nombres de estado (`CAPITAL` → `DISTRITO CAPITAL`, `LA GUAIRA` → `VARGAS`).
- **`emplazamientos.csv`**: Normaliza nombres de centros de servicio, subestaciones y talleres.

---

## 🔒 Seguridad y Privacidad de Datos

Este repositorio sigue las mejores prácticas de seguridad de la información (InfoSec) y protección de datos personales (PII):
- **Datos confidenciales protegidos**: Los archivos de datos reales (`data/*`) y las salidas generadas (`output/*`) están completamente excluidos del control de versiones mediante `.gitignore`.
- **Datos 100% sintéticos para pruebas**: Todos los tests y fixtures de prueba incluidos en el repositorio (`tests/data/flota_sucia.csv` y `data_test/`) utilizan nombres, identificadores y seriales ficticios.
- **Trazabilidad y Auditoría**: El sistema genera reportes de revisión que facilitan la corrección en origen sin exponer credenciales ni información reservada.

---

## 🔄 Carga de Fixtures en Django

Para poblar la base de datos de Django manteniendo la integridad referencial de Foreign Keys:

```bash
# 1. Catálogos base (Marcas, Modelos, Colores, Tipos, Estatus, Combustibles, etc.)
python manage.py loaddata output/fixtures/01_catalogos.json

# 2. Estructura organizacional (Estados, Gerencias, Centros de Servicio)
python manage.py loaddata output/fixtures/02_organizacion.json

# 3. Flota vehicular completa vinculada
python manage.py loaddata output/fixtures/03_vehiculos.json
```

---

## 🧪 Pruebas y Calidad de Código

Ejecutar la suite completa de pruebas, linter y comprobador de tipos estricto:

```bash
pytest
ruff check .
mypy src
```

