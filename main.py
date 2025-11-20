import flet as ft
import sqlite3
import json
import base64
import os
import traceback

def main(page: ft.Page):
    # --- CONFIGURACIÓN DE LA VENTANA ---
    page.title = "Gestor de Precios"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "adaptive"
    page.padding = 10

    # --- BASE DE DATOS (SQLite) ---
    conn = sqlite3.connect("tienda.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                precio REAL,
                img TEXT)""")
    conn.commit()

    # --- SISTEMA DE ARCHIVOS (FilePicker) ---
    file_picker = ft.FilePicker()       # para export/import (json)
    img_picker = ft.FilePicker()        # para seleccionar imagen al agregar producto
    page.overlay.append(file_picker)
    page.overlay.append(img_picker)

    # variable compartida para ruta de imagen seleccionada en el diálogo
    selected_image_path = {"path": ""}

    # --- LÓGICA DE EXPORTAR (Guardar Backup) ---
    def guardar_archivo_json(e: ft.FilePickerResultEvent):
        path = getattr(e, "path", None)
        if not path:
            page.show_snack_bar(ft.SnackBar(content=ft.Text("❌ Ruta de guardado inválida.")))
            return
        try:
            c.execute("SELECT nombre, precio, img FROM productos")
            productos_exportar = []
            for r in c.fetchall():
                nombre, precio, ruta_img = r
                img_data = None

                # Si es una foto local, intentamos codificarla a base64 (si existe)
                if ruta_img and not ruta_img.startswith("http"):
                    try:
                        if os.path.exists(ruta_img):
                            with open(ruta_img, "rb") as image_file:
                                img_data = base64.b64encode(image_file.read()).decode("utf-8")
                    except Exception as ex:
                        print("Warning al codificar imagen:", ex)

                item = {
                    "nombre": nombre,
                    "precio": precio,
                    "img_path": ruta_img or "",
                    "img_base64": img_data
                }
                productos_exportar.append(item)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(productos_exportar, f, ensure_ascii=False, indent=2)

            page.show_snack_bar(ft.SnackBar(content=ft.Text("✅ Lista exportada con éxito!")))
        except Exception as ex:
            tb = traceback.format_exc()
            print(tb)
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error al exportar: {ex}")))

    # --- LÓGICA DE IMPORTAR (Cargar Backup) ---
    def cargar_archivo_json(e: ft.FilePickerResultEvent):
        if not getattr(e, "files", None):
            page.show_snack_bar(ft.SnackBar(content=ft.Text("❌ No se seleccionó archivo.")))
            return
        try:
            ruta = e.files[0].path
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)

            inserted = 0
            updated = 0
            skipped = 0
            # Carpeta interna para fotos importadas: si existe data_dir en client_storage úsalo, si no usa cwd
            try:
                data_dir = page.client_storage.get("data_dir") or ""
            except Exception:
                data_dir = ""
            if not data_dir:
                data_dir = os.getcwd()
            carpeta_fotos = os.path.join(data_dir, "fotos_importadas")
            os.makedirs(carpeta_fotos, exist_ok=True)

            for idx, item in enumerate(datos):
                nombre_item = (item.get("nombre") or "").strip()
                # Si está vacío el nombre, saltarlo
                if not nombre_item:
                    skipped += 1
                    continue

                # price safe
                try:
                    precio_val = float(item.get("precio", 0) or 0)
                except Exception:
                    precio_val = 0.0

                ruta_final = item.get("img_path", "") or ""
                # Reconstruir foto desde el código Base64 (si existe)
                if item.get("img_base64"):
                    nombre_limpio = "".join(x for x in nombre_item if x.isalnum()) or "img"
                    nueva_ruta = os.path.join(carpeta_fotos, f"{nombre_limpio}_{idx}.jpg")
                    try:
                        with open(nueva_ruta, "wb") as img_file:
                            img_file.write(base64.b64decode(item["img_base64"]))
                        ruta_final = nueva_ruta
                    except Exception as ex:
                        print("Error escribiendo imagen importada:", ex)

                # Buscar producto por nombre (match para update). Ajusta si prefieres otro criterio.
                c.execute("SELECT id, precio, img FROM productos WHERE nombre=?", (nombre_item,))
                existing = c.fetchone()
                if existing:
                    prod_id, prod_precio, prod_img = existing
                    # Decidir campos a actualizar: actualiza precio y la img si ruta_final no está vacío (si está vacío mantiene la anterior)
                    new_price = precio_val
                    new_img = ruta_final if ruta_final else prod_img
                    try:
                        c.execute("UPDATE productos SET precio=?, img=? WHERE id=?", (new_price, new_img, prod_id))
                        updated += 1
                    except Exception as ex:
                        print("Error actualizando producto:", ex)
                        skipped += 1
                else:
                    try:
                        c.execute(
                            "INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)",
                            (nombre_item, precio_val, ruta_final),
                        )
                        inserted += 1
                    except Exception as ex:
                        print("Error insertando producto:", ex)
                        skipped += 1

            conn.commit()
            cargar_productos()
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"✅ Insertados: {inserted}. Actualizados: {updated}. Omitidos: {skipped}")))
        except Exception as ex:
            tb = traceback.format_exc()
            print(tb)
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error al importar: {ex}")))

    # img_picker on_result: recibe selección de imagen para el diálogo de nuevo producto
    def img_picker_result(e: ft.FilePickerResultEvent):
        try:
            if getattr(e, "files", None):
                p = e.files[0].path
                selected_image_path["path"] = p
                if "img_field" in globals_dialog_refs:
                    globals_dialog_refs["img_field"].value = p
                    page.update()
        except Exception as ex:
            print("Error en img_picker_result:", ex)

    # registrar manejadores
    file_picker.on_save_file = guardar_archivo_json
    file_picker.on_result = cargar_archivo_json
    img_picker.on_result = img_picker_result

    # --- UI: Variables y Elementos ---
    lista_productos_view = ft.Column()
    tasa_cambio = ft.TextField(
        label="Tasa BCV", value="40", keyboard_type=ft.KeyboardType.NUMBER, width=100, text_align="center"
    )

    # auxiliar para referenciar controles del diálogo desde el callback del picker
    globals_dialog_refs = {}

    # --- FUNCIÓN PRINCIPAL: CÁLCULOS ---
    def calcular(e, precio_usd, lbl_res, field_cant):
        try:
            cant = float(field_cant.value) if field_cant.value else 0.0
        except Exception:
            cant = 0.0
        try:
            tasa = float(tasa_cambio.value) if tasa_cambio.value else 0.0
        except Exception:
            tasa = 0.0

        total_usd = cant * precio_usd
        total_bs = total_usd * tasa

        lbl_res.value = f"Total: ${total_usd:.2f} | Bs: {total_bs:,.2f}"
        lbl_res.color = "green" if cant > 0 else "black"
        lbl_res.weight = ft.FontWeight.BOLD if cant > 0 else ft.FontWeight.NORMAL
        page.update()

    # --- BORRAR PRODUCTO ---
    def borrar_producto(id_prod):
        try:
            c.execute("DELETE FROM productos WHERE id=?", (id_prod,))
            conn.commit()
            cargar_productos()
        except Exception as ex:
            print("Error borrar producto:", ex)
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error al borrar: {ex}")))

    # --- RENDERIZADO DE LISTA ---
    def cargar_productos(busqueda=""):
        lista_productos_view.controls.clear()
        try:
            query = "SELECT * FROM productos WHERE nombre LIKE ?"
            c.execute(query, (f"%{busqueda}%",))
            items = c.fetchall()
            if not items:
                lista_productos_view.controls.append(
                    ft.Text("No hay productos. Agrega uno con el botón (+)", color="grey")
                )
            else:
                for row in items:
                    id_p, nombre, precio, img = row

                    lbl_res = ft.Text("Total: $0.00 | Bs: 0.00", size=12)
                    txt_cant = ft.TextField(
                        label="#",
                        width=60,
                        height=40,
                        content_padding=5,
                        keyboard_type=ft.KeyboardType.NUMBER,
                    )

                    txt_cant.on_change = lambda e, p=precio, l=lbl_res, t=txt_cant: calcular(e, p, l, t)

                    src_img = img if img else "https://via.placeholder.com/150"
                    imagen_widget = ft.Image(
                        src=src_img,
                        width=70,
                        height=70,
                        fit=ft.ImageFit.COVER,
                        border_radius=5,
                        error_content=ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED),
                    )

                    card = ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            imagen_widget,
                                            ft.Column(
                                                [
                                                    ft.Text(nombre, weight=ft.FontWeight.BOLD, size=16),
                                                    ft.Text(f"Ref: ${precio}", color="blue", weight=ft.FontWeight.BOLD),
                                                ],
                                                expand=True,
                                            ),
                                            ft.IconButton(
                                                icon=ft.icons.DELETE,
                                                icon_color="red",
                                                on_click=lambda e, i=id_p: borrar_producto(i),
                                            ),
                                        ]
                                    ),
                                    ft.Row([txt_cant, lbl_res], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ]
                            ),
                        )
                    )
                    lista_productos_view.controls.append(card)
        except Exception as ex:
            print("Error cargando productos:", ex)
            page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error: {ex}")))
        page.update()

    # --- DIÁLOGO AGREGAR PRODUCTO (con validación y selector de imagen) ---
    def dialogo_agregar(e):
        globals_dialog_refs.clear()
        selected_image_path["path"] = ""

        err_text = ft.Text("", color="red", size=12)
        vn = ft.TextField(label="Nombre")
        vp = ft.TextField(label="Precio ($)", keyboard_type=ft.KeyboardType.NUMBER)
        vi = ft.TextField(label="Imagen (ruta)", read_only=True)
        globals_dialog_refs["img_field"] = vi

        def seleccionar_imagen(ev):
            img_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png"])

        def limpiar_imagen(ev):
            selected_image_path["path"] = ""
            vi.value = ""
            page.update()

        def guardar(ev):
            if not vn.value or not vn.value.strip():
                err_text.value = "Completa el nombre."
                page.update()
                return
            try:
                prec = float(vp.value)
            except Exception:
                err_text.value = "Precio inválido."
                page.update()
                return

            ruta = selected_image_path["path"] or ""
            try:
                c.execute("INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)", (vn.value.strip(), prec, ruta))
                conn.commit()
                dlg.open = False
                page.update()
                cargar_productos()
                page.show_snack_bar(ft.SnackBar(content=ft.Text("✅ Producto agregado!")))
            except Exception as ex:
                print("Error guardar producto:", ex)
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error al guardar: {ex}")))

        btn_select_img = ft.ElevatedButton("Seleccionar imagen...", on_click=seleccionar_imagen)
        btn_clear_img = ft.TextButton("Limpiar", on_click=limpiar_imagen)

        dlg = ft.AlertDialog(
            title=ft.Text("Nuevo Producto"),
            content=ft.Column(
                [
                    vn,
                    vp,
                    ft.Row([vi, btn_select_img, btn_clear_img], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    err_text,
                ],
                height=220,
                tight=True,
            ),
            actions=[ft.TextButton("Guardar", on_click=guardar), ft.TextButton("Cancelar", on_click=lambda e: close_dlg())],
        )

        def close_dlg():
            dlg.open = False
            page.update()

        page.dialog = dlg
        dlg.open = True
        page.update()

    # --- BARRA SUPERIOR ---
    page.appbar = ft.AppBar(
        title=ft.Text("Mi Tienda"),
        bgcolor=ft.colors.BLUE_GREY_900,
        color="white",
        actions=[
            ft.IconButton(
                icon=ft.icons.UPLOAD, tooltip="Exportar Backup", on_click=lambda e: file_picker.save_file(file_name="backup_tienda.json")
            ),
            ft.IconButton(
                icon=ft.icons.DOWNLOAD, tooltip="Importar Backup", on_click=lambda e: file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])
            ),
        ],
    )

    # --- LAYOUT PRINCIPAL ---
    search_field = ft.TextField(
        prefix_icon=ft.icons.SEARCH,
        hint_text="Buscar producto...",
        on_change=lambda e: cargar_productos(e.control.value),
    )

    page.add(
        ft.Container(height=10),
        ft.Row([tasa_cambio, ft.FloatingActionButton(icon=ft.icons.ADD, on_click=dialogo_agregar)], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        search_field,
        lista_productos_view,
    )

    # Inicializar lista
    cargar_productos()

ft.app(target=main)
