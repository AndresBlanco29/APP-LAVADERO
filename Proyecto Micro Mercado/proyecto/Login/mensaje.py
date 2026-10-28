"""Diálogos de notificación Zyntra — más grandes que messagebox nativo."""
import tkinter as tk

from zyntra_ui import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BG_CARD,
    BG_ELEVATED,
    BORDER,
    CYAN,
    DANGER,
    SUCCESS,
    TEXT,
    TEXT_MUTED,
    WARNING,
    secondary_button,
    styled_label,
    work_area,
)


_KIND = {
    "info": (SUCCESS, "i"),
    "error": (DANGER, "!"),
    "warning": (WARNING, "!"),
    "question": (ACCENT, "?"),
}


def _parent_root(parent):
    if parent is None:
        return None
    try:
        return parent.winfo_toplevel()
    except tk.TclError:
        return parent


def _style_btn(btn, active):
    """Resalta el botón enfocado; el mouse sigue funcionando igual."""
    try:
        if active:
            btn.configure(
                bg=ACCENT,
                activebackground=ACCENT_HOVER,
                highlightthickness=2,
                highlightbackground=CYAN,
                highlightcolor=CYAN,
            )
        else:
            btn.configure(
                bg=BG_ELEVATED,
                activebackground="#3A4560",
                highlightthickness=1,
                highlightbackground=BORDER,
                highlightcolor=BORDER,
            )
    except tk.TclError:
        pass


