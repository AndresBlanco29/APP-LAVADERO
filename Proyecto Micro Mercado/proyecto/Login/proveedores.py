import tkinter as tk
import mensaje as mb
from Consultas import *
from zyntra_ui import *


class Proveedores(tk.Frame):
    def __init__(self, parent, usuario=None):
        super().__init__(parent, bg=BG)
        self.proveedor = self
        self.usuario = usuario
        self.items()

    def items(self):
        actions = card_frame(self, padx=12, pady=8)
        actions.pack(side="bottom", fill="x")
        primary_button(actions, "Agregar", self.agregar_pro, width=12).pack(side="left", padx=(0, 8))
        secondary_button(actions, "Modificar", self.modi_prove, width=12).pack(side="left", padx=(0, 8))
        danger_button(actions, "Eliminar", self.eliminar_prove, width=12).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        toolbar = card_frame(body, padx=16, pady=12)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        styled_label(toolbar, "Buscar proveedor", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.buscar_proveedores = styled_entry(toolbar, width=36)
        self.buscar_proveedores.pack(fill="x", pady=(6, 0))
        self.buscar_proveedores.bind("<KeyRelease>", lambda _e: debounce(self, "_prov_job", 160, self.buscar))

        self.tree_wrap, self.tree_proveedor = scrollable_tree(
            body,
            columns=("NIT", "Razon_Social", "Telefono", "Direccion"),
            headings=("NIT", "Razón social", "Teléfono", "Dirección"),
            height=5,
            widths={"NIT": 90, "Razon_Social": 150, "Telefono": 100, "Direccion": 140},
        )
        self.tree_proveedor.column("Razon_Social", anchor="w")
        self.tree_proveedor.column("Direccion", anchor="w")
        self.tree_wrap.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.tree_proveedor.bind("<<TreeviewSelect>>", self.obtener_datos)

        form = card_frame(body, padx=16, pady=16)
        form.grid(row=1, column=1, sticky="ns")
        styled_label(form, "Datos del proveedor", FONT_SUB, TEXT, BG_CARD).pack(anchor="w", pady=(0, 10))

        b1, self.NIT_proveedores = labeled_field(form, "NIT")
        b1.pack(fill="x", pady=(0, 10))
        b2, self.nombre_proveedor = labeled_field(form, "Razón social")
        b2.pack(fill="x", pady=(0, 10))
        b3, self.telefono_proveedor = labeled_field(form, "Teléfono")
        b3.pack(fill="x", pady=(0, 10))
        b4, self.direccion_proveedor = labeled_field(form, "Dirección")
        b4.pack(fill="x", pady=(0, 16))
        secondary_button(form, "Borrar campos", self.borrar_campos_proveedores, width=18).pack(fill="x")

    def on_show(self):
        if should_refresh(self):
            self.actualizar_tabla()
        self.buscar_proveedores.focus_set()

    def buscar(self, event=None):
        try:
            buscado = self.buscar_proveedores.get().lower()
            self.tree_proveedor.delete(*self.tree_proveedor.get_children())
            resultado = buscar_proveedor(buscado, buscado)
            for row in resultado or []:
                self.tree_proveedor.insert("", tk.END, values=row)
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.proveedor)

    def borrar_campos_proveedores(self):
        self.buscar_proveedores.delete(0, tk.END)
        self.NIT_proveedores.delete(0, tk.END)
        self.NIT_proveedores.focus()
        self.nombre_proveedor.delete(0, tk.END)
        self.telefono_proveedor.delete(0, tk.END)
        self.direccion_proveedor.delete(0, tk.END)

    def agregar_pro(self):
        try:
            NIT = self.NIT_proveedores.get()
            Nombre = self.nombre_proveedor.get()
            Telefono = self.telefono_proveedor.get()
            Direccion = self.direccion_proveedor.get()
            if not all([NIT, Nombre, Telefono, Direccion]):
                mb.showwarning("Advertencia", "Llene todos los campos", parent=self.proveedor)
                return
            if mb.askyesno("Confirmar", "Desea agregar un nuevo proveedor?", parent=self.proveedor):
                Agregar_Proveedor(NIT, Nombre, Telefono, Direccion)
                mb.showinfo("Exito", "El proveedor se agrego correctamente", parent=self.proveedor)
            self.borrar_campos_proveedores()
            self.actualizar_tabla()
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.proveedor)

    def modi_prove(self):
        try:
            NIT = self.NIT_proveedores.get()
            Nombre = self.nombre_proveedor.get()
            Telefono = self.telefono_proveedor.get()
            Direccion = self.direccion_proveedor.get()
            seleccionado = self.tree_proveedor.selection()
            if not seleccionado:
                mb.showwarning("Advertencia", "Debe seleccionar un proveedor", parent=self.proveedor)
                return
            pregunta = mb.askyesno("Confirmar", "Desea modificar los datos del proveedor", parent=self.proveedor)
            if pregunta:
                modificar_proveedor(Nombre, Telefono, Direccion, NIT)
                mb.showinfo("Exito", "Se han modificado correctamente los datos", parent=self.proveedor)
            self.borrar_campos_proveedores()
            self.actualizar_tabla()
        except ValueError as error:
            mb.showerror("Error {}".format(error), parent=self.proveedor)

    def eliminar_prove(self):
        seleccionado = self.tree_proveedor.selection()
        if not seleccionado:
            mb.showwarning("Advertencia", "Debe seleccionar un proveedor", parent=self.proveedor)
            return
        pregunta = mb.askyesno("Confirmar", "Desea eliminar el proveedor?", parent=self.proveedor)
        if pregunta:
            item = self.tree_proveedor.item(seleccionado, "values")
            from auditoria import log_accion
            eliminar_proveedor(item[0])
            log_accion(self.usuario, "Eliminó registro", f"Proveedor NIT {item[0]} {item[1]}")
            mb.showinfo("Exito", "Se ha eliminado correctamente el proveedor", parent=self.proveedor)
        self.borrar_campos_proveedores()
        self.actualizar_tabla()

    def actualizar_tabla(self):
        def ok(rows):
            self.tree_proveedor.delete(*self.tree_proveedor.get_children())
            for row in rows or []:
                self.tree_proveedor.insert("", tk.END, values=row)
            mark_refreshed(self)

        load_async(self, lambda: mostrar_proveedores() or [], ok)

    def obtener_datos(self, event=None):
        seleccionado = self.tree_proveedor.selection()
        if seleccionado:
            item = self.tree_proveedor.item(seleccionado, "values")
            self.NIT_proveedores.delete(0, tk.END)
            self.NIT_proveedores.insert(0, item[0])
            self.nombre_proveedor.delete(0, tk.END)
            self.nombre_proveedor.insert(0, item[1])
            self.telefono_proveedor.delete(0, tk.END)
            self.telefono_proveedor.insert(0, item[2])
            self.direccion_proveedor.delete(0, tk.END)
            self.direccion_proveedor.insert(0, item[3])
