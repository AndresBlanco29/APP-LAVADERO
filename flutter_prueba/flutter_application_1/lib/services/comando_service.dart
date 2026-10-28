import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_client.dart';
import 'dashboard_service.dart';

final cop = NumberFormat.currency(locale: 'es_CO', symbol: '\$', decimalDigits: 0);

class ComandoService {
  static const _wsHint = '/ws/devoluciones/admin/';
  static const pinKey = 'approval_pin';

  Future<int> adminId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt('admin_id') ?? 0;
  }

  Future<String> adminUsuario() async {
    final prefs = await SharedPreferences.getInstance();
    return (prefs.getString('admin_usuario') ?? '').trim();
  }

  Future<String> approvalPin() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(pinKey) ?? '';
  }

  Future<void> setApprovalPin(String pin) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(pinKey, pin.trim());
  }

  String wsUrl(int adminId) {
    final http = ApiClient.baseUrl;
    final ws = http.startsWith('https')
        ? http.replaceFirst('https', 'wss')
        : http.replaceFirst('http', 'ws');
    return '$ws$_wsHint$adminId/';
  }

  Future<Map<String, dynamic>> resumen() async {
    final data = await ApiClient.tryGet('/comando/resumen/', ttl: Duration.zero);
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    final dash = await DashboardService().obtenerResumen();
    final ventaHoy = (dash['totalDia'] as num?)?.toDouble() ?? 0;
    final ventaMes = (dash['totalMes'] as num?)?.toDouble() ?? 0;
    final utilHoy = (dash['gananciaDia'] as num?)?.toDouble() ?? 0;
    final utilMes = (dash['gananciaMes'] as num?)?.toDouble() ?? 0;
    return {
      'hoy': {
        'venta': ventaHoy,
        'costo': (ventaHoy - utilHoy).clamp(0, double.infinity),
        'utilidad': utilHoy,
        'margen_pct': ventaHoy == 0 ? 0 : (utilHoy / ventaHoy) * 100,
        'tickets': dash['ticketsDia'] ?? 0,
      },
      'mes': {
        'venta': ventaMes,
        'costo': (ventaMes - utilMes).clamp(0, double.infinity),
        'utilidad': utilMes,
        'margen_pct': ventaMes == 0 ? 0 : (utilMes / ventaMes) * 100,
        'tickets': dash['ticketsMes'] ?? 0,
      },
      'pendientes': 0,
      'fefo': {'vencidos': 0, 'd30': 0, 'd60': 0, 'd90': 0},
      'bolsillos': {'bolsillos': <dynamic>[]},
      'live_sales': <dynamic>[],
      'offline': true,
      'ventasPorDia': dash['ventasPorDia'],
    };
  }

  Future<List<Map<String, dynamic>>> pendientes() async {
    final data = await ApiClient.tryGet(
      '/api/v1/devoluciones/pendientes/',
      ttl: Duration.zero,
    );
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> responder({
    required int id,
    required String estado,
    String nota = '',
  }) async {
    final admin = await adminId();
    final data = await ApiClient.postJson(
      '/api/v1/devoluciones/$id/responder/',
      {
        'estado': estado,
        'nota': nota,
        'admin_id': admin,
        'usuario': await adminUsuario(),
      },
    );
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> bolsillos() async {
    final data = await ApiClient.tryGet('/api/v1/bolsillos/', ttl: Duration.zero);
    if (data is Map) return Map<String, dynamic>.from(data);
    return {'bolsillos': <dynamic>[], 'venta_hoy': 0, 'venta_mes': 0};
  }

  Future<void> crearBolsillo(Map<String, dynamic> body) async {
    body = Map<String, dynamic>.from(body);
    body['usuario'] = await adminUsuario();
    body['admin_id'] = await adminId();
    await ApiClient.postJson('/api/v1/bolsillos/', body);
    ApiClient.invalidate('/api/v1/bolsillos/');
  }

  Future<Map<String, dynamic>> egresoBolsillo({
    required int id,
    required double monto,
    String nota = '',
    String metodo = 'Efectivo',
    String categoria = '',
    String comprobante = '',
    List<Map<String, dynamic>> origenes = const [],
  }) async {
    final body = <String, dynamic>{
      'monto': monto,
      'nota': nota,
      'metodo': metodo,
      'categoria': categoria,
      'comprobante': comprobante,
      'admin_id': await adminId(),
      'usuario': await adminUsuario(),
    };
    if (origenes.isNotEmpty) {
      body['origenes'] = origenes;
    }
    final data = await ApiClient.postJson(
      '/api/v1/bolsillos/$id/egreso/',
      body,
    );
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> pagoProveedor({
    required List<Map<String, dynamic>> origenes,
    String nota = '',
    String comprobante = '',
  }) async {
    // Entrega 4: pagos van al bolsillo central con validación por medio.
    final total = origenes.fold<double>(
      0,
      (a, o) => a + ((o['monto'] as num?)?.toDouble() ?? 0),
    );
    return bolsilloProveedoresPago(
      proveedor: nota.isEmpty ? 'Proveedor' : nota,
      total: total,
      origenes: [
        for (final o in origenes)
          {
            'metodo': '${o['metodo']}' == 'Tarjeta' || '${o['metodo']}' == 'Transferencia'
                ? ('${o['metodo']}' == 'Tarjeta' ? 'Datafono' : 'Nequi')
                : o['metodo'],
            'monto': o['monto'],
          },
      ],
      referencia: comprobante,
      observacion: nota,
    );
  }

  Future<Map<String, dynamic>> cierreDiarioResumen(String fechaDesde) async {
    final q = Uri.encodeQueryComponent(fechaDesde);
    final data = await ApiClient.tryGet(
      '/cierre-diario/resumen/?fecha_desde=$q',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'fecha_desde': fechaDesde,
      'total_ventas': 0,
      'tickets': 0,
      'correcciones': 0,
      'medios': <dynamic>[],
    };
  }

  Future<Map<String, dynamic>> cierreDiarioDetalle(int id) async {
    final data = await ApiClient.tryGet('/cierre-diario/$id/', ttl: Duration.zero);
    if (data is Map) return Map<String, dynamic>.from(data);
    return {'cierre': <String, dynamic>{}, 'medios': <dynamic>[]};
  }

  Future<List<Map<String, dynamic>>> cierreDiarioAuditoria({
    int? cierreId,
    String? fechaDesde,
  }) async {
    final params = <String>[];
    if (cierreId != null) params.add('cierre_id=$cierreId');
    if (fechaDesde != null && fechaDesde.isNotEmpty) {
      params.add('fecha_desde=${Uri.encodeQueryComponent(fechaDesde)}');
    }
    final q = params.isEmpty ? '' : '?${params.join('&')}';
    final data = await ApiClient.tryGet('/cierre-diario/auditoria/$q', ttl: Duration.zero);
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<String> _usuarioQ() async {
    final u = await adminUsuario();
    return Uri.encodeQueryComponent(u);
  }

  Future<List<Map<String, dynamic>>> cierreGeneralDiarios() async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/cierre-general/diarios/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> cierreGeneralDiarioDetalle(int id) async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/cierre-general/diarios/$id/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {};
  }

  Future<List<Map<String, dynamic>>> cierreGeneralList() async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/cierre-general/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> cierreGeneralGet(int id) async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/cierre-general/$id/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {};
  }

  Future<Map<String, dynamic>> cierreGeneralCrear({
    required List<int> idsCierres,
    String titulo = '',
    String observacion = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/cierre-general/', {
      'usuario': usuario,
      'ids_cierres': idsCierres,
      'titulo': titulo,
      'observacion': observacion,
    });
    ApiClient.invalidate('/cierre-general/');
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> cierreGeneralChecklist({
    required int cierreId,
    required int cierreTurnoId,
    required Map<String, bool> checklist,
    String notaAdmin = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/cierre-general/$cierreId/checklist/', {
      'usuario': usuario,
      'cierre_turno_id': cierreTurnoId,
      'checklist': checklist,
      'nota_admin': notaAdmin,
    });
    ApiClient.invalidate('/cierre-general/');
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> cierreGeneralConsolidar(int cierreId) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/cierre-general/$cierreId/consolidar/', {
      'usuario': usuario,
    });
    ApiClient.invalidate('/cierre-general/');
    ApiClient.invalidate('/provision-admin/');
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> cierreGeneralAnular(
    int cierreId, {
    String motivo = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/cierre-general/$cierreId/anular/', {
      'usuario': usuario,
      'motivo': motivo,
    });
    ApiClient.invalidate('/cierre-general/');
    ApiClient.invalidate('/provision-admin/');
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> provisionAdminResumen() async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/provision-admin/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'saldo_pendiente': 0,
      'porcentaje': 30,
      'multiplo_redondeo': 10000,
      'historial': <dynamic>[],
    };
  }

  Future<Map<String, dynamic>> provisionAdminPorCierre(int cierreGeneralId) async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/provision-admin/$cierreGeneralId/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {};
  }

  Future<Map<String, dynamic>> bolsilloProveedoresResumen() async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/bolsillo-proveedores/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'saldos': {'efectivo': 0, 'nequi': 0, 'datafono': 0, 'total': 0},
      'movimientos': <dynamic>[],
      'integridad_ok': true,
    };
  }

  Future<Map<String, dynamic>> bolsilloProveedoresPago({
    required String proveedor,
    required double total,
    required List<Map<String, dynamic>> origenes,
    String referencia = '',
    String observacion = '',
    bool aCredito = false,
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/api/v1/bolsillo-proveedores/pago/', {
      'usuario': usuario,
      'proveedor': proveedor,
      'proveedor_nombre': proveedor,
      'total': total,
      'origenes': origenes,
      'referencia': referencia,
      'observacion': observacion,
      'a_credito': aCredito,
    });
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> bolsilloProveedoresObligacion({
    required String proveedor,
    required double total,
    String referencia = '',
    String observacion = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/api/v1/bolsillo-proveedores/obligacion/', {
      'usuario': usuario,
      'proveedor': proveedor,
      'proveedor_nombre': proveedor,
      'total': total,
      'referencia': referencia,
      'observacion': observacion,
    });
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> bolsilloProveedoresReclasificar({
    required String metodoOrigen,
    required String metodoDestino,
    required double monto,
    String referencia = '',
    String observacion = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/api/v1/bolsillo-proveedores/reclasificar/', {
      'usuario': usuario,
      'metodo_origen': metodoOrigen,
      'metodo_destino': metodoDestino,
      'monto': monto,
      'referencia': referencia,
      'observacion': observacion,
    });
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> provisionObligacionesResumen() async {
    final u = await _usuarioQ();
    final data = await ApiClient.tryGet(
      '/provision-obligaciones/?usuario=$u',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'saldos': {
        'dinero_real': 0,
        'dinero_comprometido': 0,
        'disponible': 0,
      },
      'empleados': {'reserva_diaria': 0, 'empleados': <dynamic>[]},
      'obligaciones': <dynamic>[],
      'por_tipo': <String, dynamic>{},
      'movimientos': <dynamic>[],
    };
  }

  Future<Map<String, dynamic>> provisionObligacionesEmpleado({
    required String nombre,
    required double salarioMensual,
    String observacion = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/api/v1/provision-obligaciones/empleado/', {
      'usuario': usuario,
      'nombre': nombre,
      'salario_mensual': salarioMensual,
      'observacion': observacion,
    });
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> provisionObligacionesCrear({
    required String tipo,
    required String nombre,
    required double valor,
    String descripcion = '',
    String categoria = '',
    String observacion = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/api/v1/provision-obligaciones/obligacion/', {
      'usuario': usuario,
      'tipo': tipo,
      'nombre': nombre,
      'valor': valor,
      'descripcion': descripcion,
      'categoria': categoria.isEmpty ? tipo : categoria,
      'observacion': observacion,
    });
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> provisionObligacionesPagar(
    int obligacionId, {
    String observacion = '',
  }) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson(
      '/api/v1/provision-obligaciones/obligacion/$obligacionId/pagar/',
      {'usuario': usuario, 'observacion': observacion},
    );
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> provisionObligacionesNomina({String observacion = ''}) async {
    final usuario = await adminUsuario();
    final data = await ApiClient.postJson('/api/v1/provision-obligaciones/nomina/', {
      'usuario': usuario,
      'observacion': observacion,
    });
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> reportesAdminDashboard({
    String preset = 'mes',
    String? desde,
    String? hasta,
    int? vendedorId,
    String? categoria,
    String? proveedor,
    String? medioPago,
    int? productoId,
  }) async {
    final u = await _usuarioQ();
    final params = <String>['usuario=$u', 'preset=${Uri.encodeQueryComponent(preset)}'];
    if (desde != null && desde.isNotEmpty) {
      params.add('desde=${Uri.encodeQueryComponent(desde)}');
    }
    if (hasta != null && hasta.isNotEmpty) {
      params.add('hasta=${Uri.encodeQueryComponent(hasta)}');
    }
    if (vendedorId != null) params.add('vendedor_id=$vendedorId');
    if (categoria != null && categoria.isNotEmpty) {
      params.add('categoria=${Uri.encodeQueryComponent(categoria)}');
    }
    if (proveedor != null && proveedor.isNotEmpty) {
      params.add('proveedor=${Uri.encodeQueryComponent(proveedor)}');
    }
    if (medioPago != null && medioPago.isNotEmpty) {
      params.add('medio_pago=${Uri.encodeQueryComponent(medioPago)}');
    }
    if (productoId != null) params.add('producto_id=$productoId');
    final data = await ApiClient.tryGet(
      '/reportes-admin/?${params.join('&')}',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'ventas': {'total': 0, 'tickets': 0, 'por_medio': {}, 'serie_diaria': []},
      'bolsillos': {
        'administrativo': {},
        'proveedores': {'efectivo': 0, 'nequi': 0, 'datafono': 0, 'total': 0},
        'excluidos': [
          {'nombre': 'Datafono', 'razon': 'Medio de pago, no bolsillo'},
        ],
      },
      'movimientos_proveedores': <dynamic>[],
      'cierres': {'diarios': [], 'generales': []},
      'alertas': <dynamic>[],
    };
  }

  Future<Map<String, dynamic>> cierreMensual({int? mes, int? anio}) async {
    final now = DateTime.now();
    final q = '?mes=${mes ?? now.month}&anio=${anio ?? now.year}';
    final data = await ApiClient.tryGet(
      '/comando/cierre-mensual/$q',
      ttl: Duration.zero,
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'mes': mes ?? now.month,
      'anio': anio ?? now.year,
      'cerrado': false,
      'pl': {},
      'recaudo': {},
      'bolsillos': {},
      'dias': <dynamic>[],
    };
  }

  Future<Map<String, dynamic>> cerrarMes({
    required int mes,
    required int anio,
  }) async {
    final data = await ApiClient.postJson(
      '/comando/cierre-mensual/',
      {'mes': mes, 'anio': anio},
    );
    ApiClient.invalidate();
    return Map<String, dynamic>.from(data as Map);
  }

  Future<Map<String, dynamic>> rentabilidad({int dias = 30}) async {
    final data = await ApiClient.tryGet(
      '/comando/rentabilidad/?dias=$dias',
      ttl: const Duration(seconds: 20),
    );
    if (data is Map) return Map<String, dynamic>.from(data);
    return {
      'dias': dias,
      'por_presentacion': <dynamic>[],
      'por_categoria': <dynamic>[],
      'top_productos': <dynamic>[],
    };
  }

  Future<Map<String, dynamic>> fefo({String laboratorio = ''}) async {
    final q = laboratorio.isEmpty ? '' : '?laboratorio=$laboratorio';
    final data = await ApiClient.tryGet('/comando/fefo/$q', ttl: Duration.zero);
    if (data is Map) return Map<String, dynamic>.from(data);
    return {'vencidos': 0, 'd30': 0, 'd60': 0, 'd90': 0, 'items': <dynamic>[]};
  }

  Future<List<Map<String, dynamic>>> liveSales() async {
    final data = await ApiClient.tryGet(
      '/comando/live-sales/?limit=20',
      ttl: Duration.zero,
    );
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }
}
