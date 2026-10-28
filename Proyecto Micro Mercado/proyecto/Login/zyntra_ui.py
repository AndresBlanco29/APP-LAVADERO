import time
import tkinter as tk
from tkinter import ttk

from dinero import (
    cursor_tras_digitos,
    formato_dinero,
    formato_entrada,
    parse_dinero,
    parse_dinero_o_none,
    redondear_centena,
)

APP_NAME = "Zyntra POS"

# Paleta marca con más contraste (mismos tonos, más vivos)
BG = "#070A10"
BG_HEADER = "#0C1018"
BG_CARD = "#141925"
BG_ELEVATED = "#1E2536"
BG_INPUT = "#222A3C"
BG_NAV = "#0E121C"
ACCENT = "#3B82FF"
ACCENT_HOVER = "#5B9AFF"
ACCENT_DARK = "#2563EB"
PURPLE = "#B794F6"
PURPLE_DARK = "#7C5CFF"
CYAN = "#67D4FF"
TEXT = "#FFFFFF"
TEXT_MUTED = "#D2D6E2"
TEXT_DIM = "#9AA1B4"
BORDER = "#3A455C"
DANGER = "#FF4D4F"
DANGER_HOVER = "#FF7875"
SUCCESS = "#2DD46A"
WARNING = "#FFB020"

FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_HEADING = ("Segoe UI", 18, "bold")
FONT_SUB = ("Segoe UI", 13)
FONT_BODY = ("Segoe UI", 13)
FONT_LABEL = ("Segoe UI", 12)
FONT_BUTTON = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 11)
FONT_MONEY = ("Segoe UI", 30, "bold")
FONT_LOGO = ("Segoe UI", 20, "bold")
FONT_POS = ("Segoe UI", 14)
FONT_POS_BTN = ("Segoe UI", 14, "bold")
FONT_POS_TOTAL = ("Segoe UI", 28, "bold")
FONT_NAV = ("Segoe UI", 13, "bold")
FONT_TABLE = ("Segoe UI", 14)
FONT_TABLE_HEAD = ("Segoe UI", 12, "bold")


def debounce(widget, attr, delay_ms, callback):
    job = getattr(widget, attr, None)
    if job:
        try:
            widget.after_cancel(job)
        except Exception:
            pass
    setattr(widget, attr, widget.after(int(delay_ms), callback))


def should_refresh(obj, attr="_last_refresh", seconds=20):
    now = time.monotonic()
    last = getattr(obj, attr, 0)
    if now - last < seconds:
        return False
    setattr(obj, attr, now)
    return True


def load_async(widget, fetcher, on_ok, on_err=None):
    """Consulta en segundo plano y pinta en el hilo de Tk para no congelar la UI."""
    import threading

    token = int(getattr(widget, "_load_token", 0) or 0) + 1
    widget._load_token = token

    def work():
        err = None
        data = None
        try:
            data = fetcher()
        except Exception as error:
            err = error

        def apply():
            if int(getattr(widget, "_load_token", 0) or 0) != token:
                return
            if err is not None:
                if on_err:
                    on_err(err)
                return
            on_ok(data)

        try:
            widget.after(0, apply)
        except tk.TclError:
            pass

    threading.Thread(target=work, daemon=True, name="zyntra-load").start()


def fill_tree_chunked(widget, tree, rows, chunk=40, on_done=None):
    """Inserta filas en tandas para que la ventana siga respondiendo."""
    try:
        tree.delete(*tree.get_children())
    except tk.TclError:
        return
    data = list(rows or [])
    token = int(getattr(widget, "_fill_token", 0) or 0) + 1
    widget._fill_token = token
    idx = [0]
    insert = tree.insert

    def step():
        if int(getattr(widget, "_fill_token", 0) or 0) != token:
            return
        try:
            if not tree.winfo_exists():
                return
        except tk.TclError:
            return
        end = min(idx[0] + chunk, len(data))
        for item in data[idx[0]:end]:
            if isinstance(item, dict):
                insert("", tk.END, values=item.get("values"), tags=item.get("tags") or ())
            elif isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[1], (tuple, list)):
                insert("", tk.END, values=item[0], tags=item[1])
            else:
                insert("", tk.END, values=item)
        idx[0] = end
        if idx[0] < len(data):
            widget.after(1, step)
        elif on_done:
            on_done()

    widget.after(0, step)


