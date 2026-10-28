import tkinter as tk
import mensaje as mb
import modificar_usuarios
import nuevo_usuario
import Consultas as Consultas
from zyntra_ui import *


class Personal(tk.Frame):
    def __init__(self, parent, usuario=None):
        super().__init__(parent, bg=BG)
        self.personal = self
        self.usuario = usuario
        self.items()

    def items(self):
        toolbar = card_frame(self, padx=12, pady=8)
        toolbar.pack(fill="x", pady=(0, 8))
        styled_label(toolbar, "Buscar usuario", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        row = tk.Frame(toolbar, bg=BG_CARD)
        row.pack(fill="x", pady=(6, 0))
        self.buscar_usuario = styled_entry(row, width=36)
        self.buscar_usuario.pack(side="left", fill="x", expand=True)
        self.buscar_usuario.bind("<KeyRelease>", lambda _e: debounce(self, "_pers_job", 160, self.buscar))
        secondary_button(row, "Actualizar tabla", self.actualizar_tabla, width=16).pack(side="left", padx=(10, 0))

        footer = card_frame(self, padx=12, pady=8)
        footer.pack(side="bottom", fill="x")
        sel = tk.Frame(footer, bg=BG_CARD)
        sel.pack(fill="x", pady=(0, 10))
        styled_label(sel, "Usuario seleccionado", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left")
        self.usuario_seleccionado = styled_entry(sel, width=28)
        self.usuario_seleccionado.pack(side="left", padx=(10, 0))

        btns = tk.Frame(footer, bg=BG_CARD)
        btns.pack(fill="x")
        secondary_button(btns, "Modificar usuario seleccionado", self.abrir_modificar_usuario, width=26).pack(side="left", padx=(0, 8))
        primary_button(btns, "Agregar usuario", self.abrir_agregar_usuario, width=18).pack(side="left", padx=(0, 8))
        danger_button(btns, "Eliminar usuario seleccionado", self.Eliminar_usuario, width=26).pack(side="left")

        self.tree_wrap, self.tree_personal = scrollable_tree(
            self,
            columns=("Codigo", "usuario", "password", "nombre", "telefono"),
            headings=("Código", "Usuario", "Password", "Nombre", "Teléfono"),
            height=5,
            widths={"Codigo": 80, "usuario": 120, "password": 120, "nombre": 160, "telefono": 110},
        )
        self.tree_wrap.pack(fill="both", expand=True, pady=(0, 8))
        self.tree_personal.bind("<<TreeviewSelect>>", self.obtener_usuario)

    def on_show(self):
        if should_refresh(self):
            self.actualizar_tabla()

    def actualizar_tabla(self):
        def ok(rows):
            self.tree_personal.delete(*self.tree_personal.get_children())
            for row in rows or []:
                self.tree_personal.insert("", tk.END, values=row)
            mark_refreshed(self)
            self.buscar_usuario.focus_set()

        load_async(self, lambda: Consultas.mostrar_personal() or [], ok)

    def abrir_modificar_usuario(self):
        usuario_data = self.obtener_datos()
        if usuario_data:
            dlg = modificar_usuarios.modificar_usuarios(usuario_data, self.winfo_toplevel())
            self.wait_window(dlg.modi_usuarios)
            self.actualizar_tabla()
        else:
            mb.showwarning("Advertencia", "Seleccione un usuario para modificar.", parent=self.personal)

    def abrir_agregar_usuario(self):
        dlg = nuevo_usuario.nuevo_usuario(self.winfo_toplevel())
        self.wait_window(dlg.nuevo_usuario)
        self.actualizar_tabla()

    def Eliminar_usuario(self):
        try:
            usuario_seleccionado = self.tree_personal.selection()
            if not usuario_seleccionado:
                mb.showinfo("Advertencia", "Seleccione un usuario", parent=self.personal)
                return
            item = self.tree_personal.item(usuario_seleccionado, "values")
            Codigo = item[0]
            from auditoria import log_accion
            Consultas.eliminar_personal(Codigo)
            log_accion(self.usuario, "Eliminó registro", f"Usuario #{Codigo} {item[1]}")
            self.actualizar_tabla()
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.personal)

    def buscar(self, event=None):
        try:
            texto_buscado = self.buscar_usuario.get().lower()
            self.tree_personal.delete(*self.tree_personal.get_children())
            resultado = Consultas.buscar_personal(texto_buscado, texto_buscado, texto_buscado)
            for row in resultado or []:
                self.tree_personal.insert("", tk.END, values=row)
            if self.tree_personal.get_children():
                self.first_item = self.tree_personal.get_children()[0]
                self.tree_personal.selection_set(self.first_item)
                self.obtener_usuario()
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.personal)

    def obtener_usuario(self, event=None):
        try:
            usuario = self.tree_personal.selection()
            if not usuario:
                self.usuario_seleccionado.delete(0, tk.END)
            if usuario:
                item = self.tree_personal.item(usuario, "values")
                nombre_usuario = item[1]
                self.usuario_seleccionado.delete(0, tk.END)
                self.usuario_seleccionado.insert(0, nombre_usuario)
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.personal)

    def obtener_datos(self):
        try:
            usuario = self.tree_personal.selection()
            if usuario:
                return self.tree_personal.item(usuario, "values")
            return None
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.personal)
