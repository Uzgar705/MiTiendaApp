import flet as ft
import sqlite3
import json
import base64
import os
import shutil

def main(page: ft.Page):
    page.title = "Gestor de Precios PRO"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "adaptive"

    # --- BASE DE DATOS ---
    conn = sqlite3.connect("tienda.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                precio REAL,
                img TEXT)""")
    conn.commit()

    # --- UTILIDADES DE ARCHIVOS (FilePicker) ---
    # Esto permite abrir y guardar archivos en el celular/PC
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    # --- LÓGICA PRO: IMPORTAR / EXPORTAR CON FOTOS ---

    def guardar_archivo_json(e: ft.FilePickerResultEvent):
        if e.path:
            try:
                c.execute("SELECT nombre, precio, img FROM productos")
                productos_exportar = []
                
                for r in c.fetchall():
                    nombre, precio, ruta_img = r
                    img_data = None
                    
                    # Verificamos si es una imagen local (del teléfono) y si existe
                    if ruta_img and not ruta_img.startswith("http"):
                        try:
                            if os.path.exists(ruta_img):
                                with open(ruta_img, "rb") as image_file:
                                    # AQUÍ OCURRE LA MAGIA: Convertimos foto a texto
                                    img_data = base64.b64encode(image_file.read()).decode('utf-8')
                        except:
                            pass # Si falla la foto, se va sin foto

                    item = {
                        "nombre": nombre,
                        "precio": precio,
                        "img_path": ruta_img if ruta_img.startswith("http") else "local",
                        "img_base64": img_data # Aquí va la foto codificada
                    }
                    productos_exportar.append(item)
                
                with open(e.path, 'w', encoding='utf-8') as f:
                    json.dump(productos_exportar, f, ensure_ascii=False)
                
                page.show_snack_bar(ft.SnackBar(content=ft.Text("✅ Copia de seguridad (con fotos) creada!")))
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error: {ex}")))

    def cargar_archivo_json(e: ft.FilePickerResultEvent):
        if e.files:
            try:
                ruta = e.files[0].path
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                
                count = 0
                # Carpeta donde guardaremos las fotos recuperadas en el nuevo teléfono
                carpeta_fotos = os.path.join(os.getcwd(), "fotos_importadas")
                os.makedirs(carpeta_fotos, exist_ok=True)

                for item in datos:
                    ruta_final = item.get('img_path')
                    
                    # Si viene con foto codificada (Base64), hay que reconstruirla
                    if item.get('img_base64'):
                        nombre_limpio = "".join(x for x in item['nombre'] if x.isalnum()) # Quitar símbolos raros
                        nueva_ruta = os.path.join(carpeta_fotos, f"{nombre_limpio}_{count}.jpg")
                        
                        # MAGIA INVERSA: De texto a archivo de imagen
                        with open(nueva_ruta, "wb") as img_file:
                            img_file.write(base64.b64decode(item['img_base64']))
                        ruta_final = nueva_ruta

                    # Guardar en base de datos
                    c.execute("INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)", 
                              (item['nombre'], item['precio'], ruta_final))
                    count += 1
                
                conn.commit()
                cargar_productos()
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"✅ Se importaron {count} productos y sus fotos!")))
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error al importar: {ex}")))
                # Insertamos los datos nuevos
                count = 0
                for item in datos:
                    # Verificamos si ya existe para no duplicar (opcional)
                    c.execute("INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)", 
                              (item['nombre'], item['precio'], item['img']))
                    count += 1
                conn.commit()
                cargar_productos() # Refrescar pantalla
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"✅ Se importaron {count} productos!")))
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"❌ Error al leer archivo: {ex}")))

    # Conectamos los eventos del selector de archivos
    file_picker.on_save_file = guardar_archivo_json
    file_picker.on_result = cargar_archivo_json


    # --- FUNCIONES DE LA APP (Igual que antes) ---
    def calcular(e, precio_usd, lbl_res, field_cant):
        try:
            cant = float(field_cant.value) if field_cant.value else 0
            tasa = float(tasa_cambio.value) if tasa_cambio.value else 0
            lbl_res.value = f"Total: ${cant*precio_usd:.2f} | Bs: {cant*precio_usd*tasa:,.2f}"
            lbl_res.color = "green" if cant > 0 else "black"
            lbl_res.weight = "bold" if cant > 0 else "normal"
            page.update()
        except: pass

    def borrar_producto(id_prod):
        c.execute("DELETE FROM productos WHERE id=?", (id_prod,))
        conn.commit()
        cargar_productos()

    lista_productos_view = ft.Column()
    tasa_cambio = ft.TextField(label="Tasa BCV", value="40", keyboard_type="number", width=100)

    def cargar_productos(busqueda=""):
        lista_productos_view.controls.clear()
        query = "SELECT * FROM productos WHERE nombre LIKE ?"
        c.execute(query, (f"%{busqueda}%",))
        for row in c.fetchall():
            id_p, nombre, precio, img = row
            lbl_res = ft.Text("Total: $0.00 | Bs: 0.00", size=12)
            txt_cant = ft.TextField(label="#", width=60, height=40, content_padding=5, keyboard_type="number")
            txt_cant.on_change = lambda e, p=precio, l=lbl_res, t=txt_cant: calcular(e, p, l, t)
            
            lista_productos_view.controls.append(
                ft.Card(content=ft.Container(padding=10, content=ft.Column([
                    ft.Row([
                        ft.Image(src=img if img else "https://via.placeholder.com/80", width=60, height=60, fit="cover", border_radius=5),
                        ft.Column([ft.Text(nombre, weight="bold"), ft.Text(f"${precio}", color="blue")], expand=True),
                        ft.IconButton(icon=ft.icons.DELETE, icon_color="red", on_click=lambda e, i=id_p: borrar_producto(i))
                    ]),
                    ft.Row([txt_cant, lbl_res], alignment="spaceBetween")
                ])))
            )
        page.update()

    def dialogo_agregar(e):
        def guardar(e):
            if vn.value and vp.value:
                c.execute("INSERT INTO productos (nombre, precio, img) VALUES (?, ?, ?)", 
                          (vn.value, float(vp.value), vi.value))
                conn.commit()
                dlg.open = False
                page.update()
                cargar_productos()
        
        vn, vp, vi = ft.TextField(label="Nombre"), ft.TextField(label="Precio", keyboard_type="number"), ft.TextField(label="URL Imagen")
        dlg = ft.AlertDialog(title=ft.Text("Nuevo"), content=ft.Column([vn, vp, vi], height=150), 
                             actions=[ft.TextButton("Guardar", on_click=guardar)])
        page.dialog = dlg
        dlg.open = True
        page.update()

    # --- BOTONES DE EXPORTAR / IMPORTAR ---
    def clic_exportar(e):
        file_picker.save_file(file_name="lista_precios.json", caption="Guardar lista de precios")
    
    def clic_importar(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"], dialog_title="Selecciona el archivo json")

    # --- BARRA SUPERIOR (APPBAR) ---
    page.appbar = ft.AppBar(
        title=ft.Text("Mi Tienda"),
        bgcolor=ft.colors.BLUE_GREY_900,
        color="white",
        actions=[
            ft.IconButton(icon=ft.icons.UPLOAD_FILE, tooltip="Exportar Lista", on_click=clic_exportar),
            ft.IconButton(icon=ft.icons.DOWNLOAD_FOR_OFFLINE, tooltip="Importar Lista", on_click=clic_importar),
        ]
    )

    # --- CUERPO PRINCIPAL ---
    page.add(
        ft.Row([tasa_cambio, ft.FloatingActionButton(icon=ft.icons.ADD, on_click=dialogo_agregar)], alignment="center"),
        ft.TextField(prefix_icon=ft.icons.SEARCH, hint_text="Buscar...", on_change=lambda e: cargar_productos(e.control.value)),
        ft.Divider(),
        lista_productos_view
    )
    cargar_productos()


ft.app(target=main)