def mark_refreshed(obj, attr="_last_refresh"):
    setattr(obj, attr, time.monotonic())


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(start, end, t):
    return int(start + (end - start) * t)


def work_area(win=None):
    """Área visible del escritorio (sin barra de tareas)."""
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width > 200 and height > 200:
                return rect.left, rect.top, width, height
    except Exception:
        pass
    if win is not None:
        try:
            return 0, 0, win.winfo_screenwidth(), max(480, win.winfo_screenheight() - 80)
        except tk.TclError:
            pass
    return 0, 0, 1366, 688


def clamp_to_work_area(win, width, height, margin=8):
    left, top, area_w, area_h = work_area(win)
    width = min(max(int(width), 360), max(360, area_w - margin))
    height = min(max(int(height), 320), max(320, area_h - margin))
    x = left + max(0, (area_w - width) // 2)
    y = top + max(0, (area_h - height) // 2)
    try:
        win.maxsize(area_w, area_h)
    except tk.TclError:
        pass
    return width, height, x, y


def center_window(win, width, height):
    win.update_idletasks()
    width, height, x, y = clamp_to_work_area(win, width, height)
    win.geometry(f"{width}x{height}+{x}+{y}")
    return width, height


def limit_minsize(win, min_w, min_h):
    _, _, area_w, area_h = work_area(win)
    win.minsize(min(int(min_w), area_w), min(int(min_h), area_h))


def setup_window(win, title, width, height, resizable=False):
    apply_ttk_styles()
    win.title(f"{title} — {APP_NAME}")
    win.configure(bg=BG)
    win.geometry(f"{width}x{height}")
    if not resizable:
        win.resizable(False, False)
    center_window(win, width, height)
    return width, height


def setup_app_root(win):
    apply_ttk_styles()
    win.title(APP_NAME)
    win.configure(bg=BG)
    win.minsize(900, 560)
    try:
        win.state("zoomed")
    except tk.TclError:
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        win.geometry(f"{screen_w}x{screen_h}+0+0")


def prepare_modal(win, parent, title, width, height, resizable=False):
    apply_ttk_styles()
    win.title(f"{title} — {APP_NAME}")
    win.configure(bg=BG)
    width, height, x, y = clamp_to_work_area(win, width, height)
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.resizable(resizable, resizable)
    if parent is not None:
        try:
            win.transient(parent.winfo_toplevel())
            win.grab_set()
        except tk.TclError:
            pass
    center_window(win, width, height)


def size_modal_to_content(win, inner, extra_height=0, prefer_width=None):
    """Ensancha la ventana y la hace tan alta como el contenido; el scroll queda como último recurso."""
    win.update_idletasks()
    inner.update_idletasks()
    _, _, area_w, area_h = work_area(win)
    if prefer_width is None:
        prefer_width = min(1440, area_w - 16)
    width = min(max(int(prefer_width), 820), max(640, area_w - 16))
    height = int(inner.winfo_reqheight()) + int(extra_height)
    height = min(max(height, min(520, area_h - 16)), area_h - 16)
    return center_window(win, width, height)


def clear_container(container):
    for child in list(container.winfo_children()):
        child.destroy()


def card_frame(parent, padx=24, pady=20):
    frame = tk.Frame(
        parent,
        bg=BG_CARD,
        padx=padx,
        pady=pady,
        highlightthickness=1,
        highlightbackground=BORDER,
    )
    return frame


def labeled_field(parent, text, bg=BG_CARD):
    box = tk.Frame(parent, bg=bg)
    styled_label(box, text, FONT_LABEL, TEXT_MUTED, bg).pack(anchor="w")
    entry = styled_entry(box)
    entry.pack(fill="x", pady=(6, 0))
    return box, entry


def scrollable_body(parent, bg=BG_CARD, padx=28, pady=20):
    """Área con scroll vertical limitado al contenido. La barra solo aparece si hace falta."""
    wrap = tk.Frame(parent, bg=bg)
    wrap.grid_rowconfigure(0, weight=1)
    wrap.grid_columnconfigure(0, weight=1)
    canvas = tk.Canvas(wrap, bg=bg, highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(wrap, orient="vertical", style="Vertical.TScrollbar")
    canvas.grid(row=0, column=0, sticky="nsew")
    inner = tk.Frame(canvas, bg=bg, padx=padx, pady=pady)
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    job = {"id": None}

    def _can_scroll():
        try:
            return inner.winfo_reqheight() > canvas.winfo_height() + 2
        except tk.TclError:
            return False

    def _clamp():
        if not _can_scroll():
            canvas.yview_moveto(0)
            return
        first, last = canvas.yview()
        span = last - first
        if first < 0:
            canvas.yview_moveto(0)
        elif last > 1:
            canvas.yview_moveto(max(0.0, 1.0 - span))

    def _yview(*args):
        if not _can_scroll():
            canvas.yview_moveto(0)
            return
        canvas.yview(*args)
        _clamp()

    def _on_vsb(*args):
        if not _can_scroll():
            vsb.set(0, 1)
            return
        vsb.set(*args)

    vsb.configure(command=_yview)
    canvas.configure(yscrollcommand=_on_vsb)

    def _refresh():
        try:
            if not canvas.winfo_exists():
                return
            cw = max(canvas.winfo_width(), 1)
            ch = max(canvas.winfo_height(), 1)
            canvas.itemconfigure(window_id, width=cw)
            inner.update_idletasks()
            ih = max(inner.winfo_reqheight(), 1)
            if ih > ch + 2:
                vsb.grid(row=0, column=1, sticky="ns")
                canvas.configure(scrollregion=(0, 0, cw, ih))
                _clamp()
            else:
                vsb.grid_remove()
                canvas.yview_moveto(0)
                canvas.configure(scrollregion=(0, 0, cw, ch))
        except tk.TclError:
            pass

    def _schedule(_event=None):
        if job["id"] is not None:
            try:
                wrap.after_cancel(job["id"])
            except tk.TclError:
                pass
        try:
            job["id"] = wrap.after_idle(_refresh)
        except tk.TclError:
            pass

    def _over_this(event):
        try:
            if not canvas.winfo_exists():
                return False
            widget = wrap.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return False
        while widget is not None:
            if widget is wrap:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _wheel(event):
        if not _over_this(event):
            return
        if not _can_scroll():
            return
        first, last = canvas.yview()
        steps = 0
        if getattr(event, "delta", 0):
            steps = int(-1 * (event.delta / 120)) or (-1 if event.delta > 0 else 1)
        elif getattr(event, "num", None) == 4:
            steps = -1
        elif getattr(event, "num", None) == 5:
            steps = 1
        if steps < 0 and first <= 0:
            return
        if steps > 0 and last >= 1:
            return
        canvas.yview_scroll(steps, "units")
        _clamp()

    def _bind(_event=None):
        if getattr(wrap, "_wheel_bound", False):
            return
        wrap._wheel_bound = True
        canvas.bind_all("<MouseWheel>", _wheel, add="+")
        canvas.bind_all("<Button-4>", _wheel, add="+")
        canvas.bind_all("<Button-5>", _wheel, add="+")

    inner.bind("<Configure>", _schedule)
    canvas.bind("<Configure>", _schedule)
    wrap.bind("<Map>", _bind)
    wrap.refresh_scroll = _schedule
    return wrap, inner


_styles_ok = False


def apply_ttk_styles(force=False):
    global _styles_ok
    if _styles_ok and not force:
        return
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "Zyntra.Treeview",
        background=BG_CARD,
        foreground=TEXT,
        fieldbackground=BG_CARD,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        rowheight=36,
        font=FONT_TABLE,
    )
    style.configure(
        "Zyntra.Treeview.Heading",
        background=BG_ELEVATED,
        foreground=CYAN,
        bordercolor=BORDER,
        relief="flat",
        font=FONT_TABLE_HEAD,
        padding=(10, 12),
    )
    style.map(
        "Zyntra.Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", TEXT)],
    )
    # Permite que los tags (stock bajo) se vean con el tema clam.
    def _tree_map(option):
        return [elm for elm in style.map("Zyntra.Treeview", query_opt=option) if elm[:2] != ("!disabled", "!selected")]

    try:
        style.map(
            "Zyntra.Treeview",
            foreground=_tree_map("foreground"),
            background=_tree_map("background"),
        )
    except tk.TclError:
        pass
    style.map(
        "Zyntra.Treeview.Heading",
        background=[("active", ACCENT_DARK)],
        foreground=[("active", TEXT)],
    )
    style.configure(
        "Zyntra.TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_INPUT,
        foreground=TEXT,
        arrowcolor=CYAN,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=8,
        font=FONT_POS,
    )
    style.map(
        "Zyntra.TCombobox",
        fieldbackground=[("readonly", BG_INPUT)],
        foreground=[("readonly", TEXT)],
        background=[("readonly", BG_INPUT)],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=BG_ELEVATED,
        troughcolor=BG,
        bordercolor=BORDER,
        arrowcolor=TEXT,
        relief="flat",
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=BG_ELEVATED,
        troughcolor=BG,
        bordercolor=BORDER,
        arrowcolor=TEXT,
        relief="flat",
    )
    _styles_ok = True


