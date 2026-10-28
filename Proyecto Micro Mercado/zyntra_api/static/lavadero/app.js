const S = {
  token: localStorage.getItem("lv_token") || "",
  sesion: JSON.parse(localStorage.getItem("lv_sesion") || "null"),
  vista: "lavar",
  catalogo: null,
  branchId: Number(localStorage.getItem("lv_branch") || 0),
  zonaId: Number(localStorage.getItem("lv_zona") || 0),
  ordenes: [],
  draft: null,
  modal: null,
  reporte: null,
  resumen: null,
  preset: "mes",
  comparar: "mes_anterior",
  ajuste: "menu",
  soloProductos: false,
  timer: null,
  bolsillosDraft: null,
  olvide: false,
  recupero: new URLSearchParams(location.search).get("recuperar") || "",
  gastos: null,
  gastosPeriodo: "hoy",
  gastoApartado: "pagos",
  gastoEdit: null,
};

function logoMarca() {
  return `<svg class="logo" viewBox="0 0 140 78" aria-hidden="true">
    <path d="M6 28h22M2 38h20M8 48h16" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
    <path d="M40 46c1-14 12-22 26-22h16c10 0 16 5 21 14l7 8h10c5 0 8 3 8 7v7H36v-7c0-4 2-7 4-7z" fill="currentColor"/>
    <path d="M62 28h14c6 0 10 3 13 8" fill="none" stroke="#1e9b45" stroke-width="3" stroke-linecap="round"/>
    <circle cx="62" cy="60" r="9" fill="currentColor"/>
    <circle cx="104" cy="60" r="9" fill="currentColor"/>
    <circle cx="62" cy="60" r="4" fill="#1e9b45"/>
    <circle cx="104" cy="60" r="4" fill="#1e9b45"/>
  </svg>`;
}

