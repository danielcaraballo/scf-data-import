"""
Django Management Command: importar_flota
========================================
Permite importar y sincronizar periódicamente la flota vehicular en el SCF
a partir de un archivo CSV o Excel normalizado (flota_normalizada.YYYY-MM-DD.xlsx / .csv).

Características:
- Idempotente: Realiza Upsert (update_or_create) por clave natural (VIN, SAP o Placa).
- Preserva Historial: Mantiene la Primary Key (ID) del vehículo en la base de datos,
  garantizando que no se pierdan órdenes de trabajo, siniestros ni mantenimientos.
- Resuelve Catálogos: Realiza get_or_create dinámico para marcas, modelos, estados,
  gerencias y emplazamientos nuevos.
- Soporta --dry-run para simular sin persistir cambios en la base de datos.
"""
from pathlib import Path
from typing import Any

try:
    from django.core.management.base import BaseCommand, CommandError
    from django.db import transaction
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False
    BaseCommand = object  # type: ignore
    CommandError = Exception  # type: ignore

import pandas as pd


class Command(BaseCommand):  # type: ignore[misc]
    help = "Importa o actualiza el inventario de flota en el SCF desde un CSV o Excel normalizado"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "file_path",
            type=str,
            help="Ruta al archivo normalizado (flota_normalizada.YYYY-MM-DD.xlsx o .csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la importación sin guardar cambios en la base de datos",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Tamaño de lote para transacciones de base de datos (por defecto: 500)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not DJANGO_AVAILABLE:
            raise RuntimeError("Django no está instalado en este entorno.")

        file_path = Path(options["file_path"])
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if not file_path.exists():
            raise CommandError(f"El archivo especificado no existe: {file_path}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"Iniciando importación desde: {file_path}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo --dry-run activado: No se guardarán cambios en la base de datos."))

        # 1. Cargar datos con pandas
        ext = file_path.suffix.lower()
        if ext in (".xls", ".xlsx"):
            df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
        elif ext == ".csv":
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        else:
            raise CommandError(f"Formato no soportado ({ext}). Use .xlsx o .csv")

        total_rows = len(df)
        self.stdout.write(f"Total de registros a procesar: {total_rows:,}")

        # 2. Importar modelos de Django dinámicamente
        try:
            from django.apps import apps
            Marca = apps.get_model("catalogos", "Marca")
            Modelo = apps.get_model("catalogos", "Modelo")
            Color = apps.get_model("catalogos", "Color")
            Clase = apps.get_model("catalogos", "Clase")
            Categoria = apps.get_model("catalogos", "Categoria")
            TipoCombustible = apps.get_model("catalogos", "TipoCombustible")
            EstatusVehiculo = apps.get_model("catalogos", "EstatusVehiculo")
            TipoUso = apps.get_model("catalogos", "TipoUso")
            Estado = apps.get_model("organizacion", "Estado")
            Gerencia = apps.get_model("organizacion", "Gerencia")
            Emplazamiento = apps.get_model("organizacion", "Emplazamiento")
            Vehiculo = apps.get_model("vehiculos", "Vehiculo")
        except LookupError as e:
            raise CommandError(f"Error al cargar modelos de Django del SCF: {e}")

        # 3. Procesar registros
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        # Cachés locales en memoria para optimizar get_or_create
        cache_marca: dict[str, Any] = {}
        cache_modelo: dict[tuple[int, str], Any] = {}
        cache_color: dict[str, Any] = {}
        cache_clase: dict[str, Any] = {}
        cache_categoria: dict[str, Any] = {}
        cache_combustible: dict[str, Any] = {}
        cache_estatus: dict[str, Any] = {}
        cache_uso: dict[str, Any] = {}
        cache_estado: dict[str, Any] = {}
        cache_gerencia: dict[tuple[int, str], Any] = {}
        cache_emplazamiento: dict[tuple[int, str], Any] = {}

        try:
            with transaction.atomic():
                for idx, row in df.iterrows():
                    row_num = idx + 2
                    vin = str(row.get("vin", "")).strip().upper()
                    sap = str(row.get("numero_economico", "")).strip()
                    placa = str(row.get("placa", "")).strip().upper()

                    # Verificar al menos un identificador
                    if not vin and not sap and not placa:
                        skipped_count += 1
                        continue

                    try:
                        # Resolver Catálogos
                        marca_name = str(row.get("marca", "")).strip().upper()
                        marca_obj = None
                        if marca_name:
                            if marca_name not in cache_marca:
                                marca_obj, _ = Marca.objects.get_or_create(nombre=marca_name)
                                cache_marca[marca_name] = marca_obj
                            else:
                                marca_obj = cache_marca[marca_name]

                        modelo_name = str(row.get("modelo", "")).strip()
                        modelo_obj = None
                        if modelo_name and marca_obj:
                            key_m = (marca_obj.pk, modelo_name)
                            if key_m not in cache_modelo:
                                modelo_obj, _ = Modelo.objects.get_or_create(
                                    marca=marca_obj,
                                    nombre=modelo_name,
                                )
                                cache_modelo[key_m] = modelo_obj
                            else:
                                modelo_obj = cache_modelo[key_m]

                        color_name = str(row.get("color", "")).strip().title()
                        color_obj = None
                        if color_name:
                            if color_name not in cache_color:
                                color_obj, _ = Color.objects.get_or_create(nombre=color_name)
                                cache_color[color_name] = color_obj
                            else:
                                color_obj = cache_color[color_name]

                        clase_name = str(row.get("clase", "")).strip().title()
                        clase_obj = None
                        if clase_name:
                            if clase_name not in cache_clase:
                                clase_obj, _ = Clase.objects.get_or_create(nombre=clase_name)
                                cache_clase[clase_name] = clase_obj
                            else:
                                clase_obj = cache_clase[clase_name]

                        cat_name = str(row.get("categoria", "")).strip().title()
                        cat_obj = None
                        if cat_name:
                            if cat_name not in cache_categoria:
                                cat_obj, _ = Categoria.objects.get_or_create(nombre=cat_name)
                                cache_categoria[cat_name] = cat_obj
                            else:
                                cat_obj = cache_categoria[cat_name]

                        comb_name = str(row.get("tipo_combustible", "")).strip().title()
                        comb_obj = None
                        if comb_name:
                            if comb_name not in cache_combustible:
                                comb_obj, _ = TipoCombustible.objects.get_or_create(nombre=comb_name)
                                cache_combustible[comb_name] = comb_obj
                            else:
                                comb_obj = cache_combustible[comb_name]

                        estatus_name = str(row.get("estatus", "")).strip().title()
                        estatus_obj = None
                        if estatus_name:
                            if estatus_name not in cache_estatus:
                                estatus_obj, _ = EstatusVehiculo.objects.get_or_create(nombre=estatus_name)
                                cache_estatus[estatus_name] = estatus_obj
                            else:
                                estatus_obj = cache_estatus[estatus_name]

                        uso_name = str(row.get("tipo_uso", "")).strip().title()
                        uso_obj = None
                        if uso_name:
                            if uso_name not in cache_uso:
                                uso_obj, _ = TipoUso.objects.get_or_create(nombre=uso_name)
                                cache_uso[uso_name] = uso_obj
                            else:
                                uso_obj = cache_uso[uso_name]

                        # Resolver Organización
                        estado_name = str(row.get("estado", "")).strip().upper()
                        estado_obj = None
                        if estado_name:
                            if estado_name not in cache_estado:
                                estado_obj, _ = Estado.objects.get_or_create(nombre=estado_name)
                                cache_estado[estado_name] = estado_obj
                            else:
                                estado_obj = cache_estado[estado_name]

                        gerencia_name = str(row.get("gerencia", "")).strip().upper()
                        gerencia_obj = None
                        if gerencia_name and estado_obj:
                            key_g = (estado_obj.pk, gerencia_name)
                            if key_g not in cache_gerencia:
                                gerencia_obj, _ = Gerencia.objects.get_or_create(
                                    estado=estado_obj,
                                    nombre=gerencia_name,
                                )
                                cache_gerencia[key_g] = gerencia_obj
                            else:
                                gerencia_obj = cache_gerencia[key_g]

                        empl_name = str(row.get("emplazamiento", "")).strip()
                        empl_obj = None
                        if empl_name and gerencia_obj:
                            key_e = (gerencia_obj.pk, empl_name)
                            if key_e not in cache_emplazamiento:
                                empl_obj, _ = Emplazamiento.objects.get_or_create(
                                    gerencia=gerencia_obj,
                                    nombre=empl_name,
                                )
                                cache_emplazamiento[key_e] = empl_obj
                            else:
                                empl_obj = cache_emplazamiento[key_e]

                        # Año y Km numéricos
                        try:
                            anio_val = int(row.get("anio", 0)) if str(row.get("anio", "")).strip().isdigit() else None
                        except (ValueError, TypeError):
                            anio_val = None

                        try:
                            km_val = int(row.get("kilometraje", 0)) if str(row.get("kilometraje", "")).strip().isdigit() else None
                        except (ValueError, TypeError):
                            km_val = None

                        try:
                            litros_val = float(str(row.get("litros_aceite", 0)).replace(",", ".")) if str(row.get("litros_aceite", "")).strip() else None
                        except (ValueError, TypeError):
                            litros_val = None

                        # Buscar vehículo existente por clave natural
                        vehiculo = None
                        if vin:
                            vehiculo = Vehiculo.objects.filter(vin=vin).first()
                        if not vehiculo and sap:
                            vehiculo = Vehiculo.objects.filter(numero_economico=sap).first()
                        if not vehiculo and placa:
                            vehiculo = Vehiculo.objects.filter(placa=placa).first()

                        # Preparar campos a actualizar
                        vehicle_data = {
                            "numero_economico": sap,
                            "vin": vin,
                            "placa": placa,
                            "color_placa": str(row.get("color_placa", "")).strip(),
                            "placa_intt": str(row.get("placa_intt", "")).strip(),
                            "serial_motor": str(row.get("serial_motor", "")).strip(),
                            "numero_unidad": str(row.get("numero_unidad", "")).strip(),
                            "subtipo": str(row.get("subtipo", "")).strip(),
                            "anio": anio_val,
                            "kilometraje": km_val,
                            "tipo_aceite": str(row.get("tipo_aceite", "")).strip(),
                            "litros_aceite": litros_val,
                            "unidad_usuaria": str(row.get("unidad_usuaria", "")).strip(),
                            "observaciones": str(row.get("observaciones", "")).strip(),
                            "observacion_estatus": str(row.get("observacion_estatus", "")).strip(),
                            "marca": marca_obj,
                            "modelo": modelo_obj,
                            "color": color_obj,
                            "clase": clase_obj,
                            "categoria": cat_obj,
                            "tipo_combustible": comb_obj,
                            "estatus": estatus_obj,
                            "tipo_uso": uso_obj,
                            "estado": estado_obj,
                            "gerencia": gerencia_obj,
                            "emplazamiento": empl_obj,
                        }

                        if vehiculo:
                            # Actualizar manteniendo PK
                            for key, val in vehicle_data.items():
                                setattr(vehiculo, key, val)
                            if not dry_run:
                                vehiculo.save()
                            updated_count += 1
                        else:
                            # Crear nuevo vehículo
                            if not dry_run:
                                Vehiculo.objects.create(**vehicle_data)
                            created_count += 1

                    except Exception as err:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f"Fila {row_num}: Error procesando vehículo - {err}"))

                if dry_run:
                    # En modo dry-run revertimos explícitamente
                    transaction.set_rollback(True)

        except Exception as e:
            raise CommandError(f"Fallo crítico en la transacción de base de datos: {e}")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("  RESUMEN DE SINCRONIZACIÓN DE FLOTA"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total filas procesadas   : {total_rows:,}")
        self.stdout.write(f"Vehículos actualizados   : {updated_count:,}")
        self.stdout.write(f"Vehículos nuevos creados : {created_count:,}")
        self.stdout.write(f"Filas omitidas (sin id)  : {skipped_count:,}")
        self.stdout.write(f"Errores en filas         : {error_count:,}")
        self.stdout.write("=" * 50 + "\n")
