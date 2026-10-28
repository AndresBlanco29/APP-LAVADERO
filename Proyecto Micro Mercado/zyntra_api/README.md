# Zyntra API para Railway

Esta carpeta es la API del celular (jefe). Reemplaza `api-production-b438` y ahora sí manda **Anulada**, **Estado** y **Ganancia**.

## Desplegar en el servicio que ya existe (misma URL)

1. Entra a [Railway](https://railway.app) y abre el servicio `api-production-b438`.
2. En **Settings → Source** conecta esta carpeta (`zyntra_api`) o súbela con CLI:

```bash
cd "D:\Proyecto Micro Mercado\zyntra_api"
npx @railway/cli login
npx @railway/cli link
npx @railway/cli up
```

3. En **Variables** conecta el MySQL del mismo proyecto (o pega):

| Variable | Valor típico |
|---|---|
| `MYSQLHOST` | el host del plugin MySQL (interno si está en el mismo proyecto) |
| `MYSQLPORT` | `3306` interno / el puerto público si usas el proxy |
| `MYSQLUSER` | `root` |
| `MYSQLPASSWORD` | la del MySQL de Railway |
| `MYSQLDATABASE` | `railway` |

Railway inyecta esas variables si usas **Add variable → Variable reference** al servicio MySQL.

4. Start command (ya está en `Procfile` / `railway.json`):

`uvicorn main:app --host 0.0.0.0 --port $PORT`

## Probar en local

Copia `.env.example` a `.env`, pon la contraseña de MySQL y corre:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Abre `http://127.0.0.1:8000/docs` y `http://127.0.0.1:8000/ventas`.
Cada venta debe traer `Anulada`, `Estado` y `Ganancia`.