function normalizarPlaca(valor) {
  return String(valor || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
}

function normalizarNombreCliente(valor) {
  return String(valor || "")
    .toUpperCase()
    .replace(/[^A-ZÁÉÍÓÚÜÑ ]/g, "")
    .replace(/ {2,}/g, " ")
    .slice(0, 80);
}

function soloDigitos(valor) {
  return String(valor || "").replace(/\D/g, "").slice(0, 10);
}

function nombreEmpleado(persona) {
  if (!persona) return "";
  let nombre = String(persona.nombre || "").trim();
  let apellido = String(persona.apellido || "").trim();
  if (!apellido) {
    const partes = nombre.split(/\s+/).filter(Boolean);
    if (partes.length > 1) {
      apellido = partes.pop();
      nombre = partes.join(" ");
    }
  }
  return [nombre, apellido].filter(Boolean).join(" ");
}

function puedeRegistrar() {
  if (!totalDraft()) return false;
  if (S.soloProductos) return true;
  return Boolean(S.draft.tipoId)
    && S.draft.servicios.length > 0
    && S.draft.empleados.length > 0
    && normalizarPlaca(S.draft.placa).length >= 5
    && normalizarNombreCliente(S.draft.nombre).trim().length >= 3
    && soloDigitos(S.draft.tel).length >= 10;
}

function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function plata(valor) {
  const n = Math.round(Number(valor) || 0);
  const signo = n < 0 ? "-" : "";
  return signo + "$" + Math.abs(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function margenUtilidad(costo, precio) {
  const venta = Number(precio);
  const base = Number(costo);
  if (!(venta > 0) || !Number.isFinite(base)) return null;
  return (1 - base / venta) * 100;
}

function precioDesdeMargen(costo, margen) {
  const base = Number(costo);
  const pct = Number(margen);
  if (!(base > 0) || !Number.isFinite(pct) || pct >= 100) return null;
  return Math.round(base / (1 - pct / 100));
}

function textoPorcentaje(valor) {
  if (valor == null || !Number.isFinite(Number(valor))) return "";
  const redondo = Math.round(Number(valor) * 10) / 10;
  return Number.isInteger(redondo) ? String(redondo) : redondo.toFixed(1);
}

function miles(valor) {
  return Math.abs(Math.round(Number(valor) || 0)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function textoDivisor(margen) {
  const divisor = 1 - Number(margen) / 100;
  if (!(divisor > 0)) return "";
  const texto = (Math.round(divisor * 1000) / 1000).toFixed(3).replace(".", ",");
  return texto.endsWith("0") ? texto.slice(0, -1) : texto;
}

function formulaProducto(costo, precio, margen, modo) {
  const base = Number(costo);
  const venta = Number(precio);
  if (!(base > 0) || !(venta > 0)) return "";
  if (modo === "margen" && margen !== "" && Number(margen) < 100) {
    const divisor = textoDivisor(margen);
    if (!divisor) return "";
    return `${miles(base)} ÷ ${divisor} = ${plata(venta)}`;
  }
  const calculado = margenUtilidad(base, venta);
  if (calculado == null) return "";
  return `1 − (${miles(base)} ÷ ${miles(venta)}) = ${textoPorcentaje(calculado).replace(".", ",")}%`;
}

function toast(texto) {
  const caja = document.getElementById("toast");
  caja.hidden = false;
  caja.textContent = texto;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { caja.hidden = true; }, 2800);
}

function detalleError(data) {
  if (!data) return "No se pudo completar";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg || "").join(", ");
  return "No se pudo completar";
}

async function api(ruta, opciones = {}) {
  const res = await fetch("/api/lavadero" + ruta, {
    method: opciones.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(S.token ? { Authorization: "Bearer " + S.token } : {}),
    },
    body: opciones.body ? JSON.stringify(opciones.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    salir(false);
    draw();
    throw new Error(detalleError(data));
  }
  if (!res.ok) throw new Error(detalleError(data));
  return data;
}

function salir(aviso = true) {
  S.token = "";
  S.sesion = null;
  S.catalogo = null;
  localStorage.removeItem("lv_token");
  localStorage.removeItem("lv_sesion");
  if (aviso) toast("Sesión cerrada");
}

function esDueno() {
  return S.sesion && S.sesion.rol === "admin";
}

function etiquetaRol(rol) {
  if (rol === "admin") return "Administrador";
  if (rol === "vendedor" || rol === "cajero") return "Vendedor";
  return rol || "";
}

function vistasDeSesion() {
  const items = [
    ["lavar", "🚿", "Lavar"],
    ["tablero", "📋", "Tablero"],
  ];
  if (esDueno()) items.push(["plata", "💰", "Plata"], ["gastos", "🧾", "Gastos"], ["reportes", "📊", "Reportes"], ["ajustes", "⚙️", "Ajustes"]);
  return items;
}

function opcionesRevision() {
  if (S.catalogo && S.catalogo.revision && S.catalogo.revision.length) return S.catalogo.revision;
  return ["Rayones", "Golpes", "Vidrios", "Espejos", "Antena", "Tapetes", "Objetos dentro", "Llantas"];
}

function activos(lista) {
  return (lista || []).filter((x) => Number(x.activo) === 1);
}

function sucursales() {
  const todas = activos(S.catalogo.sucursales);
  if (S.sesion.branch_id) return todas.filter((s) => s.id === S.sesion.branch_id);
  return todas;
}

function zonasBranch() {
  return activos(S.catalogo.zonas).filter((z) => z.branch_id === S.branchId);
}

function tiposZona() {
  return activos(S.catalogo.tipos).filter((t) => t.zona_id === S.zonaId);
}

function precioDe(servicio, tipoId) {
  const mapa = servicio.precios || {};
  const valor = mapa[tipoId] ?? mapa[String(tipoId)];
  return valor == null ? null : Number(valor);
}

function nuevoDraft() {
  return { tipoId: 0, servicios: [], productos: {}, empleados: [], placa: "", tel: "", nombre: "", checklist: [], nota: "" };
}

function leerExtras() {
  if (!S.draft) return;
  const placa = document.getElementById("placa");
  const tel = document.getElementById("tel");
  const nombre = document.getElementById("cliente");
  if (placa) S.draft.placa = normalizarPlaca(placa.value);
  if (tel) S.draft.tel = soloDigitos(tel.value);
  if (nombre) S.draft.nombre = normalizarNombreCliente(nombre.value).trim();
  const nota = document.getElementById("nota");
  if (nota) S.draft.nota = String(nota.value || "").slice(0, 240);
  if (!Array.isArray(S.draft.checklist)) S.draft.checklist = [];
}

function totalDraft() {
  if (!S.draft) return 0;
  let total = 0;
  if (!S.soloProductos) {
    for (const id of S.draft.servicios) {
      const servicio = S.catalogo.servicios.find((s) => s.id === id);
      if (servicio) total += precioDe(servicio, S.draft.tipoId) || 0;
    }
  }
  for (const [id, cant] of Object.entries(S.draft.productos)) {
    const producto = S.catalogo.productos.find((p) => p.id === Number(id));
    if (producto && cant > 0) total += Number(producto.precio) * cant;
  }
  return total;
}

function elegirInicial() {
  const lista = sucursales();
  if (!lista.some((s) => s.id === S.branchId)) S.branchId = lista[0] ? lista[0].id : 0;
  const zonas = zonasBranch();
  if (!zonas.some((z) => z.id === S.zonaId)) S.zonaId = zonas[0] ? zonas[0].id : 0;
  localStorage.setItem("lv_branch", String(S.branchId));
  localStorage.setItem("lv_zona", String(S.zonaId));
  if (!S.draft) S.draft = nuevoDraft();
}

async function cargarBase() {
  S.catalogo = await api("/catalogo");
  elegirInicial();
}

function draw() {
  const app = document.getElementById("app");
  if (S.recupero) {
    app.innerHTML = htmlRecupero();
    document.getElementById("form-recupero").onsubmit = enviarRecupero;
    return;
  }
  if (!S.sesion) {
    app.innerHTML = S.olvide ? htmlOlvide() : htmlLogin();
    const login = document.getElementById("form-login");
    if (login) login.onsubmit = enviarLogin;
    const olvide = document.getElementById("form-olvide");
    if (olvide) olvide.onsubmit = enviarOlvide;
    const volver = document.getElementById("volver-login");
    if (volver) volver.onclick = () => { S.olvide = false; draw(); };
    const pedir = document.getElementById("pedir-olvide");
    if (pedir) pedir.onclick = () => { S.olvide = true; draw(); };
    return;
  }
  if (!vistasDeSesion().some(([id]) => id === S.vista)) S.vista = "lavar";
  app.innerHTML = htmlShell();
  document.querySelectorAll("[data-vista]").forEach((b) => {
    b.onclick = () => ir(b.dataset.vista);
  });
  document.getElementById("salir").onclick = () => { salir(); draw(); };
  document.querySelectorAll("[data-branch]").forEach((b) => {
    b.onclick = () => {
      S.branchId = Number(b.dataset.branch);
      localStorage.setItem("lv_branch", String(S.branchId));
      const zonas = zonasBranch();
      S.zonaId = zonas[0] ? zonas[0].id : 0;
      S.draft = nuevoDraft();
      ir(S.vista);
    };
  });
  bindVista();
  if (S.modal) bindModal();
}

function ir(vista, opciones) {
  if (!opciones || opciones.leer !== false) leerExtras();
  if (!vistasDeSesion().some(([id]) => id === vista)) vista = "lavar";
  if (vista !== "reportes" && !sucursales().some((s) => s.id === S.branchId)) {
    const primera = sucursales()[0];
    S.branchId = primera ? primera.id : 0;
    const zonas = zonasBranch();
    S.zonaId = zonas[0] ? zonas[0].id : 0;
  }
  S.vista = vista;
  S.modal = null;
  draw();
  if (vista === "tablero") cargarTablero();
  if (vista === "plata") cargarPlata();
  if (vista === "gastos") cargarGastos();
  if (vista === "reportes") cargarReporte();
}

function htmlLogin() {
  return `
    <div class="login">
      <form class="login-card" id="form-login">
        <div class="marca">
          <div class="marca-coche">🚗</div>
          <h1>CAR WASH</h1>
          <div class="detalle">DETAILING</div>
          <p>S.O.P. soluciones operativas<br>310 325 7331</p>
        </div>
        <label>Usuario</label>
        <input name="usuario" autocomplete="username" required>
        <label>Clave</label>
        <input name="clave" type="password" autocomplete="current-password" required>
        <div style="height:16px"></div>
        <button class="btn btn-green" type="submit">Entrar</button>
        <button class="enlace" id="pedir-olvide" type="button">Olvidé mi clave</button>
      </form>
    </div>`;
}

function htmlOlvide() {
  return `
    <div class="login">
      <form class="login-card" id="form-olvide">
        <div class="marca">
          <div class="marca-coche">🚗</div>
          <h1>CAR WASH</h1>
          <div class="detalle">DETAILING</div>
        </div>
        <h2>Olvidé mi clave</h2>
        <p class="ayuda">Escribe el usuario o el correo. Llega un mensaje para cambiar la clave.</p>
        <label>Usuario o correo</label>
        <input name="dato" autocomplete="off" required>
        <div style="height:16px"></div>
        <button class="btn btn-green" type="submit">Enviar mensaje</button>
        <button class="enlace" id="volver-login" type="button">Volver</button>
      </form>
    </div>`;
}

function htmlRecupero() {
  return `
    <div class="login">
      <form class="login-card" id="form-recupero">
        <div class="marca">
          <div class="marca-coche">🚗</div>
          <h1>CAR WASH</h1>
          <div class="detalle">DETAILING</div>
        </div>
        <h2>Clave nueva</h2>
        <p class="ayuda">El mensaje del correo te trajo aquí. Escribe la clave dos veces.</p>
        <label>Clave nueva</label>
        <input name="nueva" type="password" autocomplete="new-password" required>
        <label>Repite la clave</label>
        <input name="repite" type="password" autocomplete="new-password" required>
        <div style="height:16px"></div>
        <button class="btn btn-green" type="submit">Guardar clave</button>
      </form>
    </div>`;
}

async function enviarOlvide(ev) {
  ev.preventDefault();
  const datos = new FormData(ev.target);
  try {
    const data = await fetch("/api/lavadero/olvide", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dato: datos.get("dato") }),
    }).then(async (res) => {
      const cuerpo = await res.json();
      if (!res.ok) throw new Error(detalleError(cuerpo));
      return cuerpo;
    });
    toast(data.mensaje || "Si ese usuario tiene correo, le llega el mensaje.");
    S.olvide = false;
    draw();
  } catch (error) {
    toast(error.message);
  }
}

async function enviarRecupero(ev) {
  ev.preventDefault();
  const datos = new FormData(ev.target);
  try {
    const res = await fetch("/api/lavadero/recuperar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: S.recupero, nueva: datos.get("nueva"), repite: datos.get("repite") }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data));
    S.recupero = "";
    history.replaceState({}, "", "/lavadero");
    toast("Clave actualizada. Entra con la nueva.");
    draw();
  } catch (error) {
    toast(error.message);
  }
}

async function enviarLogin(ev) {
  ev.preventDefault();
  const datos = new FormData(ev.target);
  try {
    const res = await fetch("/api/lavadero/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario: datos.get("usuario"), clave: datos.get("clave") }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(detalleError(data));
    S.token = data.token;
    S.sesion = data;
    localStorage.setItem("lv_token", data.token);
    localStorage.setItem("lv_sesion", JSON.stringify(data));
    await cargarBase();
    draw();
    toast("Listo, " + data.nombre);
  } catch (error) {
    toast(error.message);
  }
}

function htmlShell() {
  const negocio = S.catalogo.negocio;
  const items = vistasDeSesion();
  const listos = S.ordenes.filter((o) => o.estado === "LISTO").length;
  return `
    <div class="shell">
      <header class="top">
        <div class="marca-top">
          ${logoMarca()}
          <div>
            <div class="sub">DETAILING</div>
            <h1>${esc(negocio.nombre)}</h1>
          </div>
        </div>
        <div class="quien">
          <div>${esc(S.sesion.nombre)}</div>
          <div class="sub">${esc(etiquetaRol(S.sesion.rol))}</div>
          <button class="link" id="salir" type="button">Salir</button>
        </div>
      </header>
      <div class="pills">
        ${esDueno() && S.vista === "reportes" ? `<button class="pill ${S.branchId === 0 ? "on" : ""}" data-branch="0" type="button">Todas</button>` : ""}
        ${sucursales().map((s) => `<button class="pill ${s.id === S.branchId ? "on" : ""}" data-branch="${s.id}" type="button">${esc(s.nombre)}</button>`).join("")}
      </div>
      <main class="contenido">${htmlVista()}</main>
      <nav class="nav">
        ${items.map(([id, ico, nombre]) => `<button type="button" data-vista="${id}" class="${S.vista === id ? "on" : ""}"><span class="ico">${ico}</span>${nombre}${id === "tablero" && listos ? " (" + listos + ")" : ""}</button>`).join("")}
      </nav>
      ${S.modal ? htmlModal() : ""}
    </div>`;
}

function htmlVista() {
  if (S.vista === "lavar") return htmlLavar();
  if (S.vista === "tablero") return htmlTablero();
  if (S.vista === "plata") return htmlPlata();
  if (S.vista === "gastos") return htmlGastos();
  if (S.vista === "reportes") return htmlReportes();
  if (S.vista === "ajustes") return htmlAjustes();
  return "";
}

function htmlLavar() {
  const zonas = zonasBranch();
  if (!zonas.length && !S.soloProductos) {
    return `<div class="vacio"><h2>Esta sucursal todavía no tiene zonas</h2><p>El administrador las crea en Ajustes y, si quiere, copia la carta de la Sucursal Principal.</p></div>`;
  }
  const tipos = tiposZona();
  const grupos = ["Basico", "Especial", "Premium"];
  const servicios = activos(S.catalogo.servicios).filter((s) => s.zona_id === S.zonaId && precioDe(s, S.draft.tipoId) != null);
  const empleados = activos(S.catalogo.empleados);
  const productos = activos(S.catalogo.productos);
  return `
    <div class="pills" style="padding-left:0">
      <button class="pill ${S.soloProductos ? "" : "on"}" id="modo-servicio" type="button">Servicio</button>
      <button class="pill ${S.soloProductos ? "on" : ""}" id="modo-producto" type="button">Solo productos</button>
      ${S.soloProductos ? "" : zonas.map((z) => `<button class="pill ${z.id === S.zonaId ? "on" : ""}" data-zona="${z.id}" type="button">${esc(z.nombre)}</button>`).join("")}
    </div>
    ${S.soloProductos ? "" : `
      <div class="seccion">1. Vehículo</div>
      <div class="grid grid-3">
        ${tipos.map((t) => `<button class="vehiculo ${S.draft.tipoId === t.id ? "on" : ""}" data-tipo="${t.id}" type="button"><span class="ico">${esc(t.icono)}</span><strong>${esc(t.nombre)}</strong></button>`).join("") || `<div class="vacio">Agrega tipos de vehículo en Ajustes.</div>`}
      </div>
      <div class="seccion">2. Servicio</div>
      ${S.draft.tipoId ? grupos.map((grupo) => {
        const lista = servicios.filter((s) => s.grupo === grupo);
        if (!lista.length) return "";
        return `<div class="seccion">${esc(grupo)}</div><div class="grid grid-serv">${lista.map((s) => `
          <button class="svc ${S.draft.servicios.includes(s.id) ? "on" : ""}" data-servicio="${s.id}" type="button">
            <span class="ico">${esc(s.icono || "🚿")}</span>
            <strong>${esc(s.nombre)}</strong>
            ${s.duracion ? `<div>${esc(s.duracion)}</div>` : ""}
            <div class="precio">${plata(precioDe(s, S.draft.tipoId))}</div>
          </button>`).join("")}</div>`;
      }).join("") : `<div class="vacio">Toca el vehículo para ver los precios.</div>`}
      <div class="seccion">3. Quién lava</div>
      <div class="chips">
        ${empleados.map((e) => `<button class="chip ${S.draft.empleados.includes(e.id) ? "on" : ""}" data-empleado="${e.id}" type="button">👷 ${esc(nombreEmpleado(e))}</button>`).join("") || `<span class="ayuda">Aún no hay muchachos. El administrador los agrega en Ajustes.</span>`}
      </div>
    `}
    <div class="seccion">${S.soloProductos ? "Productos" : "Sumar productos"}</div>
    <div class="lista">
      ${productos.map((p) => {
        const cant = S.draft.productos[p.id] || 0;
        return `<div class="producto"><div><strong>${esc(p.nombre)}</strong><div>${plata(p.precio)}</div></div>
          <div class="mas"><button type="button" data-menos="${p.id}">−</button><strong>${cant}</strong><button type="button" data-mas="${p.id}">+</button></div></div>`;
      }).join("") || `<div class="vacio">No hay productos de mostrador.</div>`}
    </div>
    ${S.soloProductos ? "" : `
      <div class="grid grid-3" style="margin-top:12px">
        <div><label>Placa</label><input id="placa" class="placa-input" name="lv-placa" autocomplete="off" value="${esc(S.draft.placa)}" placeholder="ABC123" maxlength="8" required></div>
        <div><label>WhatsApp del cliente</label><input id="tel" name="lv-whatsapp" autocomplete="off" value="${esc(S.draft.tel)}" placeholder="3000000000" inputmode="numeric" maxlength="10" required></div>
        <div><label>Nombre del cliente</label><input id="cliente" class="mayus" name="lv-cliente" autocomplete="off" value="${esc(S.draft.nombre)}" placeholder="NOMBRE Y APELLIDO" maxlength="80" required></div>
      </div>
      <div class="seccion">4. Revisión al recibir</div>
      <p class="ayuda">Marca lo que notes en el vehículo. Si no hay nada, déjalo en blanco.</p>
      <div class="chips">
        ${opcionesRevision().map((item) => `<button class="chip ${(S.draft.checklist || []).includes(item) ? "on" : ""}" data-revision="${esc(item)}" type="button">${esc(item)}</button>`).join("")}
      </div>
      <label>Nota (opcional)</label>
      <textarea id="nota" class="nota-corta" maxlength="240" placeholder="Si el vehículo tiene alguna particularidad">${esc(S.draft.nota)}</textarea>
    `}
    <div class="barra-fija">
      <div class="total-grande"><small>Total</small>${plata(totalDraft())}</div>
      <button class="btn btn-green" id="registrar" type="button" ${puedeRegistrar() ? "" : "disabled"}>${S.soloProductos ? "Cobrar productos" : "Registrar y Lavar"}</button>
    </div>`;
}

function bindLavar() {
  const modoS = document.getElementById("modo-servicio");
  const modoP = document.getElementById("modo-producto");
  if (modoS) modoS.onclick = () => { leerExtras(); S.soloProductos = false; draw(); };
  if (modoP) modoP.onclick = () => { leerExtras(); S.soloProductos = true; draw(); };
  document.querySelectorAll("[data-zona]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      S.zonaId = Number(b.dataset.zona);
      localStorage.setItem("lv_zona", String(S.zonaId));
      S.draft.tipoId = 0;
      S.draft.servicios = [];
      draw();
    };
  });
  document.querySelectorAll("[data-tipo]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      S.draft.tipoId = Number(b.dataset.tipo);
      S.draft.servicios = [];
      draw();
    };
  });
  document.querySelectorAll("[data-servicio]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      const id = Number(b.dataset.servicio);
      if (S.draft.servicios.includes(id)) S.draft.servicios = S.draft.servicios.filter((x) => x !== id);
      else S.draft.servicios.push(id);
      draw();
    };
  });
  document.querySelectorAll("[data-empleado]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      const id = Number(b.dataset.empleado);
      if (S.draft.empleados.includes(id)) S.draft.empleados = S.draft.empleados.filter((x) => x !== id);
      else S.draft.empleados.push(id);
      draw();
    };
  });
  document.querySelectorAll("[data-revision]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      const item = b.dataset.revision;
      if (S.draft.checklist.includes(item)) S.draft.checklist = S.draft.checklist.filter((x) => x !== item);
      else S.draft.checklist.push(item);
      draw();
    };
  });
  document.querySelectorAll("[data-mas]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      const id = b.dataset.mas;
      S.draft.productos[id] = (S.draft.productos[id] || 0) + 1;
      draw();
    };
  });
  document.querySelectorAll("[data-menos]").forEach((b) => {
    b.onclick = () => {
      leerExtras();
      const id = b.dataset.menos;
      S.draft.productos[id] = Math.max(0, (S.draft.productos[id] || 0) - 1);
      draw();
    };
  });
  const placa = document.getElementById("placa");
  const tel = document.getElementById("tel");
  const nombre = document.getElementById("cliente");
  const refrescar = () => {
    if (placa) {
      const limpia = normalizarPlaca(placa.value);
      if (placa.value !== limpia) placa.value = limpia;
      S.draft.placa = limpia;
    }
    if (tel) {
      const digitos = soloDigitos(tel.value);
      if (tel.value !== digitos) tel.value = digitos;
      S.draft.tel = digitos;
    }
    if (nombre) {
      const limpio = normalizarNombreCliente(nombre.value);
      if (nombre.value !== limpio) nombre.value = limpio;
      S.draft.nombre = limpio;
    }
    const nota = document.getElementById("nota");
    if (nota) S.draft.nota = String(nota.value || "").slice(0, 240);
    const boton = document.getElementById("registrar");
    if (boton) boton.disabled = !puedeRegistrar();
  };
  if (placa) placa.addEventListener("input", refrescar);
  if (tel) tel.addEventListener("input", refrescar);
  if (nombre) nombre.addEventListener("input", refrescar);
  const nota = document.getElementById("nota");
  if (nota) nota.addEventListener("input", refrescar);
  const registrar = document.getElementById("registrar");
  if (registrar) registrar.onclick = registrarOrden;
}

