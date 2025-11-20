import flet as ft

def main(page: ft.Page):
    page.title = "Prueba Flet"
    page.add(ft.Text("Hola — la app mínima funciona ✅"))
    page.add(ft.Text("Si esta pantalla aparece, el empaquetador está bien. Si no, hay problema con el servicio de compilación."))

ft.app(target=main)