def bind_hover(widget, normal, hover):
    widget.bind("<Enter>", lambda _e: widget.config(bg=hover))
    widget.bind("<Leave>", lambda _e: widget.config(bg=normal))


def rounded_rect(canvas, x1, y1, x2, y2, radius=12, fill=BG_CARD, outline=""):
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, fill=fill, outline=outline)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, fill=fill, outline=outline)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, fill=fill, outline=outline)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, fill=fill, outline=outline)
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=outline)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=outline)


def draw_gradient_text(canvas, x, y, text, font, c1=PURPLE, c2=CYAN, anchor="w"):
    if anchor in ("center", "e"):
        probe = canvas.create_text(0, 0, text=text, font=font, anchor="w")
        bbox = canvas.bbox(probe)
        canvas.delete(probe)
        text_w = (bbox[2] - bbox[0]) if bbox else 0
        if anchor == "center":
            x = x - text_w // 2
        else:
            x = x - text_w
    rgb1 = _hex_to_rgb(c1)
    rgb2 = _hex_to_rgb(c2)
    cx = x
    total = max(len(text) - 1, 1)
    for i, char in enumerate(text):
        t = i / total
        color = "#{:02x}{:02x}{:02x}".format(
            _lerp(rgb1[0], rgb2[0], t),
            _lerp(rgb1[1], rgb2[1], t),
            _lerp(rgb1[2], rgb2[2], t),
        )
        item = canvas.create_text(cx, y, text=char, fill=color, font=font, anchor="w")
        bbox = canvas.bbox(item)
        if bbox:
            cx = bbox[2] + 1
    return cx