async function registrarOrden() {
  leerExtras();
  const productos = Object.entries(S.draft.productos)
    .filter(([, cant]) => cant > 0)
    .map(([id, cantidad]) => ({ producto_id: Number(id), cantidad }));
  try {
    if (S.soloProductos) {
      await api("/venta-productos", {
        method: "POST",
        body: { branch_id: S.branchId, productos, pagos: [{ medio: "Efectivo", monto: totalDraft() }] },
      });
      toast("Productos cobrados");
    } else {
      S.draft.placa = normalizarPlaca(S.draft.placa);
      if (!puedeRegistrar()) {
        toast("Elige quién lava, y completa la placa, el nombre y el WhatsApp.");
        return;
      }
      await api("/ordenes", {
        method: "POST",
        body: {
          branch_id: S.branchId,
          zona_id: S.zonaId,
          tipo_id: S.draft.tipoId,
          servicios: S.draft.servicios,
          productos,
          colaboradores: S.draft.empleados.map((id) => ({ empleado_id: id, peso: 1 })),
          placa: S.draft.placa,
          cliente_telefono: S.draft.tel,
          cliente_nombre: S.draft.nombre,
          checklist: S.draft.checklist,
          nota: S.draft.nota,
        },
      });
      toast("Vehículo en proceso");
    }
    S.draft = nuevoDraft();
    ir("tablero", { leer: false });
  } catch (error) {
    toast(error.message);
  }
}

function htmlRevision(orden) {
  const marcas = Array.isArray(orden.checklist) ? orden.checklist : [];
  const nota = String(orden.nota || "").trim();
  if (!marcas.length && !nota) return "";
  return `${marcas.length ? `<div class="revision">${marcas.map((item) => `<span>${esc(item)}</span>`).join("")}</div>` : ""}${nota ? `<div class="nota-orden">📝 ${esc(nota)}</div>` : ""}`;
}

function htmlTablero() {
  const proceso = S.ordenes.filter((o) => o.estado === "EN_PROCESO");
  const listos = S.ordenes.filter((o) => o.estado === "LISTO");
  const columna = (titulo, lista, clase) => `
    <section class="columna">
      <h2>${titulo} (${lista.length})</h2>
      ${lista.map(htmlOrden).join("") || `<div class="vacio">Nada por aquí.</div>`}
    </section>`;
  return `<div class="kanban">${columna("🟡 En proceso", proceso, "proceso")}${columna("🟢 Listo para entregar", listos, "listo")}</div>`;
}

function htmlOrden(orden) {
  const clase = orden.estado === "LISTO" ? "listo" : "proceso";
  const servicios = (orden.items || []).map((i) => esc(i.descripcion)).join(" · ");
  const gente = (orden.colaboradores || []).map((c) => esc(c.empleado)).join(", ");
  return `
    <article class="orden ${clase}">
      <div class="placa">${esc(orden.icono || "")} ${esc(orden.placa)}</div>
      <div>${esc(orden.cliente_nombre || "")}</div>
      <div>${esc(orden.vehiculo)} · ${esc(orden.zona)}</div>
      <div>${servicios}</div>
      ${gente ? `<div>👷 ${gente}</div>` : ""}
      ${htmlRevision(orden)}
      <div class="precio">${plata(orden.total)}</div>
      <div class="acciones">
        <button class="btn btn-small" data-corregir="${orden.id}" type="button">Corregir</button>
        ${orden.estado === "EN_PROCESO"
          ? `<button class="btn btn-yellow btn-small" data-listo="${orden.id}" type="button">¡Listo!</button>`
          : `<button class="btn btn-wa btn-small" data-wa="${orden.id}" type="button">Avisar por WhatsApp</button>
             <button class="btn btn-green btn-small" data-cobrar="${orden.id}" type="button">Cobrar aquí</button>`}
        <button class="btn btn-danger btn-small" data-anular="${orden.id}" type="button">Anular</button>
      </div>
    </article>`;
}

async function cargarTablero(silencioso = false) {
  try {
    S.ordenes = await api("/ordenes?branch_id=" + S.branchId);
    if (S.vista === "tablero" && !S.modal) draw();
  } catch (error) {
    if (!silencioso) toast(error.message);
  }
}

function bindTablero() {
  document.querySelectorAll("[data-listo]").forEach((b) => {
    b.onclick = async () => {
      try {
        await api("/ordenes/" + b.dataset.listo + "/listo", { method: "POST" });
        toast("Listo para entregar. Avisa por WhatsApp o cobra aquí.");
        await cargarTablero();
      } catch (error) { toast(error.message); }
    };
  });
  document.querySelectorAll("[data-corregir]").forEach((b) => {
    b.onclick = () => {
      const orden = S.ordenes.find((o) => o.id === Number(b.dataset.corregir));
      if (!orden) return;
      S.modal = { tipo: "corregir", orden };
      draw();
    };
  });
  document.querySelectorAll("[data-cobrar]").forEach((b) => {
    b.onclick = () => {
      const orden = S.ordenes.find((o) => o.id === Number(b.dataset.cobrar));
      if (!orden || orden.estado !== "LISTO") {
        toast("Primero márcalo listo para entregar.");
        return;
      }
      S.modal = { tipo: "confirmar-cobro", orden };
      draw();
    };
  });
  document.querySelectorAll("[data-wa]").forEach((b) => {
    b.onclick = () => abrirWhatsapp(Number(b.dataset.wa));
  });
  document.querySelectorAll("[data-anular]").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("¿Anulas este vehículo?")) return;
      try {
        await api("/ordenes/" + b.dataset.anular + "/anular", { method: "POST" });
        await cargarTablero();
      } catch (error) { toast(error.message); }
    };
  });
}

async function abrirWhatsapp(ordenId) {
  try {
    let data = await api("/ordenes/" + ordenId + "/whatsapp");
    if (!data.url) {
      S.modal = { tipo: "telefono", ordenId, texto: data.texto };
      draw();
      return;
    }
    window.open(data.url, "_blank");
  } catch (error) {
    toast(error.message);
  }
}

function htmlBolsa(bolsa) {
  let sub = bolsa.tipo === "MUCHACHOS"
    ? `${bolsa.porcentaje}% reservado · toca y mira cuánto va para cada uno`
    : `${bolsa.porcentaje}% reservado · toca y mira ingresos y egresos`;
  if (Number(bolsa.gastado)) sub += `. Salió ${plata(bolsa.gastado)} · queda ${plata(bolsa.queda)}`;
  const cuerpo = `<span>${esc(bolsa.icono || "")} ${esc(bolsa.nombre)}</span><strong>${plata(bolsa.monto)}</strong><small>${esc(sub)}</small>`;
  const clase = bolsa.tipo === "MUCHACHOS" ? "naranja" : bolsa.tipo === "UTILIDAD" ? "verde" : "";
  return `<button class="bolsa ${clase}" data-bolsa="${bolsa.id || ""}" type="button" style="background:${esc(bolsa.color || "#3b82f6")}">${cuerpo}</button>`;
}

