import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/api_service.dart';
import 'chat_screen.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  final String userId;

  const HomeScreen({
    super.key,
    required this.userId,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Map<String, dynamic>> _accounts = [];

  bool _loading = true;
  bool _balancesVisible = true;

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    setState(() => _loading = true);

    final accounts = await ApiService.getAccounts(widget.userId);

    setState(() {
      _accounts = accounts;
      _loading = false;
    });
  }

  String _formatProductName(String raw) {
    const names = {
      'cuenta_debito': 'Cuenta Débito',
      'cuenta_negocios': 'Cuenta Negocios',
      'inversion_hey': 'Inversión',
      'tarjeta_credito_hey': 'Tarjeta Crédito',
    };

    return names[raw.toLowerCase()] ?? raw;
  }

  IconData _productIcon(String raw) {
    if (raw.contains('debito')) {
      return Icons.credit_card_rounded;
    }

    if (raw.contains('negocio')) {
      return Icons.business_center_rounded;
    }

    if (raw.contains('inversion')) {
      return Icons.trending_up_rounded;
    }

    if (raw.contains('credito')) {
      return Icons.payment_rounded;
    }

    return Icons.account_balance_wallet_rounded;
  }

  Color _productColor(int index) {
    const colors = [
      Color(0xFF4F46E5),
      Color(0xFF10B981),
      Color(0xFFF59E0B),
      Color(0xFFEF4444),
    ];

    return colors[index % colors.length];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A1A),
      body: Stack(
        children: [
          Positioned(
            top: -60,
            right: -60,
            child: Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    const Color(
                      0xFF4F46E5,
                    ).withValues(alpha: 0.25),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          SafeArea(
            child: RefreshIndicator(
              onRefresh: _loadAccounts,
              color: const Color(0xFF4F46E5),
              backgroundColor: const Color(0xFF1A1A2E),
              child: CustomScrollView(
                slivers: [
                  // HEADER
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(
                        24,
                        24,
                        24,
                        0,
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Hola 👋',
                                style: GoogleFonts.inter(
                                  color: Colors.white54,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                widget.userId,
                                style: GoogleFonts.syne(
                                  color: Colors.white,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                          Row(
                            children: [
                              // VISIBILIDAD
                              GestureDetector(
                                onTap: () {
                                  setState(() {
                                    _balancesVisible = !_balancesVisible;
                                  });
                                },
                                child: Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: Colors.white.withValues(
                                      alpha: 0.06,
                                    ),
                                    borderRadius: BorderRadius.circular(
                                      12,
                                    ),
                                  ),
                                  child: Icon(
                                    _balancesVisible
                                        ? Icons.visibility_outlined
                                        : Icons.visibility_off_outlined,
                                    color: Colors.white54,
                                    size: 20,
                                  ),
                                ),
                              ),

                              const SizedBox(width: 10),

                              // LOGOUT
                              GestureDetector(
                                onTap: () {
                                  Navigator.pushReplacement(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => const LoginScreen(),
                                    ),
                                  );
                                },
                                child: Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: Colors.white.withValues(
                                      alpha: 0.06,
                                    ),
                                    borderRadius: BorderRadius.circular(
                                      12,
                                    ),
                                  ),
                                  child: const Icon(
                                    Icons.logout_rounded,
                                    color: Colors.white54,
                                    size: 20,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ).animate().fadeIn(duration: 500.ms),
                    ),
                  ),

                  const SliverToBoxAdapter(
                    child: SizedBox(height: 32),
                  ),

                  // TITULO
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                      ),
                      child: Text(
                        'Mis cuentas',
                        style: GoogleFonts.syne(
                          color: Colors.white70,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.4,
                        ),
                      ).animate().fadeIn(delay: 200.ms),
                    ),
                  ),

                  const SliverToBoxAdapter(
                    child: SizedBox(height: 16),
                  ),

                  // CUENTAS
                  _loading
                      ? const SliverToBoxAdapter(
                          child: Center(
                            child: Padding(
                              padding: EdgeInsets.all(
                                40,
                              ),
                              child: CircularProgressIndicator(
                                color: Color(
                                  0xFF4F46E5,
                                ),
                                strokeWidth: 2,
                              ),
                            ),
                          ),
                        )
                      : _accounts.isEmpty
                          ? SliverToBoxAdapter(
                              child: Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(
                                    40,
                                  ),
                                  child: Text(
                                    'No se encontraron cuentas',
                                    style: GoogleFonts.inter(
                                      color: Colors.white38,
                                    ),
                                  ),
                                ),
                              ),
                            )
                          : SliverList(
                              delegate: SliverChildBuilderDelegate(
                                (context, i) {
                                  return Padding(
                                    padding: const EdgeInsets.fromLTRB(
                                      24,
                                      0,
                                      24,
                                      14,
                                    ),
                                    child: _AccountCard(
                                      name: _formatProductName(
                                        _accounts[i]['tipo_producto'] ?? '',
                                      ),
                                      balance:
                                          (_accounts[i]['saldo_actual'] as num?)
                                                  ?.toDouble() ??
                                              0,
                                      icon: _productIcon(
                                        _accounts[i]['tipo_producto'] ?? '',
                                      ),
                                      color: _productColor(i),
                                      visible: _balancesVisible,
                                      index: i,
                                    ),
                                  );
                                },
                                childCount: _accounts.length,
                              ),
                            ),

                  const SliverToBoxAdapter(
                    child: SizedBox(height: 32),
                  ),

                  // CHATBOT
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                      ),
                      child: _ChatbotButton(
                        userId: widget.userId,
                      ),
                    ),
                  ),

                  const SliverToBoxAdapter(
                    child: SizedBox(height: 40),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// =========================
// ACCOUNT CARD
// =========================

class _AccountCard extends StatelessWidget {
  final String name;
  final double balance;
  final IconData icon;
  final Color color;
  final bool visible;
  final int index;

  const _AccountCard({
    required this.name,
    required this.balance,
    required this.icon,
    required this.color,
    required this.visible,
    required this.index,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF13131F),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.06),
        ),
      ),
      child: Row(
        children: [
          // ICONO
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(
                14,
              ),
            ),
            child: Icon(
              icon,
              color: color,
              size: 22,
            ),
          ),

          const SizedBox(width: 16),

          // INFO
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: GoogleFonts.inter(
                    color: Colors.white60,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                visible
                    ? Text(
                        '\$${balance.toStringAsFixed(2).replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')} MXN',
                        style: GoogleFonts.syne(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                        ),
                      )
                    : Text(
                        '•••••• MXN',
                        style: GoogleFonts.syne(
                          color: Colors.white54,
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 4,
                        ),
                      ),
              ],
            ),
          ),

          const Icon(
            Icons.arrow_forward_ios_rounded,
            color: Colors.white24,
            size: 14,
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(
          delay: Duration(
            milliseconds: 300 + index * 100,
          ),
        )
        .slideX(begin: 0.1);
  }
}

// =========================
// BOTON CHATBOT
// =========================

class _ChatbotButton extends StatelessWidget {
  final String userId;

  const _ChatbotButton({
    required this.userId,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ChatScreen(userId: userId),
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [
              Color(0xFF4F46E5),
              Color(0xFF7C3AED),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: const Color(
                0xFF4F46E5,
              ).withValues(alpha: 0.35),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: Colors.white.withValues(
                  alpha: 0.15,
                ),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.auto_awesome_rounded,
                color: Colors.white,
                size: 22,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'NovaBank AI',
                    style: GoogleFonts.syne(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Pregúntame lo que necesites',
                    style: GoogleFonts.inter(
                      color: Colors.white70,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.arrow_forward_ios_rounded,
              color: Colors.white70,
              size: 16,
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 700.ms).slideY(begin: 0.15);
  }
}
