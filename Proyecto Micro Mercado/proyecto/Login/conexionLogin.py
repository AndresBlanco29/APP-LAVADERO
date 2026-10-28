import threading
import time
import pymysql


class _ReusableConnection:
    """Keeps the Railway socket open. close() only frees cursors so callers stay compatible."""

    def __init__(self, raw):
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "_cursors", [])

    def cursor(self, *args, **kwargs):
        cur = self._raw.cursor(*args, **kwargs)
        self._cursors.append(cur)
        return cur

    def close(self):
        for cur in list(self._cursors):
            try:
                cur.close()
            except Exception:
                pass
        object.__setattr__(self, "_cursors", [])
        FormularioLogin._soltar()

    def ping(self, reconnect=True):
        return self._raw.ping(reconnect=reconnect)

    def commit(self):
        return self._raw.commit()

    def rollback(self):
        try:
            return self._raw.rollback()
        except Exception:
            return None

    def __getattr__(self, name):
        return getattr(self._raw, name)


class FormularioLogin:
    _lock = threading.RLock()
    _pool = None
    _last_ok = 0.0

    @classmethod
    def _soltar(cls):
        try:
            cls._lock.release()
        except RuntimeError:
            pass

    @classmethod
    def conexion_base_de_datos(cls, silencioso=False):
        cls._lock.acquire()
        try:
            cone = cls._conexion_interna(silencioso)
        except Exception:
            cls._lock.release()
            raise
        if cone is None:
            cls._lock.release()
        return cone

    @classmethod
    def _conexion_interna(cls, silencioso=False):
        now = time.monotonic()
        if cls._pool is not None:
            if now - cls._last_ok < 20:
                cls._last_ok = now
                return cls._pool
            try:
                cls._pool.ping(reconnect=True)
                cls._last_ok = now
                return cls._pool
            except Exception:
                cls._desechar()
        try:
            raw = pymysql.connect(
                user="root",
                password="gOETksBanEaqSzdndWKVEQKKoHWaRmIU",
                host="hopper.proxy.rlwy.net",
                port=54973,
                database="railway",
                connect_timeout=5,
                read_timeout=30,
                write_timeout=30,
                charset="utf8mb4",
                autocommit=False,
            )
            cls._pool = _ReusableConnection(raw)
            cls._last_ok = time.monotonic()
            return cls._pool
        except pymysql.MySQLError as error:
            if not silencioso:
                print("Error al conectar a la base de datos: {}".format(error))
            cls._pool = None
            return None

    @classmethod
    def _desechar(cls):
        if cls._pool is None:
            return
        try:
            cls._pool._raw.close()
        except Exception:
            pass
        cls._pool = None

    @classmethod
    def cerrar_conexion(cls):
        cls._lock.acquire()
        try:
            cls._desechar()
        finally:
            cls._lock.release()