function htmlPlata() {
  if (!S.resumen) return `<div class="vacio">Cargando la caja de hoy…</div>`;
  const r = S.resumen;
  const bolsas = r.bolsillos && r.bolsillos.length ? r.bolsillos : [
    { nombre: "Para los muchachos", porcentaje: 30, tipo: "MUCHACHOS", icono: "👷", color: "#f97316", monto: r.comisiones },
    { nombre: "Gastos operativos", porcentaje: 35, tipo: "GASTO", icono: "💡", color: "#3b82f6", monto: r.gastos },
    { nombre: "Utilidad neta", porcentaje: 25, tipo: "UTILIDAD", icono: "💰", color: "#1e9b45", monto: r.ganancia },
  ];
  const base = Math.max(r.producido, 1);
  return `
    <h2 style="margin-top:0">${esc(r.branch_nombre)}</h2>
    <div class="bolsillos">
      ${bolsas.map(htmlBolsa).join("")}
    </div>
    <div class="reparto">${bolsas.map((b) => `<i style="width:${(Math.max(b.monto, 0) / base) * 100}%;background:${esc(b.color || "#1e9b45")}"></i>`).join("")}</div>
    <p>Entró ${plata(r.producido)} · ${r.vehiculos} ${r.vehiculos === 1 ? "vehículo" : "vehículos"} · Carros ${plata(r.carros)} · Motos ${plata(r.motos)} · Productos ${plata(r.productos)}</p>
    <div class="frase">${esc(r.texto)}</div>
    <div class="fila-botones">
      <button class="btn btn-green" id="cerrar-dia" type="button" style="min-width:220px">${r.cerrado ? "Día cerrado" : "Cerrar Día"}</button>
      <button class="btn" id="imprimir-dia" type="button">Imprimir</button>
      ${esDueno() && r.cerrado ? `<button class="btn btn-ghost" id="reabrir" type="button">Reabrir día</button>` : ""}
      ${esDueno() ? `<button class="btn btn-ghost" id="ir-gastos" type="button">Registrar gasto</button>` : ""}
      ${esDueno() ? `<button class="btn btn-ghost" id="ir-bolsillos" type="button">Configurar porcentajes</button>` : ""}
    </div>
    <div class="seccion">Hoy entraron</div>
    <div class="lista">${(r.ultimas || []).map((u) => `<div><span>${esc(u.icono)} ${esc(u.placa || u.vehiculo)} · ${esc(u.hora)}</span><strong>${plata(u.total)}</strong></div>`).join("") || `<div class="vacio">Todavía no entra plata hoy.</div>`}</div>`;
}

async function cargarPlata() {
  try {
    S.resumen = await api("/resumen-dia?branch_id=" + S.branchId);
    if (S.vista === "plata" && !S.modal) draw();
  } catch (error) {
    toast(error.message);
  }
}

function bindPlata() {
  document.querySelectorAll("[data-bolsa]").forEach((boton) => {
    boton.onclick = () => {
      const bolsa = (S.resumen.bolsillos || []).find((b) => String(b.id) === boton.dataset.bolsa);
      if (!bolsa) return;
      if (bolsa.tipo === "MUCHACHOS") S.modal = { tipo: "muchachos", resumen: S.resumen };
      else S.modal = { tipo: "bolsillo", bolsa, resumen: S.resumen };
      draw();
    };
  });
  const cerrar = document.getElementById("cerrar-dia");
  if (cerrar) cerrar.onclick = () => cerrarDia(false);
  const imprimir = document.getElementById("imprimir-dia");
  if (imprimir) imprimir.onclick = () => imprimirRecibo(S.resumen);
  const irBolsillos = document.getElementById("ir-bolsillos");
  if (irBolsillos) irBolsillos.onclick = () => {
    S.ajuste = "bolsillos";
    S.bolsillosDraft = null;
    ir("ajustes");
  };
  const irGastos = document.getElementById("ir-gastos");
  if (irGastos) irGastos.onclick = () => ir("gastos");
  const reabrir = document.getElementById("reabrir");
  if (reabrir) reabrir.onclick = async () => {
    try {
      S.resumen = await api("/reabrir-dia", { method: "POST", body: { branch_id: S.branchId } });
      draw();
    } catch (error) { toast(error.message); }
  };
}

function fechaHoy() {
  const ahora = new Date();
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const dia = String(ahora.getDate()).padStart(2, "0");
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

function htmlGastos() {
  if (!S.gastos) return `<div class="vacio">Cargando los gastos…</div>`;
  const datos = S.gastos;
  const edit = S.gastoEdit || {};
  const inventario = S.gastoApartado === "inventario";
  const bolsas = (S.catalogo.bolsillos || []).filter((b) => b.tipo !== "MUCHACHOS");
  const periodos = [["hoy", "Hoy"], ["semana", "Semana"], ["mes", "Mes"], ["todo", "Todo"]];
  const filas = (datos.gastos || []).filter((g) => inventario ? (g.productos || []).length : !(g.productos || []).length);
  const total = filas.reduce((suma, g) => suma + Number(g.monto || 0), 0);
  const unidades = filas.reduce((suma, g) => suma + (g.productos || []).reduce((n, p) => n + Number(p.cantidad || 0), 0), 0);
  const porBolsa = {};
  filas.forEach((g) => {
    const cubo = porBolsa[g.bolsillo_id] || { nombre: g.bolsillo_nombre, monto: 0 };
    cubo.monto += Number(g.monto || 0);
    porBolsa[g.bolsillo_id] = cubo;
  });
  const cantidades = {};
  const precios = {};
  (edit.productos || []).forEach((p) => {
    cantidades[p.producto_id] = p.cantidad;
    precios[p.producto_id] = p.precio;
  });
  const productos = productosIngreso();
  return `
    <h2 style="margin-top:0">Gastos</h2>
    <div class="pills" style="padding-left:0">
      <button class="pill ${inventario ? "" : "on"}" data-apartado="pagos" type="button">Pagos y compras</button>
      <button class="pill ${inventario ? "on" : ""}" data-apartado="inventario" type="button">Ingreso de inventario</button>
    </div>
    <p class="ayuda">${inventario
      ? "Escribe cuántos entran y el precio de cada uno. El total es el gasto y sale del bolsillo que elijas. El de los muchachos no se toca."
      : "Registra pagos y compras que no son de los productos que vendes. El bolsillo de los muchachos no se toca."}</p>
    <form id="form-gasto" class="tarjeta-form">
      ${inventario ? "" : `<label>Es un</label>
      <select name="clase">
        <option value="PAGO" ${edit.clase !== "COMPRA" ? "selected" : ""}>Pago</option>
        <option value="COMPRA" ${edit.clase === "COMPRA" ? "selected" : ""}>Compra</option>
      </select>
      <label>Qué se pagó o se compró</label>
      <input name="concepto" required maxlength="80" value="${esc(edit.concepto || "")}" placeholder="Arriendo, servicios, seguridad social">`}
      ${inventario ? `<div class="seccion">Productos que entran</div>
      ${productos.map((p) => {
        const precio = precios[p.id] != null ? precios[p.id] : (Number(p.costo) || "");
        return `<div class="producto ingreso-linea" data-producto="${p.id}" data-nombre="${esc(p.nombre)}">
        <div><strong>${esc(p.nombre)}</strong><div class="gasto-meta">Hay ${Number(p.stock) || 0}</div></div>
        <div class="ingreso-nums">
          <span><em>Cantidad</em><input data-cant type="number" min="0" value="${cantidades[p.id] || 0}"></span>
          <span><em>Precio</em><input data-precio type="number" min="0" value="${precio}"></span>
          <strong data-sub></strong>
        </div>
      </div>`;
      }).join("") || `<div class="vacio">Todavía no hay productos de mostrador.</div>`}
      <p class="total-compra"><span>Total de la compra</span><strong id="total-ingreso">$0</strong></p>` : `<label>Valor</label>
      <input name="monto" type="number" min="1" required value="${edit.monto || ""}" placeholder="0">`}
      <label>Fecha</label>
      <input name="fecha" type="date" required value="${esc(edit.fecha || fechaHoy())}">
      <label>Sale del bolsillo</label>
      <select name="bolsillo_id" required>
        <option value="">Elige el bolsillo</option>
        ${bolsas.map((b) => `<option value="${b.id}" ${Number(edit.bolsillo_id) === b.id ? "selected" : ""}>${esc(b.nombre)}</option>`).join("")}
      </select>
      <label>Nota (opcional)</label>
      <input name="nota" maxlength="160" value="${esc(edit.nota || "")}" placeholder="Factura, proveedor o detalle">
      <div style="height:12px"></div>
      <button class="btn btn-green" type="submit">${edit.id ? "Guardar cambio" : "Registrar"}</button>
      ${edit.id ? `<button class="btn btn-ghost" id="cancelar-gasto" type="button">Cancelar</button>` : ""}
    </form>
    <div class="pills" style="padding-left:0">
      ${periodos.map(([id, nombre]) => `<button class="pill ${S.gastosPeriodo === id ? "on" : ""}" data-periodo="${id}" type="button">${nombre}</button>`).join("")}
    </div>
    <div class="kpis" style="margin-top:12px">
      <div class="kpi"><span>Salieron</span><strong>${plata(total)}</strong></div>
      <div class="kpi"><span>${inventario ? "Unidades" : "Registros"}</span><strong>${inventario ? unidades : filas.length}</strong></div>
    </div>
    ${Object.values(porBolsa).map((b) => `<div class="lista" style="margin-top:8px"><div><span>${esc(b.nombre)}</span><strong>${plata(b.monto)}</strong></div></div>`).join("")}
    <div class="seccion">${inventario ? "Ingresos de inventario" : "Pagos y compras"}</div>
    <div class="lista">
      ${filas.map((g) => `<div>
        <span>${inventario ? esc(textoIngreso(g)) : `${g.clase === "COMPRA" ? "Compra" : "Pago"} · ${esc(g.concepto)}`}<small class="gasto-meta">${esc(g.bolsillo_nombre)} · ${esc(fechaLarga(g.fecha))}${g.nota ? " · " + esc(g.nota) : ""}</small></span>
        <span>
          <strong>${plata(g.monto)}</strong>
          <button class="btn btn-small" data-gasto="${g.id}" type="button">Cambiar</button>
          <button class="btn btn-danger btn-small" data-quitar-gasto="${g.id}" type="button">Quitar</button>
        </span>
      </div>`).join("") || `<div class="vacio">${inventario ? "Todavía no entra inventario en este periodo." : "Todavía no hay pagos ni compras en este periodo."}</div>`}
    </div>`;
}

function productosIngreso() {
  const mapa = new Map();
  activos(S.catalogo.productos).forEach((p) => mapa.set(p.id, p));
  ((S.gastoEdit && S.gastoEdit.productos) || []).forEach((linea) => {
    if (!mapa.has(linea.producto_id)) {
      mapa.set(linea.producto_id, { id: linea.producto_id, nombre: linea.nombre, stock: 0, activo: 1 });
    }
  });
  return [...mapa.values()];
}

function textoIngreso(gasto) {
  const lineas = gasto.productos || [];
  if (!lineas.length) return gasto.concepto;
  return lineas.map((p) => `${p.nombre} x${p.cantidad}${p.precio ? " · " + plata(p.precio) : ""}`).join(", ");
}

async function cargarGastos() {
  if (!esDueno()) return;
  try {
    S.gastos = await api("/gastos?branch_id=" + S.branchId + "&preset=" + encodeURIComponent(S.gastosPeriodo));
    if (S.vista === "gastos" && !S.modal) draw();
  } catch (error) {
    toast(error.message);
  }
}

function bindGastos() {
  document.querySelectorAll("[data-apartado]").forEach((b) => {
    b.onclick = () => {
      S.gastoApartado = b.dataset.apartado;
      S.gastoEdit = null;
      draw();
    };
  });
  document.querySelectorAll("[data-periodo]").forEach((b) => {
    b.onclick = () => {
      S.gastosPeriodo = b.dataset.periodo;
      cargarGastos();
    };
  });
  const form = document.getElementById("form-gasto");
  if (form) form.onsubmit = guardarGasto;
  document.querySelectorAll("[data-cant], [data-precio]").forEach((input) => {
    input.addEventListener("input", pintarTotalIngreso);
  });
  pintarTotalIngreso();
  const cancelar = document.getElementById("cancelar-gasto");
  if (cancelar) cancelar.onclick = () => { S.gastoEdit = null; draw(); };
  document.querySelectorAll("[data-gasto]").forEach((b) => {
    b.onclick = () => {
      S.gastoEdit = (S.gastos.gastos || []).find((g) => g.id === Number(b.dataset.gasto)) || null;
      draw();
      window.scrollTo(0, 0);
    };
  });
  document.querySelectorAll("[data-quitar-gasto]").forEach((b) => {
    b.onclick = () => quitarGasto(Number(b.dataset.quitarGasto));
  });
}

function pintarTotalIngreso() {
  let total = 0;
  document.querySelectorAll("[data-producto]").forEach((fila) => {
    const cantidad = Number(fila.querySelector("[data-cant]").value) || 0;
    const precio = Number(fila.querySelector("[data-precio]").value) || 0;
    const subtotal = cantidad * precio;
    total += subtotal;
    const caja = fila.querySelector("[data-sub]");
    if (caja) caja.textContent = subtotal ? plata(subtotal) : "";
  });
  const aviso = document.getElementById("total-ingreso");
  if (aviso) aviso.textContent = plata(total);
}

async function guardarGasto(ev) {
  ev.preventDefault();
  const datos = Object.fromEntries(new FormData(ev.target).entries());
  const cuerpo = {
    branch_id: S.branchId,
    clase: datos.clase,
    concepto: datos.concepto,
    monto: Number(datos.monto),
    fecha: datos.fecha,
    bolsillo_id: Number(datos.bolsillo_id),
    nota: datos.nota,
  };
  if (!cuerpo.bolsillo_id) {
    toast("Elige el bolsillo de donde sale este gasto.");
    return;
  }
  if (S.gastoApartado === "inventario") {
    cuerpo.clase = "COMPRA";
    cuerpo.productos = [...document.querySelectorAll("[data-producto]")].map((fila) => ({
      producto_id: Number(fila.dataset.producto),
      nombre: fila.dataset.nombre,
      cantidad: Number(fila.querySelector("[data-cant]").value) || 0,
      precio: Number(fila.querySelector("[data-precio]").value) || 0,
    })).filter((p) => p.cantidad > 0);
    if (!cuerpo.productos.length) {
      toast("Escribe cuántos entran de cada producto.");
      return;
    }
    if (cuerpo.productos.some((p) => p.precio <= 0)) {
      toast("Escribe el precio de cada producto que entra.");
      return;
    }
    cuerpo.monto = cuerpo.productos.reduce((suma, p) => suma + p.cantidad * p.precio, 0);
    cuerpo.concepto = cuerpo.productos.map((p) => `${p.nombre} x${p.cantidad}`).join(", ");
  }
  try {
    const id = S.gastoEdit && S.gastoEdit.id;
    await api(id ? "/gastos/" + id : "/gastos", { method: id ? "PATCH" : "POST", body: cuerpo });
    S.gastoEdit = null;
    toast(id ? "Registro actualizado" : "Registro guardado");
    await cargarBase();
    await cargarGastos();
  } catch (error) {
    toast(error.message);
  }
}

async function quitarGasto(id) {
  const fila = (S.gastos.gastos || []).find((g) => g.id === id);
  if (!fila || !confirm(fila.productos && fila.productos.length ? "¿Quitas este ingreso? La existencia baja otra vez." : "¿Quitas " + fila.concepto + "?")) return;
  try {
    await api("/gastos/" + id, { method: "DELETE" });
    if (S.gastoEdit && S.gastoEdit.id === id) S.gastoEdit = null;
    toast("Gasto quitado");
    await cargarBase();
    await cargarGastos();
  } catch (error) {
    toast(error.message);
  }
}

async function cerrarDia(confirmar) {
  try {
    const data = await api("/cerrar-dia", { method: "POST", body: { branch_id: S.branchId, confirmar } });
    S.resumen = data;
    if (data.requiere_confirmacion) {
      S.modal = { tipo: "confirmar-cierre", aviso: data.aviso };
      draw();
      return;
    }
    S.modal = { tipo: "cierre-listo", texto: data.texto, whatsapp: data.whatsapp || "" };
    draw();
  } catch (error) {
    toast(error.message);
  }
}

function htmlReportes() {
  if (!S.reporte) return `<div class="vacio">Armando el comparativo…</div>`;
  const r = S.reporte;
  const variacion = r.variacion_pct == null ? "Sin periodo anterior" : (r.variacion_pct >= 0 ? "▲ " : "▼ ") + Math.abs(r.variacion_pct) + "%";
  const max = Math.max(...r.serie_diaria.map((d) => d.total), 1);
  const maxMes = Math.max(...r.serie_mensual.map((d) => d.total), 1);
  const bloque = (titulo, filas, etiqueta, valor) => `
    <div class="seccion">${titulo}</div>
    <div class="lista">${filas.length ? filas.map((f) => `<div><span>${esc(f[etiqueta])}</span><strong>${typeof valor === "function" ? valor(f) : plata(f[valor])}</strong></div>`).join("") : `<div class="vacio">Sin movimientos.</div>`}</div>`;
  return `
    <div class="pills" style="padding-left:0">
      ${["hoy", "semana", "mes", "año"].map((p) => `<button class="pill ${S.preset === p ? "on" : ""}" data-preset="${p}" type="button">${p === "año" ? "Año" : p[0].toUpperCase() + p.slice(1)}</button>`).join("")}
      ${["mes_anterior", "mismo_mes_anio_pasado"].map((c) => `<button class="pill ${S.comparar === c ? "on" : ""}" data-comparar="${c}" type="button">${c === "mes_anterior" ? "Vs mes pasado" : "Vs año pasado"}</button>`).join("")}
    </div>
    <div class="frase">${esc(r.frase)}</div>
    <div class="kpis" style="margin-top:12px">
      <div class="kpi"><span>Entró</span><strong>${plata(r.producido)}</strong></div>
      <div class="kpi"><span>Vehículos</span><strong>${r.vehiculos}</strong></div>
      <div class="kpi"><span>Para ti</span><strong>${plata(r.ganancia)}</strong></div>
      <div class="kpi"><span>Comparado</span><strong class="${(r.variacion_pct || 0) >= 0 ? "sube" : "baja"}">${variacion}</strong></div>
    </div>
    <div class="seccion">Día a día</div>
    <div class="barras">${r.serie_diaria.map((d) => `<div class="bar-col" title="${esc(d.fecha)} ${plata(d.total)}"><div class="bar" style="height:${Math.max(4, (d.total / max) * 100)}%"></div><em>${d.fecha.slice(8)}</em></div>`).join("")}</div>
    <div class="seccion">Mes a mes</div>
    <div class="barras">${r.serie_mensual.map((d) => `<div class="bar-col" title="${esc(d.mes)} ${plata(d.total)}"><div class="bar" style="height:${Math.max(4, (d.total / maxMes) * 100)}%;background:#f5c400"></div><em>${d.mes.slice(5)}</em></div>`).join("")}</div>
    ${bloque("Por sucursal", r.por_sucursal, "sucursal", "total")}
    ${bloque("Por zona", r.por_zona, "zona", "total")}
    ${bloque("Servicios que más entran", r.por_servicio, "nombre", (f) => `${f.cantidad} · ${plata(f.total)}`)}
    ${bloque("Muchachos", r.por_colaborador, "nombre", (f) => `${f.ordenes} órdenes · ${plata(f.comision)}`)}
    ${bloque("Cómo te pagaron", r.por_medio, "medio", "total")}
    <p class="ayuda">Listos sin cobrar: ${r.listos_sin_cobrar}. Anuladas en el periodo: ${r.anuladas}. Ticket promedio ${plata(r.ticket_promedio)}.</p>`;
}

async function cargarReporte() {
  if (!esDueno()) return;
  try {
    const q = new URLSearchParams({
      branch_id: String(S.branchId || 0),
      preset: S.preset,
      comparar: S.comparar,
    });
    S.reporte = await api("/reportes?" + q.toString());
    if (S.vista === "reportes" && !S.modal) draw();
  } catch (error) {
    toast(error.message);
  }
}

function bindReportes() {
  document.querySelectorAll("[data-preset]").forEach((b) => {
    b.onclick = () => { S.preset = b.dataset.preset; cargarReporte(); };
  });
  document.querySelectorAll("[data-comparar]").forEach((b) => {
    b.onclick = () => { S.comparar = b.dataset.comparar; cargarReporte(); };
  });
}

const MENU = [
  ["negocio", "🏪", "Mi negocio", "Nombre, teléfono y mensaje"],
  ["sucursal", "📍", "Sucursales", "Locales"],
  ["zona", "🧩", "Zonas", "Carros, motos u otras"],
  ["tipo", "🚗", "Vehículos", "Moto, carro, camioneta"],
  ["servicio", "🚿", "Servicios y precios", "La carta de cada zona"],
  ["producto", "🛍️", "Productos", "Ceras y mostrador"],
  ["empleado", "👷", "Muchachos", "Quién lava"],
  ["regla", "%", "Comisiones", "Cuánto se llevan"],
  ["bolsillos", "💰", "Bolsillos", "Porcentajes del día, suman 100%"],
  ["medio", "💳", "Cómo te pagan", "Efectivo, Nequi…"],
  ["usuario", "🔑", "Quién entra", "Administrador y vendedor"],
  ["clave", "🔒", "Mi clave", "Cambiar la contraseña"],
];

function htmlAjustes() {
  if (!esDueno()) return `<div class="vacio">Solo el administrador cambia los ajustes.</div>`;
  if (S.ajuste === "menu") {
    return `<div class="menu-ajustes">${MENU.map(([id, ico, titulo, sub]) => `<button class="tarjeta" data-ajuste="${id}" type="button"><span class="ico">${ico}</span><strong>${titulo}</strong><div>${sub}</div></button>`).join("")}</div>`;
  }
  if (S.ajuste === "negocio" || S.ajuste === "clave") return `<button class="btn btn-ghost btn-small" id="volver-ajustes" type="button">Volver</button><p>Usa el formulario.</p>`;
  if (S.ajuste === "bolsillos") return htmlBolsillos();
  return htmlListaAjuste();
}

function htmlBolsillos() {
  if (!S.bolsillosDraft) {
    S.bolsillosDraft = (S.catalogo.bolsillos || []).map((b) => ({ ...b }));
  }
  const suma = S.bolsillosDraft.reduce((total, b) => total + (Number(b.porcentaje) || 0), 0);
  const nombres = S.bolsillosDraft.every((b) => String(b.nombre || "").trim().length >= 3);
  const cuadra = suma === 100 && nombres && S.bolsillosDraft.length > 0;
  const aviso = suma === 100 ? "Listo, suman 100%." : suma < 100 ? `Faltan ${100 - suma}%.` : `Sobran ${suma - 100}%.`;
  return `
    <button class="btn btn-ghost btn-small" id="volver-ajustes" type="button">Volver</button>
    <h2>Bolsillos</h2>
    <p class="ayuda">El de los muchachos sale del trabajo ya cobrado. Los demás, menos la utilidad, son ese porcentaje de lo que entró. La utilidad es lo que queda. Entre todos deben sumar 100%.</p>
    ${S.bolsillosDraft.map((b, i) => `
      <div class="bolsillo-fila" data-bolsillo="${i}">
        <input data-nombre value="${esc(b.nombre || "")}" maxlength="60" placeholder="Nombre del bolsillo" ${b.tipo === "MUCHACHOS" || b.tipo === "UTILIDAD" ? "" : ""}>
        <input data-pct type="number" min="0" max="100" step="1" value="${Number(b.porcentaje) || 0}">
        ${b.tipo === "GASTO" ? `<button class="btn btn-danger btn-small" data-quitar-bolsillo="${i}" type="button">Quitar</button>` : `<span class="ayuda">${b.tipo === "MUCHACHOS" ? "Trabajo" : "Lo que queda"}</span>`}
      </div>
      <p class="ayuda">${b.tipo === "MUCHACHOS" ? "Su porcentaje reserva la parte de los muchachos. El dinero es el de las comisiones." : b.tipo === "UTILIDAD" ? "Su porcentaje reserva la utilidad. El dinero es lo que queda al cerrar el día." : "Este porcentaje se aparta de lo que entró."}</p>
    `).join("")}
    <button class="btn btn-ghost" id="agregar-bolsillo" type="button">Agregar bolsillo</button>
    <p id="suma-bolsillos" class="${cuadra ? "suma-ok" : "suma-mal"}">Suman ${suma}%. ${aviso}</p>
    <button class="btn btn-green" id="guardar-bolsillos" type="button" ${cuadra ? "" : "disabled"}>Guardar</button>`;
}

function leerBolsillosForm() {
  if (!S.bolsillosDraft) return;
  document.querySelectorAll("[data-bolsillo]").forEach((fila) => {
    const i = Number(fila.dataset.bolsillo);
    const bolsa = S.bolsillosDraft[i];
    if (!bolsa) return;
    const nombre = fila.querySelector("[data-nombre]");
    const pct = fila.querySelector("[data-pct]");
    if (nombre) bolsa.nombre = nombre.value;
    if (pct) bolsa.porcentaje = Math.max(0, Math.min(100, Math.round(Number(pct.value) || 0)));
  });
}

function pintarSumaBolsillos() {
  leerBolsillosForm();
  const suma = S.bolsillosDraft.reduce((total, b) => total + (Number(b.porcentaje) || 0), 0);
  const nombres = S.bolsillosDraft.every((b) => String(b.nombre || "").trim().length >= 3);
  const cuadra = suma === 100 && nombres;
  const aviso = document.getElementById("suma-bolsillos");
  const guardar = document.getElementById("guardar-bolsillos");
  if (aviso) {
    aviso.className = cuadra ? "suma-ok" : "suma-mal";
    aviso.textContent = `Suman ${suma}%. ${suma === 100 ? "Listo, suman 100%." : suma < 100 ? `Faltan ${100 - suma}%.` : `Sobran ${suma - 100}%.`}`;
  }
  if (guardar) guardar.disabled = !cuadra;
}

function nombreRegistro(entidad, fila) {
  if (entidad === "regla") {
    const servicio = (S.catalogo.servicios.find((s) => s.id === fila.servicio_id) || {}).nombre;
    const empleado = nombreEmpleado(S.catalogo.empleados.find((e) => e.id === fila.empleado_id));
    if (fila.empleado_id && fila.servicio_id) return `${empleado} en ${servicio}: ${fila.porcentaje}%`;
    if (fila.servicio_id) return `${servicio}: ${fila.porcentaje}%`;
    return `Grupo ${fila.grupo}: ${fila.porcentaje}%`;
  }
  if (entidad === "reparto") {
    const sucursal = (S.catalogo.sucursales.find((s) => s.id === fila.branch_id) || {}).nombre || "Sucursal";
    const zona = fila.zona_id ? (S.catalogo.zonas.find((z) => z.id === fila.zona_id) || {}).nombre : "Toda la sucursal";
    const valor = fila.modo === "PORCENTAJE" ? fila.valor + "%" : plata(fila.valor) + " al día";
    return `${sucursal} · ${zona} · ${valor}`;
  }
  if (entidad === "usuario") return `${fila.nombre} (${fila.usuario}) · ${etiquetaRol(fila.rol)}${fila.correo ? " · " + fila.correo : " · sin correo"}`;
  if (entidad === "tipo") {
    const zona = (S.catalogo.zonas.find((z) => z.id === fila.zona_id) || {}).nombre || "";
    return `${fila.icono || ""} ${fila.nombre} · ${zona}`;
  }
  if (entidad === "servicio") {
    const zona = (S.catalogo.zonas.find((z) => z.id === fila.zona_id) || {}).nombre || "";
    return `${fila.icono || ""} ${fila.nombre} · ${zona}`;
  }
  if (entidad === "producto") return fila.nombre;
  if (entidad === "zona") {
    const sucursal = (S.catalogo.sucursales.find((s) => s.id === fila.branch_id) || {}).nombre || "";
    return `${fila.nombre} · ${sucursal}`;
  }
  if (entidad === "empleado") return nombreEmpleado(fila);
  return fila.nombre || fila.usuario || ("#" + fila.id);
}

function filasEntidad(entidad) {
  const mapa = {
    sucursal: S.catalogo.sucursales,
    zona: S.catalogo.zonas,
    tipo: S.catalogo.tipos,
    servicio: S.catalogo.servicios,
    producto: S.catalogo.productos,
    empleado: S.catalogo.empleados,
    regla: S.catalogo.reglas,
    reparto: S.catalogo.reparto,
    medio: S.catalogo.medios,
    usuario: S.catalogo.usuarios,
  };
  return mapa[entidad] || [];
}

function htmlListaAjuste() {
  const titulo = (MENU.find((m) => m[0] === S.ajuste) || [])[2] || "Ajustes";
  const filas = filasEntidad(S.ajuste);
  return `
    <button class="btn btn-ghost btn-small" id="volver-ajustes" type="button">Volver</button>
    <h2>${esc(titulo)}</h2>
    <button class="btn btn-green" id="agregar" type="button" style="max-width:280px">Agregar</button>
    <div class="lista" style="margin-top:12px">
      ${filas.map((f) => `<div class="item-ajuste ${Number(f.activo) === 0 ? "apagado" : ""}"><span>${esc(nombreRegistro(S.ajuste, f))}${Number(f.activo) === 0 ? " · apagado" : ""}</span>
        <span>
          <button class="btn btn-small" data-editar="${f.id}" type="button">Cambiar</button>
          <button class="btn btn-danger btn-small" data-quitar="${f.id}" type="button">Quitar</button>
          ${S.ajuste === "zona" ? `<button class="btn btn-small" data-copiar="${f.id}" type="button">Copiar carta</button>` : ""}
        </span></div>`).join("") || `<div class="vacio">Todavía no hay nada aquí.</div>`}
    </div>`;
}

function bindAjustes() {
  document.querySelectorAll("[data-ajuste]").forEach((b) => {
    b.onclick = async () => {
      S.ajuste = b.dataset.ajuste;
      S.modal = null;
      if (S.ajuste === "negocio") S.modal = { tipo: "negocio" };
      else if (S.ajuste === "clave") S.modal = { tipo: "clave" };
      else if (S.ajuste === "bolsillos") {
        S.bolsillosDraft = null;
        try { await cargarBase(); } catch (error) { toast(error.message); }
      }
      draw();
    };
  });
  const volver = document.getElementById("volver-ajustes");
  if (volver) volver.onclick = () => { S.ajuste = "menu"; S.modal = null; S.bolsillosDraft = null; draw(); };
  document.querySelectorAll("[data-bolsillo] input").forEach((input) => {
    input.addEventListener("input", pintarSumaBolsillos);
  });
  const agregarBolsa = document.getElementById("agregar-bolsillo");
  if (agregarBolsa) agregarBolsa.onclick = () => {
    leerBolsillosForm();
    S.bolsillosDraft.push({ nombre: "", porcentaje: 0, tipo: "GASTO", icono: "💡" });
    draw();
  };
  document.querySelectorAll("[data-quitar-bolsillo]").forEach((b) => {
    b.onclick = () => {
      leerBolsillosForm();
      S.bolsillosDraft.splice(Number(b.dataset.quitarBolsillo), 1);
      draw();
    };
  });
  const guardarBolsas = document.getElementById("guardar-bolsillos");
  if (guardarBolsas) guardarBolsas.onclick = async () => {
    leerBolsillosForm();
    try {
      const data = await api("/bolsillos", {
        method: "PUT",
        body: {
          bolsillos: S.bolsillosDraft.map((b) => ({
            nombre: String(b.nombre || "").trim(),
            porcentaje: Number(b.porcentaje) || 0,
            tipo: b.tipo || "GASTO",
            icono: b.icono || "",
            id: b.id || 0,
          })),
        },
      });
      S.catalogo.bolsillos = data.bolsillos;
      S.bolsillosDraft = null;
      toast("Bolsillos guardados");
      draw();
    } catch (error) { toast(error.message); }
  };
  const agregar = document.getElementById("agregar");
  if (agregar) agregar.onclick = () => { S.modal = { tipo: "entidad", entidad: S.ajuste, registro: {} }; draw(); };
  document.querySelectorAll("[data-editar]").forEach((b) => {
    b.onclick = () => {
      const registro = filasEntidad(S.ajuste).find((f) => f.id === Number(b.dataset.editar));
      S.modal = { tipo: "entidad", entidad: S.ajuste, registro };
      draw();
    };
  });
  document.querySelectorAll("[data-quitar]").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("¿Lo quitas? Si ya se usó, solo se apaga y el historial sigue.")) return;
      try {
        const data = await api("/ajustes/" + S.ajuste + "/" + b.dataset.quitar, { method: "DELETE" });
        toast(data.modo === "apagado" ? "Quedó apagado. El historial sigue." : "Eliminado");
        await cargarBase();
        draw();
      } catch (error) { toast(error.message); }
    };
  });
  document.querySelectorAll("[data-copiar]").forEach((b) => {
    b.onclick = () => {
      S.modal = { tipo: "copiar", destino: Number(b.dataset.copiar) };
      draw();
    };
  });
}

function camposEntidad(entidad, registro) {
  const zonas = S.catalogo.zonas.map((z) => `<option value="${z.id}" ${Number(registro.zona_id) === z.id ? "selected" : ""}>${esc(z.nombre)}</option>`).join("");
  const sucursalesOpt = S.catalogo.sucursales.map((s) => `<option value="${s.id}" ${Number(registro.branch_id) === s.id ? "selected" : ""}>${esc(s.nombre)}</option>`).join("");
  const servicios = activos(S.catalogo.servicios).map((s) => `<option value="${s.id}" ${Number(registro.servicio_id) === s.id ? "selected" : ""}>${esc(s.nombre)}</option>`).join("");
  const empleados = activos(S.catalogo.empleados).map((e) => `<option value="${e.id}" ${Number(registro.empleado_id) === e.id ? "selected" : ""}>${esc(nombreEmpleado(e))}</option>`).join("");
  if (entidad === "sucursal") return `
    <label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>
    <label>Teléfono</label><input name="telefono" value="${esc(registro.telefono || "")}">
    <label>Dirección</label><input name="direccion" value="${esc(registro.direccion || "")}">`;
  if (entidad === "zona") return `
    <label>Sucursal</label><select name="branch_id">${sucursalesOpt}</select>
    <label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>
    <label>Tipo</label><select name="tipo">
      ${["CARROS", "MOTOS", "MIXTA"].map((t) => `<option ${registro.tipo === t ? "selected" : ""}>${t}</option>`).join("")}
    </select>`;
  if (entidad === "tipo") return `
    <label>Zona</label><select name="zona_id">${zonas}</select>
    <label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>
    <label>Código</label><input name="codigo" value="${esc(registro.codigo || "")}" placeholder="AUTOMOVIL">
    <label>Icono</label><input name="icono" value="${esc(registro.icono || "🚗")}">`;
  if (entidad === "producto") {
    const margen = margenUtilidad(registro.costo, registro.precio);
    return `
    <label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>
    <label>Costo</label><input id="prod-costo" name="costo" type="number" min="0" value="${registro.costo ?? 0}">
    <label>Precio de venta</label><input id="prod-precio" name="precio" type="number" min="1" value="${registro.precio || ""}" required>
    <label>Margen de utilidad (%)</label><input id="prod-margen" type="number" step="0.1" max="99.9" value="${margen == null ? "" : textoPorcentaje(margen)}">
    <p class="margen-caja" id="prod-margen-texto"></p>
    <label>Existencia</label><input name="stock" type="number" min="0" value="${registro.stock || 0}">`;
  }
  if (entidad === "empleado") {
    const persona = {
      nombre: registro.nombre || "",
      apellido: registro.apellido || "",
    };
    if (!persona.apellido) {
      const partes = String(persona.nombre).trim().split(/\s+/).filter(Boolean);
      if (partes.length > 1) {
        persona.apellido = partes.pop();
        persona.nombre = partes.join(" ");
      }
    }
    return `
    <label>Nombres</label><input class="mayus" name="nombre" value="${esc(persona.nombre)}" required placeholder="JUAN">
    <label>Apellidos</label><input class="mayus" name="apellido" value="${esc(persona.apellido)}" required placeholder="PÉREZ">
    <label>Teléfono</label><input name="telefono" value="${esc(registro.telefono || "")}" inputmode="numeric" maxlength="10" placeholder="3000000000">
    <p class="ayuda">Nombres y apellidos se guardan en mayúscula. El teléfono acepta máximo 10 números.</p>`;
  }
  if (entidad === "medio") return `<label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>`;
  if (entidad === "usuario") return `
    <label>Usuario</label><input name="usuario" value="${esc(registro.usuario || "")}" required>
    <label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>
    <label>Rol</label><select name="rol"><option value="vendedor" ${registro.rol !== "admin" ? "selected" : ""}>Vendedor</option><option value="admin" ${registro.rol === "admin" ? "selected" : ""}>Administrador</option></select>
    <p class="ayuda">El vendedor solo registra ventas y sigue los vehículos en el tablero. El administrador ve la plata, los reportes y todos los ajustes.</p>
    <label>Sucursal (vacío = todas)</label><select name="branch_id"><option value="0">Todas</option>${sucursalesOpt}</select>
    <label>Correo</label><input name="correo" data-sin-pegar autocomplete="off" spellcheck="false" inputmode="email" value="${registro.id ? esc(registro.correo || "") : ""}" required placeholder="nombre@correo.com">
    <label>Repite el correo</label><input name="correo_confirma" data-sin-pegar autocomplete="off" spellcheck="false" inputmode="email" placeholder="Escríbelo otra vez">
    <p class="ayuda">Escríbelo en los dos campos. No se puede copiar ni pegar, porque si quedó mal se repetiría el error.</p>
    <label>Clave ${registro.id ? "(déjala vacía si no cambia)" : ""}</label><input name="clave" type="password">`;
  if (entidad === "regla") return `
    <label>Grupo, si aplica a varios</label><select name="grupo"><option value="">—</option>${["Basico", "Especial", "Premium"].map((g) => `<option ${registro.grupo === g ? "selected" : ""}>${g}</option>`).join("")}</select>
    <label>O un servicio</label><select name="servicio_id"><option value="0">Todos del grupo</option>${servicios}</select>
    <label>O solo un muchacho</label><select name="empleado_id"><option value="0">Cualquiera</option>${empleados}</select>
    <label>Porcentaje</label><input name="porcentaje" type="number" min="0" max="100" value="${registro.porcentaje ?? 40}" required>`;
  if (entidad === "reparto") return `
    <label>Sucursal</label><select name="branch_id">${sucursalesOpt}</select>
    <label>Zona</label><select name="zona_id"><option value="0">Toda la sucursal</option>${S.catalogo.zonas.map((z) => `<option value="${z.id}" ${Number(registro.zona_id) === z.id ? "selected" : ""}>${esc(z.nombre)}</option>`).join("")}</select>
    <label>Cómo se aparta</label><select name="modo"><option value="PORCENTAJE" ${registro.modo === "PORCENTAJE" ? "selected" : ""}>Porcentaje de lo que entra</option><option value="FIJO_DIARIO" ${registro.modo === "FIJO_DIARIO" ? "selected" : ""}>Un valor fijo cada día</option></select>
    <label>Valor</label><input name="valor" type="number" value="${registro.valor ?? 10}" required>`;
  return "";
}

function bindMargenProducto(form) {
  const costo = form.querySelector("#prod-costo");
  const precio = form.querySelector("#prod-precio");
  const margen = form.querySelector("#prod-margen");
  const caja = form.querySelector("#prod-margen-texto");
  if (!costo || !precio || !margen || !caja) return;
  let ancla = "precio";

  const pintar = () => {
    const pct = Number(margen.value);
    if (margen.value !== "" && !(pct < 100)) {
      caja.hidden = false;
      caja.textContent = "El margen tiene que ser menor de 100%.";
      return;
    }
    const formula = formulaProducto(costo.value, precio.value, margen.value, ancla);
    caja.hidden = !formula;
    caja.textContent = formula;
  };

  costo.addEventListener("input", () => {
    if (ancla === "margen" && margen.value !== "") {
      const venta = precioDesdeMargen(costo.value, margen.value);
      if (venta != null) precio.value = String(venta);
    } else {
      const pct = margenUtilidad(costo.value, precio.value);
      margen.value = pct == null ? "" : textoPorcentaje(pct);
    }
    pintar();
  });
  precio.addEventListener("input", () => {
    ancla = "precio";
    const pct = margenUtilidad(costo.value, precio.value);
    margen.value = pct == null ? "" : textoPorcentaje(pct);
    pintar();
  });
  margen.addEventListener("input", () => {
    ancla = "margen";
    const venta = precioDesdeMargen(costo.value, margen.value);
    if (venta != null) precio.value = String(venta);
    pintar();
  });
  pintar();
}

function htmlPrecios(registro) {
  const zonaId = Number(registro.zona_id || (S.catalogo.zonas[0] || {}).id || 0);
  const tipos = S.catalogo.tipos.filter((t) => t.zona_id === zonaId);
  return `
    <label>Zona</label><select name="zona_id" id="zona-servicio">${S.catalogo.zonas.map((z) => `<option value="${z.id}" ${zonaId === z.id ? "selected" : ""}>${esc(z.nombre)}</option>`).join("")}</select>
    <label>Nombre</label><input name="nombre" value="${esc(registro.nombre || "")}" required>
    <label>Grupo</label><select name="grupo">${["Basico", "Especial", "Premium"].map((g) => `<option ${registro.grupo === g ? "selected" : ""}>${g}</option>`).join("")}</select>
    <label>Icono</label><input name="icono" value="${esc(registro.icono || "🚿")}">
    <label>Duración, si aplica</label><input name="duracion" value="${esc(registro.duracion || "")}" placeholder="Dura 1 año">
    <div class="seccion">Precio por vehículo</div>
    ${tipos.map((t) => `<label>${esc(t.icono)} ${esc(t.nombre)}</label><input name="precio_${t.id}" type="number" value="${precioDe(registro, t.id) || ""}" placeholder="0 si no aplica">`).join("") || `<p>Primero crea los vehículos de esa zona.</p>`}`;
}

function serviciosCorregir(orden) {
  if (orden.tipo_orden === "PRODUCTO") return [];
  const mapa = new Map();
  for (const servicio of activos(S.catalogo.servicios)) {
    const valor = precioDe(servicio, orden.tipo_id);
    if (servicio.zona_id === orden.zona_id && valor != null) mapa.set(servicio.id, { ...servicio, valor });
  }
  for (const item of orden.items || []) {
    if (item.tipo === "SERVICIO" && item.servicio_id && !mapa.has(item.servicio_id)) {
      mapa.set(item.servicio_id, {
        id: item.servicio_id,
        nombre: item.descripcion,
        grupo: item.grupo || "Basico",
        valor: Number(item.precio) || Number(item.subtotal) || 0,
      });
    }
  }
  return [...mapa.values()];
}

function htmlServiciosCorregir(orden) {
  const lista = serviciosCorregir(orden);
  if (!lista.length) return "";
  const actuales = new Map(
    (orden.items || [])
      .filter((i) => i.tipo === "SERVICIO")
      .map((i) => [i.servicio_id, Number(i.precio) || Number(i.subtotal) || 0]),
  );
  const grupos = ["Basico", "Especial", "Premium"];
  return `<div class="seccion">Servicios</div>${grupos.map((grupo) => {
    const delGrupo = lista.filter((s) => s.grupo === grupo);
    if (!delGrupo.length) return "";
    return `<div class="seccion">${esc(grupo)}</div><div class="lista">${delGrupo.map((s) => {
      const valor = actuales.has(s.id) ? actuales.get(s.id) : s.valor;
      return `<button class="elige ${actuales.has(s.id) ? "on" : ""}" data-corr-svc="${s.id}" data-precio="${valor}" type="button"><span>${esc(s.nombre)}</span><strong>${plata(valor)}</strong></button>`;
    }).join("")}</div>`;
  }).join("")}`;
}

function productosCorregir(orden) {
  const mapa = new Map();
  for (const producto of activos(S.catalogo.productos)) {
    mapa.set(producto.id, {
      id: producto.id,
      nombre: producto.nombre,
      valor: Number(producto.precio) || 0,
      stock: Number(producto.stock) || 0,
      cantidad: 0,
    });
  }
  for (const item of orden.items || []) {
    if (item.tipo !== "PRODUCTO" || !item.producto_id) continue;
    const cantidad = Number(item.cantidad) || 0;
    const valor = Number(item.precio) || (cantidad ? Number(item.subtotal) / cantidad : 0);
    const previo = mapa.get(item.producto_id);
    if (previo) {
      previo.cantidad = cantidad;
      previo.valor = valor;
    } else {
      mapa.set(item.producto_id, {
        id: item.producto_id,
        nombre: item.descripcion,
        valor,
        stock: cantidad,
        cantidad,
      });
    }
  }
  return [...mapa.values()];
}

function htmlProductosCorregir(orden) {
  const lista = productosCorregir(orden);
  if (!lista.length) return "";
  return `<div class="seccion">Productos</div><div class="lista">${lista.map((p) => `
    <div class="producto">
      <div><strong>${esc(p.nombre)}</strong><div>${plata(p.valor)}</div></div>
      <div class="mas">
        <button type="button" data-corr-menos="${p.id}">−</button>
        <strong data-corr-cant="${p.id}" data-precio="${p.valor}" data-stock="${p.stock}">${p.cantidad}</strong>
        <button type="button" data-corr-mas="${p.id}">+</button>
      </div>
    </div>`).join("")}</div>`;
}

function totalCorreccion() {
  let total = 0;
  document.querySelectorAll("[data-corr-svc].on").forEach((b) => {
    total += Number(b.dataset.precio) || 0;
  });
  document.querySelectorAll("[data-corr-cant]").forEach((el) => {
    total += (Number(el.dataset.precio) || 0) * (Number(el.textContent) || 0);
  });
  return total;
}

function detalleMovimiento(movimiento) {
  const productos = (movimiento.productos || []).map((p) => `${p.nombre} x${p.cantidad}`).join(", ");
  const partes = [];
  if (productos) partes.push(esc(productos));
  if (movimiento.nota) partes.push(esc(movimiento.nota));
  return partes.length ? " · " + partes.join(" · ") : "";
}

function genteCorregir(orden) {
  const mapa = new Map();
  for (const empleado of activos(S.catalogo.empleados)) mapa.set(empleado.id, empleado);
  for (const col of orden.colaboradores || []) {
    if (!mapa.has(col.empleado_id)) {
      mapa.set(col.empleado_id, { id: col.empleado_id, nombre: col.empleado || "", apellido: "" });
    }
  }
  return [...mapa.values()];
}

function bindCorreccion() {
  const placa = document.getElementById("corr-placa");
  const tel = document.getElementById("corr-tel");
  const nombre = document.getElementById("corr-nombre");
  const guardar = document.getElementById("guardar-correccion");
  const normalizar = () => {
    if (placa) {
      const limpia = normalizarPlaca(placa.value);
      if (placa.value !== limpia) placa.value = limpia;
    }
    if (tel) {
      const digitos = soloDigitos(tel.value);
      if (tel.value !== digitos) tel.value = digitos;
    }
    if (nombre) {
      const limpio = normalizarNombreCliente(nombre.value);
      if (nombre.value !== limpio) nombre.value = limpio;
    }
    const gente = document.querySelectorAll("[data-corr-emp].on").length;
    const hayServicios = document.querySelector("[data-corr-svc]");
    const servicios = document.querySelectorAll("[data-corr-svc].on").length;
    const total = document.getElementById("corr-total");
    if (total) total.textContent = "Total " + plata(totalCorreccion());
    if (guardar) {
      guardar.disabled = !(
        normalizarPlaca(placa.value).length >= 5
        && normalizarNombreCliente(nombre.value).trim().length >= 3
        && soloDigitos(tel.value).length >= 10
        && gente > 0
        && (!hayServicios || servicios > 0)
      );
    }
  };
  if (placa) placa.addEventListener("input", normalizar);
  if (tel) tel.addEventListener("input", normalizar);
  if (nombre) nombre.addEventListener("input", normalizar);
  document.querySelectorAll("[data-corr-emp], [data-corr-svc], [data-corr-rev]").forEach((b) => {
    b.onclick = () => {
      b.classList.toggle("on");
      normalizar();
    };
  });
  document.querySelectorAll("[data-corr-mas], [data-corr-menos]").forEach((b) => {
    b.onclick = () => {
      const id = b.dataset.corrMas || b.dataset.corrMenos;
      const caja = document.querySelector(`[data-corr-cant="${id}"]`);
      if (!caja) return;
      const actual = Number(caja.textContent) || 0;
      const tope = Number(caja.dataset.stock) || 0;
      const siguiente = b.dataset.corrMas ? Math.min(tope, actual + 1) : Math.max(0, actual - 1);
      caja.textContent = String(siguiente);
      normalizar();
    };
  });
  normalizar();
  guardar.onclick = async () => {
    normalizar();
      if (guardar.disabled) {
      toast("Revisa la placa, el nombre, el WhatsApp, los servicios y quién lava.");
      return;
    }
    const servicios = [...document.querySelectorAll("[data-corr-svc].on")].map((b) => Number(b.dataset.corrSvc));
    const productos = [...document.querySelectorAll("[data-corr-cant]")].map((el) => ({
      producto_id: Number(el.dataset.corrCant),
      cantidad: Number(el.textContent) || 0,
    })).filter((p) => p.cantidad > 0);
    try {
      await api("/ordenes/" + S.modal.orden.id, {
        method: "PATCH",
        body: {
          placa: normalizarPlaca(placa.value),
          cliente_nombre: normalizarNombreCliente(nombre.value).trim(),
          cliente_telefono: soloDigitos(tel.value),
          colaboradores: [...document.querySelectorAll("[data-corr-emp].on")].map((b) => ({
            empleado_id: Number(b.dataset.corrEmp),
            peso: 1,
          })),
          ...(document.querySelector("[data-corr-svc]") ? { servicios } : {}),
          ...(document.querySelector("[data-corr-cant]") ? { productos } : {}),
          checklist: [...document.querySelectorAll("[data-corr-rev].on")].map((b) => b.dataset.corrRev),
          nota: (document.getElementById("corr-nota") || {}).value || "",
        },
      });
      S.modal = null;
      toast("Datos corregidos");
      await cargarTablero();
    } catch (error) {
      toast(error.message);
    }
  };
}

function htmlModal() {
  const m = S.modal;
  let cuerpo = "";
  if (m.tipo === "muchachos") {
    const resumen = m.resumen || {};
    const gente = resumen.por_colaborador || [];
    cuerpo = `<h2>Para los muchachos</h2>
      <p>De lo que ya se cobró hoy en ${esc(resumen.branch_nombre || "la sucursal")}.</p>
      ${gente.length ? gente.map((persona) => `
        <div class="muchacho">
          <div class="producto"><strong>👷 ${esc(persona.nombre)}</strong><strong>${plata(persona.comision)}</strong></div>
          <div class="lista">${(persona.trabajos || []).map((t) => `<div><span>${esc(t.placa)} · ${esc(t.servicio)}${t.porcentaje ? ` · ${t.porcentaje}%` : ""}</span><strong>${plata(t.monto)}</strong></div>`).join("")}</div>
        </div>`).join("") : `<div class="vacio">Todavía no hay comisión para entregar.</div>`}
      <p class="margen-caja">En total entregas <strong>${plata(resumen.comisiones || 0)}</strong></p>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "bolsillo") {
    const bolsa = m.bolsa || {};
    const resumen = m.resumen || {};
    const movimientos = bolsa.movimientos || [];
    const notaIngreso = bolsa.tipo === "UTILIDAD"
      ? "Lo que queda después de los muchachos y de los gastos"
      : `${bolsa.porcentaje}% de lo que se cobró hoy`;
    cuerpo = `<h2>${esc(bolsa.nombre || "Bolsillo")}</h2>
      <p>Movimientos de hoy en ${esc(resumen.branch_nombre || "la sucursal")}.</p>
      <div class="seccion">Ingresos</div>
      <div class="lista"><div><span>Lo que entró hoy<small class="gasto-meta">${esc(notaIngreso)}</small></span><strong>${plata(bolsa.monto)}</strong></div></div>
      <div class="seccion">Egresos</div>
      <div class="lista">${movimientos.length ? movimientos.map((movimiento) => `
        <div><span>${esc(movimiento.concepto)}<small class="gasto-meta">${movimiento.clase === "COMPRA" ? "Compra" : "Pago"}${detalleMovimiento(movimiento)}</small></span><strong>${plata(movimiento.monto)}</strong></div>
      `).join("") : `<div class="vacio">Todavía no sale dinero de este bolsillo.</div>`}</div>
      <p class="margen-caja">Queda <strong>${plata(bolsa.queda)}</strong></p>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "corregir") {
    const orden = m.orden;
    const elegidos = new Set((orden.colaboradores || []).map((c) => c.empleado_id));
    const marcas = new Set(Array.isArray(orden.checklist) ? orden.checklist : []);
    const gente = genteCorregir(orden);
    cuerpo = `<h2>Corregir ${esc(orden.placa || orden.vehiculo)}</h2>
      <label>Placa</label><input id="corr-placa" class="placa-input" value="${esc(orden.placa || "")}" maxlength="8" autocomplete="off">
      <label>WhatsApp del cliente</label><input id="corr-tel" value="${esc(orden.cliente_telefono || "")}" inputmode="numeric" maxlength="10" autocomplete="off">
      <label>Nombre del cliente</label><input id="corr-nombre" class="mayus" value="${esc(orden.cliente_nombre || "")}" maxlength="80" autocomplete="off">
      <div class="seccion">Revisión al recibir</div>
      <div class="chips">
        ${opcionesRevision().map((item) => `<button class="chip ${marcas.has(item) ? "on" : ""}" data-corr-rev="${esc(item)}" type="button">${esc(item)}</button>`).join("")}
      </div>
      <label>Nota (opcional)</label>
      <textarea id="corr-nota" class="nota-corta" maxlength="240">${esc(orden.nota || "")}</textarea>
      ${htmlServiciosCorregir(orden)}
      ${htmlProductosCorregir(orden)}
      <p class="margen-caja" id="corr-total"></p>
      <div class="seccion">Quién lava</div>
      <div class="chips">
        ${gente.map((e) => `<button class="chip ${elegidos.has(e.id) ? "on" : ""}" data-corr-emp="${e.id}" type="button">👷 ${esc(nombreEmpleado(e))}</button>`).join("") || `<span class="ayuda">No hay muchachos activos.</span>`}
      </div>
      <div style="height:12px"></div>
      <button class="btn btn-green" id="guardar-correccion" type="button">Guardar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "confirmar-cobro") {
    const orden = m.orden;
    cuerpo = `<h2>¿Seguro que cobras?</h2>
      <p>${esc(orden.placa || "")} · ${esc(orden.cliente_nombre || orden.vehiculo || "")}</p>
      <p class="precio">${plata(orden.total)}</p>
      <p>El cliente está en el local. Después de cobrar ya no se puede corregir.</p>
      <button class="btn btn-green" id="confirmar-cobro" type="button">Sí, cobrar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "cobrar") {
    const orden = m.orden;
    const medios = activos(S.catalogo.medios);
    cuerpo = `<h2>Cobrar ${plata(orden.total)}</h2><p>${esc(orden.placa || orden.vehiculo)}</p>
      ${medios.map((medio) => `<button class="btn btn-green" style="margin-bottom:8px" data-medio="${esc(medio.nombre)}" type="button">${esc(medio.nombre)}</button>`).join("")}
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "telefono") {
    cuerpo = `<h2>WhatsApp del cliente</h2><input id="tel-modal" inputmode="tel" placeholder="300 000 0000"><div style="height:10px"></div>
      <button class="btn btn-green" id="guardar-tel" type="button">Avisar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "confirmar-cierre") {
    cuerpo = `<h2>Ojo con la caja</h2><p>${esc(m.aviso)}</p>
      <button class="btn btn-green" id="confirmar-cierre" type="button">Sí, cerrar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "cierre-listo") {
    cuerpo = `<h2>Día cerrado</h2><div class="frase">${esc(m.texto)}</div>
      <div class="fila-botones">
        <button class="btn" id="imprimir-cierre" type="button">Imprimir</button>
        ${m.whatsapp ? `<a class="btn btn-green" style="display:grid;place-items:center;text-decoration:none" href="${esc(m.whatsapp)}" target="_blank">Enviar por WhatsApp</a>` : ""}
        <button class="btn btn-ghost" id="cerrar-modal" type="button">Listo</button>
      </div>`;
  } else if (m.tipo === "negocio") {
    const n = S.catalogo.negocio;
    cuerpo = `<h2>Mi negocio</h2>
      <label>Nombre</label><input id="neg-nombre" value="${esc(n.nombre)}">
      <label>Línea</label><input id="neg-linea" value="${esc(n.linea)}">
      <label>Teléfono</label><input id="neg-tel" value="${esc(n.telefono)}">
      <label>WhatsApp del dueño, para el cierre</label><input id="neg-dueno" value="${esc(n.whatsapp_dueno)}">
      <div class="seccion">Correo para cambiar la clave</div>
      <label>Servidor</label><input id="smtp-host" value="${esc(n.smtp_host || "")}" placeholder="smtp.gmail.com">
      <label>Puerto</label><input id="smtp-port" value="${esc(n.smtp_port || "587")}">
      <label>Usuario del correo</label><input id="smtp-usuario" value="${esc(n.smtp_usuario || "")}" autocomplete="off">
      <label>Clave del correo ${n.smtp_listo ? "(déjala vacía si no cambia)" : ""}</label><input id="smtp-clave" type="password" autocomplete="new-password">
      <label>Correo que envía</label><input id="smtp-desde" value="${esc(n.smtp_desde || "")}" placeholder="lavadero@correo.com">
      <p class="ayuda">Desde aquí sale el mensaje de Olvidé mi clave. En Gmail usa una clave de aplicación y el puerto 587.</p>
      <label>Mensaje cuando el vehículo está listo</label>
      <textarea id="neg-plantilla">${esc(n.whatsapp_plantilla)}</textarea>
      <p class="ayuda">Puedes usar {negocio} {vehiculo} {placa} {sucursal} {telefono}</p>
      <button class="btn btn-green" id="guardar-negocio" type="button">Guardar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "clave") {
    cuerpo = `<h2>Mi clave</h2>
      <label>Clave actual</label><input id="clave-actual" type="password">
      <label>Clave nueva</label><input id="clave-nueva" type="password">
      <button class="btn btn-green" id="guardar-clave" type="button">Guardar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "copiar") {
    const otras = S.catalogo.zonas.filter((z) => z.id !== m.destino);
    cuerpo = `<h2>Traer la carta de otra zona</h2>
      <select id="origen-zona">${otras.map((z) => `<option value="${z.id}">${esc(z.nombre)}</option>`).join("")}</select>
      <div style="height:10px"></div>
      <button class="btn btn-green" id="hacer-copia" type="button">Copiar servicios y precios</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button>`;
  } else if (m.tipo === "entidad") {
    const registro = m.registro || {};
    const campos = m.entidad === "servicio" ? htmlPrecios(registro) : camposEntidad(m.entidad, registro);
    cuerpo = `<h2>${registro.id ? "Cambiar" : "Agregar"}</h2><form id="form-entidad">${campos}
      <div style="height:12px"></div>
      <button class="btn btn-green" type="submit">Guardar</button>
      <button class="btn btn-ghost" id="cerrar-modal" type="button">Volver</button></form>`;
  }
  return `<div class="modal-fondo"><div class="modal">${cuerpo}</div></div>`;
}

