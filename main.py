import flet as ft
import sqlite3
import os
import traceback

def main(page: ft.Page):
    page.title = "Depuración"
    page.scroll = "adaptive"
    
    # Un contenedor para mostrar mensajes de error si algo explota
    log_view = ft.Column()
    page.add(ft.Text("--- INICIANDO SISTEMA ---"), log_view)

    try:
        # INTENTO 1: Definir ruta segura
        try:
            # En Android, esta ruta suele ser segura para escribir
            ruta_base = "/data/user/0/com.flet.mitiendaapp/files"
            # Si no existe (porque estamos en PC o la ruta cambió), usamos la actual
            if not os.path.exists(ruta_base):
                ruta_base = os.getcwd()
            
            log_view.controls.append(ft.Text(f"1. Ruta base detectada: {ruta_base}", color="blue"))
            page.update()
        except Exception as e:
            log_view.controls.append(ft.Text(f"Error en ruta: {e}", color="orange"))

        # INTENTO 2: Conectar Base de Datos
        db_path = os.path.join(ruta_base, "tienda_v2.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, dato TEXT)")
        conn.commit()
        log_view.controls.append(ft.Text("2. Base de datos Conectada OK", color="green"))
        page.update()

        # --- SI LLEGAMOS AQUI, LA BASE DE DATOS NO ES EL PROBLEMA ---
        
        # Aquí cargamos la interfaz real (simplificada para probar)
        tasa = ft.TextField(label="Probando teclado", value="123")
        btn = ft.ElevatedButton("Prueba Botón", on_click=lambda e: page.add(ft.Text("¡Vivo!")))
        
        page.add(ft.Divider(), ft.Text("Si ves esto, la App funciona:"), tasa, btn)
        page.update()

    except Exception as e:
        # AQUÍ ESTÁ LA MAGIA: Si algo falla arriba, NO se cierra la app.
        # Te muestra el error en rojo en la pantalla.
        error_msg = traceback.format_exc()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("¡ERROR FATAL DETECTADO!", color="red", size=20, weight="bold"),
                    ft.Text(f"Error: {str(e)}", color="red"),
                    ft.Text("Detalles técnicos:", weight="bold"),
                    ft.Text(error_msg, font_family="monospace", size=10)
                ]),
                bgcolor=ft.colors.RED_50,
                padding=20
            )
        )
        page.update()

ft.app(target=main)
