import 'dart:convert';
import 'package:http/http.dart' as http;

class _CacheEntry {
  final dynamic data;
  final DateTime at;
  _CacheEntry(this.data, this.at);
}

class ApiClient {
  static const baseUrl = 'https://api-production-b438.up.railway.app';
  static final Map<String, _CacheEntry> _cache = {};

  static Future<dynamic> getJson(
    String path, {
    Duration ttl = const Duration(seconds: 8),
  }) async {
    final url = path.startsWith('http') ? path : '$baseUrl$path';
    final now = DateTime.now();
    final hit = _cache[url];
    if (hit != null && now.difference(hit.at) < ttl) {
      return hit.data;
    }
    final response = await http.get(Uri.parse(url)).timeout(
      const Duration(seconds: 20),
    );
    if (response.statusCode != 200) {
      throw Exception('Error ${response.statusCode} al consultar $url');
    }
    final data = json.decode(response.body);
    _cache[url] = _CacheEntry(data, now);
    return data;
  }

  static Future<dynamic> tryGet(
    String path, {
    Duration ttl = const Duration(seconds: 6),
  }) async {
    try {
      return await getJson(path, ttl: ttl);
    } catch (_) {
      return null;
    }
  }

  static Future<dynamic> postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    final url = path.startsWith('http') ? path : '$baseUrl$path';
    final response = await http
        .post(
          Uri.parse(url),
          headers: {'Content-Type': 'application/json'},
          body: json.encode(body),
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Error ${response.statusCode}: ${response.body}');
    }
    if (response.body.isEmpty) return {'ok': true};
    return json.decode(response.body);
  }

  static void invalidate([String? path]) {
    if (path == null) {
      _cache.clear();
      return;
    }
    final url = path.startsWith('http') ? path : '$baseUrl$path';
    _cache.remove(url);
    _cache.removeWhere((key, _) => key.contains(path));
  }
}