def _dialog(title, message, kind="info", parent=None, buttons=("Aceptar",), default=0):
    """Muestra un diálogo modal grande y devuelve el índice del botón pulsado."""
    root = _parent_root(parent)
    win = tk.Toplevel(root) if root is not None else tk.Toplevel()
    win.title(str(title or "Zyntra POS"))
    win.configure(bg=BG)
    win.resizable(False, False)
    try:
        win.transient(root if root is not None else win)
        win.grab_set()
    except tk.TclError:
        pass

    n_buttons = len(buttons)
    focus = {"idx": default if 0 <= default < n_buttons else 0}
    result = {"value": focus["idx"]}
    color, glyph = _KIND.get(kind, _KIND["info"])

    # Tamaño base responsivo respecto al área útil / ventana padre
    try:
        _, _, area_w, area_h = work_area(win)
    except Exception:
        area_w, area_h = 1280, 720
    try:
        if root is not None:
            area_w = max(area_w, root.winfo_width())
            area_h = max(area_h, root.winfo_height())
    except tk.TclError:
        pass

    dlg_w = max(420, min(560, int(area_w * 0.36)))
    if area_w < 700:
        dlg_w = max(340, area_w - 48)

    outer = tk.Frame(win, bg=BG, padx=18, pady=18)
    outer.pack(fill="both", expand=True)

    card = tk.Frame(outer, bg=BG_CARD, padx=28, pady=24)
    card.pack(fill="both", expand=True)

    header = tk.Frame(card, bg=BG_CARD)
    header.pack(fill="x", pady=(0, 16))

    badge = tk.Canvas(header, width=48, height=48, bg=BG_CARD, highlightthickness=0)
    badge.pack(side="left")
    badge.create_oval(4, 4, 44, 44, fill=color, outline="")
    badge.create_text(24, 24, text=glyph, fill=TEXT, font=("Segoe UI", 18, "bold"))

    titles = tk.Frame(header, bg=BG_CARD)
    titles.pack(side="left", fill="x", expand=True, padx=(14, 0))
    styled_label(titles, str(title or ""), ("Segoe UI", 18, "bold"), TEXT, BG_CARD).pack(anchor="w")
    styled_label(titles, "Zyntra POS", ("Segoe UI", 11), TEXT_MUTED, BG_CARD).pack(anchor="w", pady=(2, 0))

    msg = str(message or "")
    wrap = max(280, dlg_w - 100)
    lbl = styled_label(card, msg, ("Segoe UI", 14), TEXT, BG_CARD)
    lbl.configure(wraplength=wrap, justify="left")
    lbl.pack(anchor="w", fill="x", pady=(0, 22))

    actions = tk.Frame(card, bg=BG_CARD)
    actions.pack(fill="x")

    def _close(idx):
        result["value"] = idx
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    btn_refs = []

    def _apply_focus(idx):
        if not btn_refs:
            return
        idx = max(0, min(int(idx), len(btn_refs) - 1))
        focus["idx"] = idx
        for i, btn in enumerate(btn_refs):
            _style_btn(btn, i == idx)
        try:
            btn_refs[idx].focus_set()
        except tk.TclError:
            pass

    def _move(delta):
        if len(btn_refs) <= 1:
            return "break"
        # Orden visual izquierda→derecha: No/Cancelar (idx 1) luego Sí/Aceptar (idx 0)
        visual = list(range(len(btn_refs) - 1, -1, -1)) if len(btn_refs) > 1 else [0]
        try:
            pos = visual.index(focus["idx"])
        except ValueError:
            pos = 0
        pos = (pos + int(delta)) % len(visual)
        _apply_focus(visual[pos])
        return "break"

    def _on_enter(_e=None):
        _close(focus["idx"])
        return "break"

    for i, label in enumerate(buttons):
        btn = secondary_button(
            actions,
            label,
            lambda idx=i: _close(idx),
            width=14,
            height=2,
            font=("Segoe UI", 12, "bold"),
        )
        # Sí/Aceptar (i==0) a la derecha; No/Cancelar a la izquierda
        side = "right" if n_buttons > 1 and i == 0 else "left"
        btn.pack(side=side, padx=(0, 10) if side == "left" else 0, fill="x", expand=(n_buttons == 1))
        btn.bind("<FocusIn>", lambda _e, idx=i: _apply_focus(idx))
        btn.bind("<Left>", lambda _e: _move(-1))
        btn.bind("<Right>", lambda _e: _move(1))
        btn.bind("<Up>", lambda _e: _move(-1))
        btn.bind("<Down>", lambda _e: _move(1))
        btn.bind("<Return>", _on_enter)
        btn.bind("<KP_Enter>", _on_enter)
        btn.bind("<space>", _on_enter)
        btn.bind("<Enter>", lambda _e, idx=i: _apply_focus(idx))
        btn_refs.append(btn)

    win.bind("<Escape>", lambda _e: _close(1 if n_buttons > 1 else 0))
    win.bind("<Return>", _on_enter)
    win.bind("<KP_Enter>", _on_enter)
    win.bind("<Left>", lambda _e: _move(-1))
    win.bind("<Right>", lambda _e: _move(1))
    win.bind("<Up>", lambda _e: _move(-1))
    win.bind("<Down>", lambda _e: _move(1))
    win.protocol("WM_DELETE_WINDOW", lambda: _close(1 if n_buttons > 1 else 0))

    win.update_idletasks()
    need_h = outer.winfo_reqheight() + 8
    dlg_h = max(240, min(need_h, int(area_h * 0.6), area_h - 40))
    x = max(0, (area_w - dlg_w) // 2)
    y = max(0, (area_h - dlg_h) // 3)
    try:
        if root is not None:
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = max(root.winfo_width(), dlg_w)
            rh = max(root.winfo_height(), dlg_h)
            x = rx + max(0, (rw - dlg_w) // 2)
            y = ry + max(0, (rh - dlg_h) // 3)
    except tk.TclError:
        pass
    win.minsize(dlg_w, min(240, dlg_h))
    win.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")
    try:
        win.focus_force()
        _apply_focus(focus["idx"])
    except tk.TclError:
        pass

    win.wait_window()
    return result["value"]


def showinfo(title, message, parent=None, **_kwargs):
    _dialog(title, message, kind="info", parent=parent, buttons=("Aceptar",), default=0)
    return "ok"


def showerror(title, message, parent=None, **_kwargs):
    _dialog(title, message, kind="error", parent=parent, buttons=("Aceptar",), default=0)
    return "ok"


def showwarning(title, message, parent=None, **_kwargs):
    _dialog(title, message, kind="warning", parent=parent, buttons=("Aceptar",), default=0)
    return "ok"


def askyesno(title, message, parent=None, **_kwargs):
    return _dialog(title, message, kind="question", parent=parent, buttons=("Sí", "No"), default=0) == 0


def askokcancel(title, message, parent=None, **_kwargs):
    return _dialog(title, message, kind="question", parent=parent, buttons=("Aceptar", "Cancelar"), default=0) == 0


def askquestion(title, message, parent=None, **_kwargs):
    return "yes" if askyesno(title, message, parent=parent) else "no"
