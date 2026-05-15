import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/api_service.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _userController = TextEditingController();

  final _passController = TextEditingController();

  bool _loading = false;
  bool _obscure = true;

  String? _error;

  Future<void> _login() async {
    final userId = _userController.text.trim();

    final pass = _passController.text.trim();

    if (userId.isEmpty || pass.isEmpty) {
      setState(() {
        _error = 'Ingresa usuario y contraseña';
      });

      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    final result = await ApiService.login(userId, pass);

    setState(() {
      _loading = false;
    });

    if (result['success'] == true) {
      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => HomeScreen(userId: userId),
        ),
      );
    } else {
      setState(() {
        _error = result['error'] ?? 'Error al iniciar sesión';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(
        0xFF0A0A1A,
      ),
      body: Stack(
        children: [
          // FONDO
          Positioned(
            top: -80,
            right: -80,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(
                      0xFF4F46E5,
                    ).withValues(alpha: 0.3),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),

          Positioned(
            bottom: -100,
            left: -60,
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(
                      0xFF10B981,
                    ).withValues(alpha: 0.2),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),

          // CONTENIDO
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // LOGO
                    Container(
                      width: 72,
                      height: 72,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [
                            Color(0xFF4F46E5),
                            Color(0xFF7C3AED),
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(
                          20,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(
                              0xFF4F46E5,
                            ).withValues(
                              alpha: 0.4,
                            ),
                            blurRadius: 24,
                            offset: const Offset(
                              0,
                              8,
                            ),
                          ),
                        ],
                      ),
                      child: Center(
                        child: Text(
                          'N',
                          style: GoogleFonts.syne(
                            fontSize: 36,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    )
                        .animate()
                        .fadeIn(
                          duration: 600.ms,
                        )
                        .slideY(begin: -0.2),

                    const SizedBox(height: 24),

                    Text(
                      'NovaBank',
                      style: GoogleFonts.syne(
                        fontSize: 32,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ).animate().fadeIn(
                          delay: 200.ms,
                        ),

                    const SizedBox(height: 6),

                    Text(
                      'Tu banco inteligente',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        color: Colors.white38,
                        letterSpacing: 1.2,
                      ),
                    ).animate().fadeIn(
                          delay: 300.ms,
                        ),

                    const SizedBox(height: 52),

                    // USUARIO
                    _buildInput(
                      controller: _userController,
                      label: 'Usuario',
                      icon: Icons.person_outline_rounded,
                    )
                        .animate()
                        .fadeIn(
                          delay: 400.ms,
                        )
                        .slideX(begin: -0.1),

                    const SizedBox(height: 16),

                    // PASSWORD
                    _buildInput(
                      controller: _passController,
                      label: 'Contraseña',
                      icon: Icons.lock_outline_rounded,
                      obscure: _obscure,
                      suffix: IconButton(
                        icon: Icon(
                          _obscure
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                          color: Colors.white38,
                          size: 20,
                        ),
                        onPressed: () {
                          setState(() {
                            _obscure = !_obscure;
                          });
                        },
                      ),
                    )
                        .animate()
                        .fadeIn(
                          delay: 500.ms,
                        )
                        .slideX(begin: 0.1),

                    if (_error != null) ...[
                      const SizedBox(
                        height: 16,
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(
                            0xFFEF4444,
                          ).withValues(
                            alpha: 0.1,
                          ),
                          borderRadius: BorderRadius.circular(
                            12,
                          ),
                          border: Border.all(
                            color: const Color(
                              0xFFEF4444,
                            ).withValues(
                              alpha: 0.3,
                            ),
                          ),
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.error_outline,
                              color: Color(
                                0xFFEF4444,
                              ),
                              size: 16,
                            ),
                            const SizedBox(
                              width: 8,
                            ),
                            Text(
                              _error!,
                              style: GoogleFonts.inter(
                                color: const Color(
                                  0xFFEF4444,
                                ),
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],

                    const SizedBox(height: 32),

                    // BOTON LOGIN
                    SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: ElevatedButton(
                        onPressed: _loading ? null : _login,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(
                            0xFF4F46E5,
                          ),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(
                              16,
                            ),
                          ),
                          elevation: 0,
                        ),
                        child: _loading
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2.5,
                                ),
                              )
                            : Text(
                                'Ingresar',
                                style: GoogleFonts.syne(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.5,
                                ),
                              ),
                      ),
                    )
                        .animate()
                        .fadeIn(
                          delay: 600.ms,
                        )
                        .slideY(begin: 0.2),

                    const SizedBox(height: 24),

                    Text(
                      'NovaBank AI • Versión 1.0',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: Colors.white24,
                      ),
                    ).animate().fadeIn(
                          delay: 800.ms,
                        ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInput({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    bool obscure = false,
    Widget? suffix,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(
          alpha: 0.05,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withValues(
            alpha: 0.08,
          ),
        ),
      ),
      child: TextField(
        controller: controller,
        obscureText: obscure,
        style: GoogleFonts.inter(
          color: Colors.white,
          fontSize: 15,
        ),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: GoogleFonts.inter(
            color: Colors.white38,
            fontSize: 14,
          ),
          prefixIcon: Icon(
            icon,
            color: Colors.white38,
            size: 20,
          ),
          suffixIcon: suffix,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 18,
          ),
          floatingLabelBehavior: FloatingLabelBehavior.never,
        ),
        onSubmitted: (_) => _login(),
      ),
    );
  }
}