function impedirCopiar(input) {
  ["paste", "drop", "copy", "cut"].forEach((evento) => {
    input.addEventListener(evento, (ev) => ev.preventDefault());
  });
}

function correoEscrito(valor) {
  return String(valor || "").trim().toLowerCase();
}

function bindModal() {
  document.querySelectorAll("[data-sin-pegar]").forEach(impedirCopiar);
  const cerrar = document.getElementById("cerrar-modal");
  if (cerrar) cerrar.onclick = () => { S.modal = null; draw(); };
  document.querySelectorAll("[data-medio]").forEach((b) => {
    b.onclick = () => cobrarCon(b.dataset.medio);
  });
  const correccion = document.getElementById("guardar-correccion");
  if (correccion) bindCorreccion();
  const tel = document.getElementById("guardar-tel");
  if (tel) tel.onclick = async () => {
    const numero = document.getElementById("tel-modal").value;
    try {
      await api("/ordenes/" + S.modal.ordenId, { method: "PATCH", body: { cliente_telefono: numero } });
      const id = S.modal.ordenId;
      S.modal = null;
      await cargarTablero();
      abrirWhatsapp(id);
    } catch (error) { toast(error.message); }
  };
  const confirmarCobro = document.getElementById("confirmar-cobro");
  if (confirmarCobro) confirmarCobro.onclick = () => {
    S.modal = { tipo: "cobrar", orden: S.modal.orden };
    draw();
  };
  const confirmar = document.getElementById("confirmar-cierre");
  if (confirmar) confirmar.onclick = () => { S.modal = null; cerrarDia(true); };
  const imprimir = document.getElementById("imprimir-cierre");
  if (imprimir) imprimir.onclick = () => imprimirRecibo(S.resumen);
  const negocio = document.getElementById("guardar-negocio");
  if (negocio) negocio.onclick = guardarNegocio;
  const clave = document.getElementById("guardar-clave");
  if (clave) clave.onclick = guardarClave;
  const copia = document.getElementById("hacer-copia");
  if (copia) copia.onclick = async () => {
    try {
      await api("/zonas/" + S.modal.destino + "/copiar/" + document.getElementById("origen-zona").value, { method: "POST" });
      toast("Carta copiada. Ya puedes cambiar precios.");
      S.modal = null;
      await cargarBase();
      draw();
    } catch (error) { toast(error.message); }
  };
  const form = document.getElementById("form-entidad");
  if (form) {
    form.onsubmit = guardarEntidad;
    form.querySelectorAll(".mayus").forEach((campo) => {
      campo.addEventListener("input", () => {
        const limpio = campo.value.toUpperCase().replace(/[^A-ZÁÉÍÓÚÜÑ ]/g, "");
        if (campo.value !== limpio) campo.value = limpio;
      });
    });
    if (S.modal.entidad === "producto") bindMargenProducto(form);
    const telEmpleado = form.querySelector("[name=telefono]");
    if (telEmpleado && S.modal.entidad === "empleado") {
      telEmpleado.addEventListener("input", () => {
        const digitos = telEmpleado.value.replace(/\D/g, "").slice(0, 10);
        if (telEmpleado.value !== digitos) telEmpleado.value = digitos;
      });
    }
    const zona = document.getElementById("zona-servicio");
    if (zona) zona.onchange = () => {
      const datos = Object.fromEntries(new FormData(form).entries());
      S.modal.registro = { ...S.modal.registro, ...datos, zona_id: Number(datos.zona_id), precios: {} };
      draw();
    };
  }
}

