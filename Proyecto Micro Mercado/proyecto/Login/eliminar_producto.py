import tkinter as tk
import mensaje as mb
import Consultas
from zyntra_ui import *


class Eliminar:
    def __init__(self, parent=None, usuario=None):
        self.usuario = usuario
        self.eliminar = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.eliminar, parent, "Eliminar Producto", 720, 560)
        self.items()

    def items(self):
        footer = card_frame(self.eliminar, padx=16, pady=10)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        self.eliminar_producto = danger_button(footer, "Eliminar productos", self.eliminar_productos, width=22)
        self.eliminar_producto.pack(fill="x")

        body = card_frame(self.eliminar, padx=16, pady=12)
        body.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        styled_label(body, "Eliminar producto", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(body, "Buscar o ingresar código", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w", pady=(10, 0))
        self.buscar_producto = styled_entry(body)
        self.buscar_producto.pack(fill="x", pady=(6, 8))
        self.buscar_producto.focus()

        wrap, self.tree_productos = scrollable_tree(
            body,
            columns=("Codigo", "Nombre", "Precio_de_venta", "Precio_de_Compra", "Cantidad", "Marca"),
            headings=("Código", "Nombre", "P. venta", "P. compra", "Cant.", "Marca"),
            height=12,
            widths={"Codigo": 80, "Nombre": 160, "Precio_de_venta": 90, "Precio_de_Compra": 90, "Cantidad": 70, "Marca": 110},
        )
        self.tree_productos.column("Nombre", anchor="w")
        wrap.pack(fill="both", expand=True)

        for row in Consultas.mostrar_Productos() or []:
            datos = Consultas.parse_producto(row)
            if not datos:
                continue
            self.tree_productos.insert(
                "",
                "end",
                values=(
                    datos["id"],
                    datos["nombre"],
                    formato_dinero(datos["precio_venta"]),
                    formato_dinero(datos["precio_compra"]),
                    datos["cantidad"],
                    datos["marca"],
                ),
            )

    def eliminar_productos(self):
        try:
            Codigo = self.buscar_producto.get()
            producto_seleccionado = self.tree_productos.selection()

            if not Codigo and not producto_seleccionado:
                mb.showwarning(
                    "Advertencia",
                    "Debe ingresar el código del producto o seleccionar un producto en la tabla.",
                    parent=self.eliminar,
                )
                return

            if not Codigo and producto_seleccionado:
                codigo = self.tree_productos.item(producto_seleccionado[0], "values")[0]
                confirmacion = mb.askyesno(
                    "Confirmación",
                    f"¿Está seguro de que desea eliminar el producto con código: {codigo}?",
                    parent=self.eliminar,
                )
                if not confirmacion:
                    return

                producto_eliminado = Consultas.eliminar_producto(codigo)
                if producto_eliminado:
                    from auditoria import log_accion
                    log_accion(self.usuario, "Eliminó registro", f"Producto código {codigo}")
                    mb.showinfo("Éxito", "Producto eliminado correctamente.", parent=self.eliminar)
                    if producto_seleccionado:
                        self.tree_productos.delete(producto_seleccionado[0])
                    else:
                        mb.showerror(
                            "Error",
                            "No se pudo eliminar el producto. Verifique el código ingresado.",
                            parent=self.eliminar,
                        )
        except ValueError as error:
            mb.showerror("Error al eliminar el producto {}".format(error), parent=self.eliminar)
