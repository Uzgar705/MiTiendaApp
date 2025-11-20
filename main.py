import flet as ft
import sqlite3
import json
import base64
import os
import shutil

def main(page: ft.Page):
    # --- 1. CONFIGURACIÓN INICIAL ---
    page.title = "Gestor de Precios"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "adaptive"
    page.padding = 10

    # --- 2. RUTA SEGURA PARA ANDROID ---
    # Esto evita que la app crashee por no saber dónde guardar el archivo
    try:
        # Buscamos una carpeta donde SI tengamos permiso de escribir
        ruta_base = page.client_storage.get("data_dir") 
        if not ruta_base:
            ruta_base = os.getcwd() # Fallback para PC
        
        ruta_db = os.path.join(ruta_base, "tienda.db")
    except:
        ruta_db = "tienda.db" # Fallback de emergencia

    # --- 3. CONEXIÓN BASE DE DATOS (AHORA DENTRO DE MAIN) ---
    conn = sqlite3.connect(ruta_db, check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                precio REAL,
                img TEXT)""")
    conn.commit()

    # --- SISTEMA DE ARCHIVOS (FilePicker) ---
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    # --- VARIABLES GLOBALES DE LA UI ---
    lista_productos_view = ft.Column()
    tasa_cambio = ft.TextField(label="Tasa BCV", value="40", keyboard_type=ft.KeyboardType.NUMBER, width=100, text_align="center")

    # --- LÓGICA DEL NEGOCIO ---

    def cargar_productos(busqueda=""):
        try:
            lista_productos_view.controls.clear()
            query = "SELECT * FROM productos WHERE nombre LIKE ?"
            c.execute(query, (f"%{busqueda}%",))
            
            items = c.fetchall()
            if not items:
                lista_productos_view.controls.append(ft.Text("No hay productos. Pulsa (+) para agregar.", color="grey"))

            for row in items:
                id_p, nombre, precio, img = row
                
                lbl_res = ft.Text("Total: $0.00 | Bs: 0.00", size=12)
                txt_cant = ft.TextField(label="#", width=60, height=40, content_padding=5, keyboard_type=ft.KeyboardType.NUMBER)
                
                # Función de cálculo
                txt_cant.on_change = lambda e, p=precio, l=lbl_res, t=txt_cant: calcular(e, p, l, t)
                
                # Imagen segura
                src_img = "https://via.placeholder.com/150"
                if img:
                    src_img = img
                
                imagen_widget = ft.Image(src=src_img, width=70, height=70, fit=ft.ImageFit.COVER, border_radius=5,
                                         error_content=ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED))

                card = ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Row([
                                imagen_widget,
                                ft.Column([
                                    ft.Text(nombre, weight="bold", size=16),
                                    ft.Text(f"Ref: ${precio}", color="blue", weight="bold"),
                                ], expand=True),
                                ft.IconButton(icon=ft.icons.DELETE, icon_color="red", on_click=lambda e, i=id_p: borrar_producto(i))
                            ]),
                            ft.Row([txt_cant, lbl_res], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ])
                    )
                )
                lista_productos_view.controls.append(card)
            page.update()
        except Exception as e:
            page.add(ft.Text(f"Error cargando lista: {e}", color="red"))

    def calcular(e, precio_usd, lbl_res, field_cant):
        try:
            cant = float(field_cant.value) if field_cant.value else 0
            tasa = float(tasa_cambio.value) if tasa_cambio.value else 0
            total_usd = cant * precio_usd
            total_bs = total_usd * tasa
            lbl_res.value = f"Total: ${total_usd:.2f} | Bs: {total_bs:,.2f}"
            lbl_res.color = "green" if cant > 0 else "black"
            lbl_res.weight = ft.FontWeight.BOLD if cant > 0 else ft.FontWeight.NORMAL
            page.update()
        except: pass

    def borrar_producto(id_prod):
        c.execute("DELETE FROM productos WHERE id=?", (id_prod,))
        conn.commit()
        cargar_productos()

    # --- IMPORTAR / EXPORTAR ---
    def guardar_archivo_json(e: ft.FilePickerResultEvent):
        if e.path:
            try:
                c.execute("SELECT nombre, precio, img FROM productos")
                productos_exportar = []
                for r in c.fetchall():
                    nombre, precio, ruta_img = r
                    img_data = None
                    if ruta_img and not ruta_img.startswith("http"):
                        try:
                            if os.path.exists(ruta_img):
                                with open(ruta_img, "rb") as image_file:
                                    img_data = base64.b64encode(image_file.read()).decode('utf-8')
                        except: pass
                    item = {"nombre": nombre, "precio": precio, "img_path": ruta_img if ruta_img.startswith("http") else "local", "img_base64": img_data}
                    productos_exportar.append(item)
                
                with open(e.path, 'w', encoding='utf-8') as f:
                    json.dump(productos_exportar, f, ensure_ascii=False)
                page.show_snack_bar(ft.SnackBar(content=ft.Text("✅ Backup guardado!")))
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Error: {ex}")))

    def cargar_archivo_json(e: ft.FilePickerResultEvent):
        if e.files:
            try:
                ruta = e.files[0].path
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                
                # Carpeta segura para fotos importadas
                carpeta_fotos = os.path.join(ruta_base, "fotos_importadas")
                os.makedirs(carpeta_fotos, exist_ok=True)
                
                count = 0
                for item in datos:
                    ruta_final = item.get('img_path')
                    if item.get('img_base64'):
                        nombre_limpio = "".join(x for x in item['nombre'] if x.isalnum())
                        nueva_ruta = os.path.join(carpeta_fotos, f"{nombre_limpio}_{count}.jpg")
                        with open(nueva_ruta, "wb") as img_file:
                            img_file.write(base64.b64decode(item['img_base64']))
                        ruta_final = nueva_ruta

                    c.execute("INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)", (item['nombre'], item['precio'], ruta_final))
                    count += 1
                conn.commit()
                cargar_productos()
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"✅ {count} productos importados!")))
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Error: {ex}")))

    file_picker.on_save_file = guardar_archivo_json
    file_picker.on_result = cargar_archivo_json

    # --- DIALOGO DE AGREGAR ---
    def dialogo_agregar(e):
        def guardar(e):
            if vn.value and vp.value:
                try:
                    prec = float(vp.value)
                    c.execute("INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)", (vn.value, prec, vi.value))
                    conn.commit()
                    dlg.open = False
                    page.update()
                    cargar_productos()
                except: pass
        
        vn = ft.TextField(label="Nombre")
        vp = ft.TextField(label="Precio ($)", keyboard_type=ft.KeyboardType.NUMBER)
        vi = ft.TextField(label="URL Imagen (Opcional)")
        
        dlg = ft.AlertDialog(
            title=ft.Text("Nuevo Producto"),
            content=ft.Column([vn, vp, vi], height=180, tight=True),
            actions=[ft.TextButton("Guardar", on_click=guardar)]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # --- ARMADO DE PANTALLA ---
    page.appbar = ft.AppBar(
        title=ft.Text("Mi Tienda"),
        bgcolor=ft.colors.BLUE_GREY_900,
        color="white",
        actions=[
            ft.IconButton(icon=ft.icons.UPLOAD, on_click=lambda e: file_picker.save_file(file_name="backup.json")),
            ft.IconButton(icon=ft.icons.DOWNLOAD, on_click=lambda e: file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])),
        ]
    )

    page.add(
        ft.Container(height=10),
        ft.Row([tasa_cambio, ft.FloatingActionButton(icon=ft.icons.ADD, on_click=dialogo_agregar)], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.TextField(prefix_icon=ft.icons.SEARCH, hint_text="Buscar...", on_change=lambda e: cargar_productos(e.control.value)),
        lista_productos_view
    )
    
    # Cargar inicial
    cargar_productos()

ft.app(target=main)