async function cobrarCon(medio) {
  const orden = S.modal.orden;
  try {
    await api("/ordenes/" + orden.id + "/cobrar", {
      method: "POST",
      body: { pagos: [{ medio, monto: orden.total }] },
    });
    S.modal = null;
    toast("Cobrado en " + medio);
    await cargarTablero();
  } catch (error) {
    toast(error.message);
  }
}

async function guardarNegocio() {
  try {
    await api("/config", {
      method: "PUT",
      body: {
        negocio_nombre: document.getElementById("neg-nombre").value,
        negocio_linea: document.getElementById("neg-linea").value,
        negocio_telefono: document.getElementById("neg-tel").value,
        whatsapp_dueno: document.getElementById("neg-dueno").value,
        whatsapp_plantilla: document.getElementById("neg-plantilla").value,
        smtp_host: document.getElementById("smtp-host").value,
        smtp_port: document.getElementById("smtp-port").value,
        smtp_usuario: document.getElementById("smtp-usuario").value,
        smtp_clave: document.getElementById("smtp-clave").value,
        smtp_desde: document.getElementById("smtp-desde").value,
      },
    });
    toast("Negocio actualizado");
    S.modal = null;
    await cargarBase();
    draw();
  } catch (error) { toast(error.message); }
}

async function guardarClave() {
  try {
    await api("/clave", {
      method: "POST",
      body: {
        actual: document.getElementById("clave-actual").value,
        nueva: document.getElementById("clave-nueva").value,
      },
    });
    toast("Clave actualizada");
    S.modal = null;
    draw();
  } catch (error) { toast(error.message); }
}