def draw_logo_mark(canvas, x, y, size=36):
    rounded_rect(canvas, x, y, x + size, y + size, radius=9, fill=PURPLE_DARK)
    canvas.create_text(
        x + size / 2,
        y + size / 2,
        text="Z",
        fill=TEXT,
        font=("Segoe UI", max(12, size // 2), "bold"),
    )


def draw_background(parent, width, height):
    canvas = tk.Canvas(
        parent,
        width=width,
        height=height,
        bg=BG,
        highlightthickness=0,
        bd=0,
    )
    canvas.place(x=0, y=0)
    canvas.create_oval(-120, -140, 340, 300, fill="#15102A", outline="")
    canvas.create_oval(width - 360, height - 280, width + 140, height + 80, fill="#0D1730", outline="")
    canvas.create_oval(width * 0.45, -80, width * 0.85, 180, fill="#101828", outline="")

    dots = [
        (80, 90), (160, 70), (240, 110), (width - 90, 80),
        (width - 180, 140), (90, height - 70), (width - 70, height - 90),
        (width // 2, 50), (width // 3, height - 40),
    ]
    for i, (x, y) in enumerate(dots):
        canvas.create_oval(x, y, x + 3, y + 3, fill="#3A4560", outline="")
        if i + 1 < len(dots):
            x2, y2 = dots[i + 1]
            canvas.create_line(x + 1, y + 1, x2 + 1, y2 + 1, fill="#1E2638")
    return canvas


def draw_header(canvas, width, subtitle, height=78):
    canvas.create_rectangle(0, 0, width, height, fill=BG_HEADER, outline="")
    canvas.create_rectangle(0, height - 2, width, height, fill=ACCENT, outline="")
    draw_logo_mark(canvas, 22, 20, 38)
    draw_gradient_text(canvas, 72, 28, APP_NAME, FONT_LOGO)
    canvas.create_text(72, 54, text=subtitle, fill=TEXT_MUTED, font=FONT_SMALL, anchor="w")
    return height


def canvas_label(canvas, x, y, text, font=FONT_LABEL, fill=TEXT_MUTED, anchor="w"):
    return canvas.create_text(x, y, text=text, fill=fill, font=font, anchor=anchor)


def styled_entry(parent, width=24, show=None, font=None, justify="left"):
    entry = tk.Entry(
        parent,
        width=width,
        font=font or FONT_POS,
        show=show or "",
        justify=justify,
        bg=BG_INPUT,
        fg=TEXT,
        insertbackground=CYAN,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        bd=6,
    )
    return entry


def styled_label(parent, text, font=FONT_LABEL, fg=TEXT_MUTED, bg=BG):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg)


def money_label(parent, text="$ 0", font=FONT_MONEY, fg=CYAN, bg=BG_CARD):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg)


def bind_money_entry(entry, on_change=None):
    """Formatea un Entry en vivo: 1500000 → 1'500.000"""

    def _fmt(event=None):
        if event is not None and getattr(event, "keysym", "") in (
            "Left",
            "Right",
            "Up",
            "Down",
            "Home",
            "End",
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Tab",
        ):
            if on_change:
                on_change(event)
            return
        bruto = entry.get()
        try:
            pos = entry.index(tk.INSERT)
        except tk.TclError:
            pos = len(bruto)
        digitos_antes = sum(1 for c in bruto[:pos] if c.isdigit())
        formateado = formato_entrada(bruto)
        if formateado != bruto:
            entry.delete(0, tk.END)
            if formateado:
                entry.insert(0, formateado)
            try:
                entry.icursor(cursor_tras_digitos(formateado, digitos_antes))
            except tk.TclError:
                pass
        if on_change:
            on_change(event)

    entry.bind("<KeyRelease>", _fmt)
    return entry


def _base_button(parent, text, command, bg, fg, hover, font=FONT_BUTTON, width=None, height=2):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground=fg,
        font=font,
        relief="flat",
        bd=0,
        cursor="hand2",
        width=width,
        height=height,
        padx=14,
        pady=8,
        highlightthickness=0,
    )
    bind_hover(btn, bg, hover)
    return btn


