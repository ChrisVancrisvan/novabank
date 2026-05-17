import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

// IP de tu PC en la red WiFi local. Cámbiala antes de compilar el APK.
// En Windows: ejecuta `ipconfig` y busca "Dirección IPv4" (ej. 192.168.1.X)
// El backend debe correr con: uvicorn app:app --host 0.0.0.0 --port 8000
const String _localBackendIp = '192.168.1.70';

class ApiService {
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000';

    // Emulador Android usa 10.0.2.2 para acceder al localhost del PC.
    // Dispositivo físico usa la IP real de tu PC en la misma red WiFi.
    if (defaultTargetPlatform == TargetPlatform.android) {
      const isEmulator =
          bool.fromEnvironment('IS_EMULATOR', defaultValue: false);
      return isEmulator
          ? 'http://10.0.2.2:8000'
          : 'http://$_localBackendIp:8000';
    }

    return 'http://localhost:8000';
  }

  // =======================
  // LOGIN (simulado con user_id)
  // =======================
  static Future<Map<String, dynamic>> login(
    String userId,
    String password,
  ) async {
    try {
      // Verificamos que el usuario exista consultando su saldo
      final response = await http.post(
        Uri.parse('$baseUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'user_id': userId, 'message': 'consultar saldo'}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        // Si el bot responde con error de usuario, login falla
        if (data['bot_response'].toString().contains('sin cuentas')) {
          return {'success': false, 'error': 'Usuario no encontrado'};
        }
        return {'success': true};
      }
      return {'success': false, 'error': 'Error de conexión'};
    } catch (e) {
      return {'success': false, 'error': 'No se pudo conectar al servidor'};
    }
  }

  // =======================
  // OBTENER CUENTAS
  // =======================
  static Future<List<Map<String, dynamic>>> getAccounts(String userId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'user_id': userId, 'message': 'consultar saldo'}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final botResponse = data['bot_response'].toString();

        // Si tiene múltiples cuentas, parsear
        if (botResponse.contains('Producto:')) {
          return _parseAccounts(botResponse);
        }

        // Si tiene una sola cuenta, construir desde la respuesta
        return [
          {
            'tipo_producto': _extractProductType(botResponse),
            'saldo_actual': _extractBalance(botResponse),
          },
        ];
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  // =======================
  // CHAT
  // =======================
  static Future<String> sendMessage(String userId, String message) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'user_id': userId, 'message': message}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['bot_response'] ?? 'Sin respuesta';
      }
      return 'Error al conectar con el servidor';
    } catch (e) {
      return 'No se pudo conectar al servidor';
    }
  }

  // =======================
  // DESCARGAR PDF AL DISPOSITIVO
  // =======================
  static Future<String?> downloadPdf(String filename) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/vouchers/$filename'),
      );
      if (response.statusCode == 200) {
        final dir = await getApplicationDocumentsDirectory();
        final file = File('${dir.path}/$filename');
        await file.writeAsBytes(response.bodyBytes);
        return file.path;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  // =======================
  // HELPERS DE PARSEO
  // =======================
  static List<Map<String, dynamic>> _parseAccounts(String text) {
    final accounts = <Map<String, dynamic>>[];
    final lines = text.split('\n');

    String? tipo;
    double? saldo;

    for (final line in lines) {
      final l = line.trim();
      if (l.startsWith('Producto:')) {
        tipo = l.replaceFirst('Producto:', '').trim();
      } else if (l.startsWith('Saldo:')) {
        final raw =
            l.replaceFirst('Saldo:', '').replaceAll(RegExp(r'[^\d.]'), '');
        saldo = double.tryParse(raw);
      }
      if (tipo != null && saldo != null) {
        accounts.add({'tipo_producto': tipo, 'saldo_actual': saldo});
        tipo = null;
        saldo = null;
      }
    }
    return accounts;
  }

  static String _extractProductType(String text) {
    final match = RegExp(
      r'(cuenta_debito|cuenta_negocios|inversion_hey|tarjeta_credito_hey)',
      caseSensitive: false,
    ).firstMatch(text);
    return match?.group(0) ?? 'Cuenta';
  }

  static double _extractBalance(String text) {
    final match = RegExp(r'\$([\d,]+\.?\d*)').firstMatch(text);
    if (match != null) {
      return double.tryParse(match.group(1)!.replaceAll(',', '')) ?? 0.0;
    }
    return 0.0;
  }
}