async function guardarEntidad(ev) {
  ev.preventDefault();
  const datos = Object.fromEntries(new FormData(ev.target).entries());
  const entidad = S.modal.entidad;
  const registro = S.modal.registro || {};
  if (entidad === "empleado") {
    datos.nombre = String(datos.nombre || "").toUpperCase();
    datos.apellido = String(datos.apellido || "").toUpperCase();
    datos.telefono = String(datos.telefono || "").replace(/\D/g, "").slice(0, 10);
  }
  if (entidad === "usuario") {
    const correo = correoEscrito(datos.correo);
    const confirma = correoEscrito(datos.correo_confirma);
    const guardado = correoEscrito(registro.correo);
    if (!registro.id || !guardado || correo !== guardado) {
      if (!correo || correo !== confirma) {
        toast("Escribe el correo dos veces, igual. No lo copies.");
        return;
      }
    }
    datos.correo = correo;
    datos.correo_confirma = confirma;
  }
  if (entidad === "servicio") {
    datos.precios = {};
    for (const [clave, valor] of Object.entries(datos)) {
      if (clave.startsWith("precio_") && valor !== "") datos.precios[clave.slice(7)] = Number(valor);
    }
  }
  try {
    const ruta = registro.id ? "/ajustes/" + entidad + "/" + registro.id : "/ajustes/" + entidad;
    await api(ruta, { method: registro.id ? "PUT" : "POST", body: datos });
    toast("Guardado");
    S.modal = null;
    await cargarBase();
    draw();
  } catch (error) { toast(error.message); }
}