def secondary_button(parent, text, command, width=None, height=2, font=FONT_BUTTON):
    btn = _base_button(parent, text, command, BG_ELEVATED, TEXT, "#3A4560", font, width, height)
    btn.configure(
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        padx=16,
        pady=10,
    )
    return btn


def danger_button(parent, text, command, width=None, height=2, font=FONT_BUTTON):
    btn = _base_button(parent, text, command, DANGER, TEXT, DANGER_HOVER, font, width, height)
    btn.configure(padx=16, pady=10)
    return btn


def warning_button(parent, text, command, width=None, height=2, font=FONT_BUTTON):
    btn = _base_button(parent, text, command, WARNING, BG, "#FFC94D", font, width, height)
    btn.configure(padx=16, pady=10)
    return btn


def primary_button(parent, text, command, width=None, height=2, font=FONT_BUTTON):
    btn = _base_button(parent, text, command, ACCENT, TEXT, ACCENT_HOVER, font, width, height)
    btn.configure(padx=16, pady=10)
    return btn


def nav_button(parent, text, command, width=11, active=False):
    bg = ACCENT if active else BG_ELEVATED
    hover = ACCENT_HOVER if active else "#3A4560"
    btn = _base_button(parent, text, command, bg, TEXT, hover, FONT_NAV, width, 2)
    btn.configure(
        padx=16,
        pady=10,
        highlightthickness=1,
        highlightbackground=ACCENT if active else BORDER,
        highlightcolor=CYAN,
    )
    return btn


def plus_button(parent, command):
    btn = _base_button(parent, "+", command, ACCENT, TEXT, ACCENT_HOVER, ("Segoe UI", 20, "bold"), 4, 1)
    btn.configure(padx=14, pady=8)
    return btn


def themed_treeview(parent, columns, headings=None, height=10, show="headings"):
    tree = ttk.Treeview(
        parent,
        columns=columns,
        show=show,
        height=height,
        style="Zyntra.Treeview",
    )
    headings = headings or columns
    for col, heading in zip(columns, headings):
        tree.heading(col, text=heading)
    configure_stock_tags(tree)
    return tree