function fechaLarga(iso) {
  const meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const partes = String(iso || "").slice(0, 10).split("-");
  if (partes.length !== 3) return iso || "";
  return `${Number(partes[2])} de ${meses[Number(partes[1]) - 1]} de ${partes[0]}`;
}

function imprimirRecibo(resumen) {
  if (!resumen) return;
  const ventana = window.open("", "cierre", "width=480,height=760");
  if (!ventana) {
    toast("Permite las ventanas emergentes para imprimir el recibo.");
    return;
  }
  const negocio = S.catalogo.negocio;
  const telefono = String(negocio.telefono || "").replace(/(\d{3})(\d{3})(\d{4})/, "$1 $2 $3");
  ventana.document.open();
  ventana.document.write(`<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Cierre del día · ${esc(negocio.nombre)}</title>
<style>
  @page { size: A5; margin: 12mm; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #eef3ef; font-family: "Segoe UI", Nunito, sans-serif; color: #14301c; }
  .hoja { width: 420px; margin: 18px auto; background: white; border-radius: 18px; overflow: hidden; box-shadow: 0 12px 40px rgba(20,48,28,.12); }
  .cabeza { background: #1e9b45; color: white; text-align: center; padding: 22px 20px 18px; }
  .logo { width: 118px; height: 66px; color: white; }
  h1 { margin: 6px 0 0; font-size: 28px; letter-spacing: 1px; }
  .detalle { color: #f5c400; font-weight: 800; letter-spacing: 4px; font-size: 14px; }
  .linea { margin: 8px 0 0; opacity: .92; font-size: 13px; }
  .cuerpo { padding: 18px 20px 22px; }
  .kicker { font-size: 12px; letter-spacing: 2px; color: #5c6b62; font-weight: 800; }
  h2 { margin: 2px 0 0; font-size: 22px; }
  .cuando { color: #5c6b62; margin: 2px 0 14px; }
  .fila { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; border-radius: 12px; margin-bottom: 8px; color: white; font-weight: 800; }
  .fila span { font-weight: 700; }
  .naranja { background: #f97316; }
  .azul { background: #3b82f6; }
  .verde { background: #1e9b45; }
  .resumen { background: #f6f8f6; border-radius: 12px; padding: 12px 14px; line-height: 1.45; }
  .pie { margin-top: 16px; border-top: 3px solid #f5c400; padding-top: 10px; text-align: center; font-size: 12px; color: #5c6b62; }
  @media print { body { background: white; } .hoja { box-shadow: none; margin: 0; width: auto; } }
</style></head>
<body><article class="hoja">
  <header class="cabeza">
    ${logoMarca()}
    <h1>CAR WASH</h1>
    <div class="detalle">DETAILING</div>
    <p class="linea">${esc(negocio.linea || "S.O.P. soluciones operativas")}<br>${esc(telefono)}</p>
  </header>
  <div class="cuerpo">
    <div class="kicker">CIERRE DEL DÍA</div>
    <h2>${esc(resumen.branch_nombre || "")}</h2>
    <p class="cuando">${esc(fechaLarga(resumen.fecha))}</p>
    ${(resumen.bolsillos || []).map((b) => `<div class="fila" style="background:${esc(b.color || "#1e9b45")}"><span>${esc(b.nombre)} · ${esc(b.porcentaje)}%${Number(b.gastado) ? ` · salió ${plata(b.gastado)}` : ""}</span><strong>${plata(b.monto)}</strong></div>`).join("")}
    <p class="resumen">${esc(resumen.texto || "")}</p>
    <p class="pie">${esc(negocio.nombre)} · ${esc(resumen.vehiculos || 0)} vehículos · Entró ${plata(resumen.producido)}</p>
  </div>
</article></body></html>`);
  ventana.document.close();
  ventana.focus();
  setTimeout(() => ventana.print(), 250);
}

function bindVista() {
  if (S.vista === "lavar") bindLavar();
  if (S.vista === "tablero") bindTablero();
  if (S.vista === "plata") bindPlata();
  if (S.vista === "gastos") bindGastos();
  if (S.vista === "reportes") bindReportes();
  if (S.vista === "ajustes") bindAjustes();
}

async function boot() {
  if (!S.token || !S.sesion) {
    draw();
    return;
  }
  try {
    await cargarBase();
    draw();
  } catch (error) {
    salir(false);
    draw();
  }
  clearInterval(S.timer);
  S.timer = setInterval(() => {
    if (S.vista === "tablero" && S.sesion && !S.modal) cargarTablero(true);
  }, 5000);
}

boot();