def configure_stock_tags(tree):
    tree.tag_configure("bajo", background="#5C1A1A", foreground="#FECACA")
    tree.tag_configure("vence7", background="#7F1D1D", foreground="#FECACA")
    tree.tag_configure("vence15", background="#7C2D12", foreground="#FED7AA")
    tree.tag_configure("vence30", background="#713F12", foreground="#FDE68A")
    tree.tag_configure("anulada", background="#3F1717", foreground="#FECACA")
    tree.tag_configure("espera", background="#3F2E12", foreground="#FDE68A")
    tree.tag_configure("ok", background=BG_CARD, foreground=TEXT)


def tree_frame(parent):
    frame = tk.Frame(parent, bg=BORDER, bd=1, highlightthickness=0)
    return frame


def scrollable_tree(
    parent,
    columns,
    headings=None,
    height=5,
    widths=None,
    stretch=None,
    minwidths=None,
    autofit=True,
    max_rows=28,
):
    wrap = tk.Frame(parent, bg=BORDER, bd=1, highlightthickness=0)
    inner = tk.Frame(wrap, bg=BG_CARD)
    inner.pack(fill="both", expand=True, padx=1, pady=1)

    tree = themed_treeview(inner, columns, headings, height)
    vsb = ttk.Scrollbar(inner, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    inner.grid_rowconfigure(0, weight=1)
    inner.grid_columnconfigure(0, weight=1)

    widths = widths or {}
    minwidths = minwidths or {}
    for col in columns:
        tree.column(
            col,
            anchor="center",
            width=widths.get(col, 90),
            minwidth=minwidths.get(col, 48),
            stretch=True,
        )

    # Autofit acotado: evita bucles CreateDIBSection (altura enorme / canvas+tree).
    if autofit:
        job = {"id": None}
        tope = max(8, int(max_rows or 28))

        def _fit(event):
            if event.widget is not inner:
                return
            h = int(event.height or 0)
            if h < 70 or h > 1400:
                return
            rows = max(4, min(tope, (h - 40) // 34))
            try:
                current = int(str(tree.cget("height")))
            except (tk.TclError, ValueError, TypeError):
                current = 0
            if current != rows:
                tree.configure(height=rows)

        def _sched(event):
            if job["id"] is not None:
                try:
                    inner.after_cancel(job["id"])
                except tk.TclError:
                    pass
            job["id"] = inner.after(100, lambda e=event: _fit(e))

        inner.bind("<Configure>", _sched)
    return wrap, tree


class HeaderBar(tk.Frame):
    def __init__(self, parent, subtitle=""):
        super().__init__(parent, bg=BG_HEADER, height=68)
        self.pack_propagate(False)

        left = tk.Frame(self, bg=BG_HEADER)
        left.pack(side="left", fill="y", padx=16, pady=10)

        logo = tk.Canvas(left, width=40, height=40, bg=BG_HEADER, highlightthickness=0)
        logo.pack(side="left")
        draw_logo_mark(logo, 2, 2, 36)

        titles = tk.Frame(left, bg=BG_HEADER)
        titles.pack(side="left", padx=(12, 0), fill="y")
        self.brand = tk.Canvas(titles, width=180, height=28, bg=BG_HEADER, highlightthickness=0)
        self.brand.pack(anchor="w")
        draw_gradient_text(self.brand, 0, 14, APP_NAME, FONT_LOGO)
        self.subtitle_lbl = styled_label(titles, subtitle, FONT_BODY, TEXT_MUTED, BG_HEADER)
        self.subtitle_lbl.pack(anchor="w")

        right = tk.Frame(self, bg=BG_HEADER)
        right.pack(side="right", padx=18)
        self.date_lbl = styled_label(right, "", ("Segoe UI", 15, "bold"), CYAN, BG_HEADER)
        self.date_lbl.pack(anchor="e")
        self.time_lbl = styled_label(right, "", FONT_BODY, TEXT_MUTED, BG_HEADER)
        self.time_lbl.pack(anchor="e")

        tk.Frame(self, bg=ACCENT, height=2).place(relx=0, rely=1, relwidth=1, y=-2)

    def set_subtitle(self, text):
        self.subtitle_lbl.config(text=text)

    def set_datetime(self, date_text, time_text):
        self.date_lbl.config(text=date_text)
        self.time_lbl.config(text=time_text)
