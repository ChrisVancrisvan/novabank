from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from datetime import datetime
import uuid
import os
import math


# ─────────────────────────────────────────
#  PALETA
# ─────────────────────────────────────────
INDIGO      = colors.HexColor("#4F46E5")
INDIGO_DARK = colors.HexColor("#3730A3")
INDIGO_LIGHT= colors.HexColor("#EEF2FF")
EMERALD     = colors.HexColor("#10B981")
EMERALD_BG  = colors.HexColor("#D1FAE5")
SLATE_900   = colors.HexColor("#0F172A")
SLATE_700   = colors.HexColor("#334155")
SLATE_500   = colors.HexColor("#64748B")
SLATE_200   = colors.HexColor("#E2E8F0")
SLATE_100   = colors.HexColor("#F1F5F9")
WHITE       = colors.HexColor("#FFFFFF")


def rounded_rect(c, x, y, w, h, r, fill_color=None, stroke_color=None, stroke_width=1):
    """Dibuja un rectángulo con esquinas redondeadas."""
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - 2*r, y, x + w, y + 2*r, 270, 90)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w - 2*r, y + h - 2*r, x + w, y + h, 0, 90)
    p.lineTo(x + r, y + h)
    p.arcTo(x, y + h - 2*r, x + 2*r, y + h, 90, 90)
    p.lineTo(x, y + r)
    p.arcTo(x, y, x + 2*r, y + 2*r, 180, 90)
    p.close()

    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)

    if fill_color and stroke_color:
        c.drawPath(p, fill=1, stroke=1)
    elif fill_color:
        c.drawPath(p, fill=1, stroke=0)
    elif stroke_color:
        c.drawPath(p, fill=0, stroke=1)


def draw_gradient_header(c, width, height, header_h=210):
    """Fondo degradado del header usando franjas horizontales."""
    steps = 60
    for i in range(steps):
        t = i / steps
        r = int(79  + (55  - 79)  * t)
        g = int(70  + (48  - 70)  * t)
        b = int(229 + (163 - 229) * t)
        c.setFillColorRGB(r/255, g/255, b/255)
        band_h = header_h / steps
        c.rect(0, height - header_h + i * band_h, width, band_h + 1, fill=1, stroke=0)


def draw_circle_decoration(c, width, height, header_h):
    """Círculos decorativos semitransparentes en el header."""
    c.saveState()
    c.setFillColorRGB(1, 1, 1, 0.06)
    c.circle(width - 60, height - 30, 120, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1, 0.04)
    c.circle(50, height - header_h + 40, 90, fill=1, stroke=0)
    c.restoreState()


def generate_transfer_pdf(
    user_id,
    amount,
    from_account,
    to_account,
    new_source_balance,
    new_target_balance
):
    os.makedirs("vouchers", exist_ok=True)

    folio = str(uuid.uuid4())[:8].upper()
    filename = f"vouchers/voucher_{folio}.pdf"

    W, H = letter
    c = canvas.Canvas(filename, pagesize=letter)

    # ── Fondo base ──────────────────────────────────────────
    c.setFillColor(SLATE_100)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Header con degradado ─────────────────────────────────
    HEADER_H = 220
    draw_gradient_header(c, W, H, HEADER_H)
    draw_circle_decoration(c, W, H, HEADER_H)

    # ── Logo / Nombre banco ──────────────────────────────────
    c.saveState()
    # Ícono banco (círculo blanco con letra N)
    icon_x, icon_y = 50, H - 60
    c.setFillColor(WHITE)
    c.circle(icon_x, icon_y, 18, fill=1, stroke=0)
    c.setFillColor(INDIGO)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(icon_x, icon_y - 5, "N")

    # Nombre banco
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(76, H - 53, "NovaBank")
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(1, 1, 1, 0.75)
    c.drawString(76, H - 68, "AI Banking")
    c.restoreState()

    # ── Título central del header ────────────────────────────
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(W / 2, H - 105, "Comprobante de Transferencia")

    # Badge "Exitosa"
    badge_w, badge_h = 160, 28
    badge_x = (W - badge_w) / 2
    badge_y = H - 148
    rounded_rect(c, badge_x, badge_y, badge_w, badge_h, 14,
                 fill_color=colors.HexColor("#ECFDF5"))
    c.setFillColor(EMERALD)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, badge_y + 8, "✓  Transferencia Exitosa")

    # Monto grande
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(W / 2, H - 205, f"${amount:,.2f}")
    c.setFont("Helvetica", 13)
    c.setFillColorRGB(1, 1, 1, 0.70)
    c.drawCentredString(W / 2, H - 220, "MXN")

    # ── Tarjeta blanca principal ──────────────────────────────
    card_margin = 35
    card_x = card_margin
    card_y = 100
    card_w = W - 2 * card_margin
    card_h = H - HEADER_H - card_y - 10
    rounded_rect(c, card_x, card_y, card_w, card_h, 14,
                 fill_color=WHITE,
                 stroke_color=SLATE_200, stroke_width=1)

    # ── Sección: Detalle de la operación ─────────────────────
    section_x = card_x + 28
    section_y = card_y + card_h - 50

    c.setFillColor(SLATE_700)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(section_x, section_y, "DETALLE DE LA OPERACIÓN")

    # Línea separadora
    c.setStrokeColor(SLATE_200)
    c.setLineWidth(1)
    c.line(section_x, section_y - 8, card_x + card_w - 28, section_y - 8)

    # ── Filas de datos ────────────────────────────────────────
    rows = [
        ("Folio",            folio,                              None),
        ("Fecha y hora",     datetime.now().strftime("%d %b %Y  •  %H:%M hrs"), None),
        ("Usuario",          user_id,                            None),
        ("Cuenta origen",    from_account,                       None),
        ("Cuenta destino",   to_account,                         None),
    ]

    row_h = 42
    start_y = section_y - 42
    col_label = section_x
    col_value = card_x + card_w / 2 - 10

    for i, (label, value, _) in enumerate(rows):
        ry = start_y - i * row_h
        # Fondo alterno
        if i % 2 == 0:
            rounded_rect(c, card_x + 12, ry - 10, card_w - 24, row_h - 4, 6,
                         fill_color=SLATE_100)
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 10)
        c.drawString(col_label, ry + 8, label)
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(col_value, ry + 8, str(value))

    # ── Sección saldos ────────────────────────────────────────
    saldo_y = start_y - len(rows) * row_h - 18

    c.setStrokeColor(SLATE_200)
    c.setLineWidth(1)
    c.line(section_x, saldo_y + 14, card_x + card_w - 28, saldo_y + 14)

    c.setFillColor(SLATE_700)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(section_x, saldo_y, "SALDOS ACTUALIZADOS")

    gap = 16
    box_w = (card_w - 56 - gap) / 2
    box_y = saldo_y - 68
    box_h = 56

    # Caja origen
    rounded_rect(c, section_x, box_y, box_w, box_h, 8,
                 fill_color=INDIGO_LIGHT, stroke_color=colors.HexColor("#C7D2FE"), stroke_width=1)
    c.setFillColor(INDIGO)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(section_x + 12, box_y + box_h - 18, "SALDO ORIGEN")
    c.setFont("Helvetica-Bold", 17)
    c.drawString(section_x + 12, box_y + 10, f"${new_source_balance:,.2f}")

    # Caja destino
    dest_x = section_x + box_w + gap
    rounded_rect(c, dest_x, box_y, box_w, box_h, 8,
                 fill_color=EMERALD_BG, stroke_color=colors.HexColor("#6EE7B7"), stroke_width=1)
    c.setFillColor(EMERALD)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(dest_x + 12, box_y + box_h - 18, "SALDO DESTINO")
    c.setFont("Helvetica-Bold", 17)
    c.drawString(dest_x + 12, box_y + 10, f"${new_target_balance:,.2f}")

    # ── Footer dentro de la tarjeta ───────────────────────────
    footer_y = card_y + 20
    c.setFillColor(SLATE_500)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(W / 2, footer_y,
        "Este comprobante fue generado automáticamente por NovaBank AI  •  Folio: " + folio)

    # ── Línea decorativa inferior de la página ────────────────
    c.setFillColor(INDIGO)
    c.rect(0, 0, W, 6, fill=1, stroke=0)

    c.save()
    return {"folio": folio, "pdf_path": filename}

# =========================
# PDF RECARGA CELULAR
# =========================

def generate_recharge_pdf(

    user_id,

    phone_number,

    amount,

    new_balance
):


    os.makedirs(
        "vouchers",
        exist_ok=True
    )


    folio = str(uuid.uuid4())[:8].upper()


    filename = (
        f"vouchers/recharge_{folio}.pdf"
    )


    W, H = letter

    c = canvas.Canvas(
        filename,
        pagesize=letter
    )


    # =========================
    # FONDO
    # =========================

    c.setFillColor(SLATE_100)

    c.rect(
        0,
        0,
        W,
        H,
        fill=1,
        stroke=0
    )


    # =========================
    # HEADER
    # =========================

    HEADER_H = 220

    draw_gradient_header(
        c,
        W,
        H,
        HEADER_H
    )

    draw_circle_decoration(
        c,
        W,
        H,
        HEADER_H
    )


    # =========================
    # LOGO
    # =========================

    icon_x, icon_y = 50, H - 60

    c.setFillColor(WHITE)

    c.circle(
        icon_x,
        icon_y,
        18,
        fill=1,
        stroke=0
    )

    c.setFillColor(INDIGO)

    c.setFont(
        "Helvetica-Bold",
        16
    )

    c.drawCentredString(
        icon_x,
        icon_y - 5,
        "N"
    )


    c.setFillColor(WHITE)

    c.setFont(
        "Helvetica-Bold",
        22
    )

    c.drawString(
        76,
        H - 53,
        "NovaBank"
    )


    # =========================
    # TÍTULO
    # =========================

    c.setFillColor(WHITE)

    c.setFont(
        "Helvetica-Bold",
        26
    )

    c.drawCentredString(
        W / 2,
        H - 105,
        "Comprobante de Recarga"
    )


    # =========================
    # STATUS
    # =========================

    badge_w, badge_h = 160, 28

    badge_x = (W - badge_w) / 2

    badge_y = H - 148


    rounded_rect(

        c,

        badge_x,

        badge_y,

        badge_w,

        badge_h,

        14,

        fill_color=colors.HexColor(
            "#ECFDF5"
        )
    )


    c.setFillColor(EMERALD)

    c.setFont(
        "Helvetica-Bold",
        12
    )

    c.drawCentredString(
        W / 2,
        badge_y + 8,
        "✓ Recarga Exitosa"
    )


    # =========================
    # MONTO
    # =========================

    c.setFillColor(WHITE)

    c.setFont(
        "Helvetica-Bold",
        44
    )

    c.drawCentredString(
        W / 2,
        H - 205,
        f"${amount:,.2f}"
    )


    c.setFont(
        "Helvetica",
        13
    )

    c.drawCentredString(
        W / 2,
        H - 220,
        "MXN"
    )


    # =========================
    # TARJETA
    # =========================

    card_margin = 35

    card_x = card_margin

    card_y = 100

    card_w = W - 2 * card_margin

    card_h = H - HEADER_H - card_y - 10


    rounded_rect(

        c,

        card_x,

        card_y,

        card_w,

        card_h,

        14,

        fill_color=WHITE,

        stroke_color=SLATE_200,

        stroke_width=1
    )


    # =========================
    # DETALLES
    # =========================

    rows = [

        ("Folio", folio),

        (
            "Fecha y hora",

            datetime.now().strftime(
                "%d %b %Y • %H:%M hrs"
            )
        ),

        ("Usuario", user_id),

        ("Número", phone_number),

        (
            "Nuevo saldo",

            f"${new_balance:,.2f}"
        )
    ]


    section_x = card_x + 28

    section_y = card_y + card_h - 50


    c.setFillColor(SLATE_700)

    c.setFont(
        "Helvetica-Bold",
        11
    )

    c.drawString(
        section_x,
        section_y,
        "DETALLE DE RECARGA"
    )


    start_y = section_y - 42

    row_h = 48


    for i, (label, value) in enumerate(rows):


        ry = start_y - i * row_h


        if i % 2 == 0:

            rounded_rect(

                c,

                card_x + 12,

                ry - 10,

                card_w - 24,

                row_h - 4,

                6,

                fill_color=SLATE_100
            )


        c.setFillColor(SLATE_500)

        c.setFont(
            "Helvetica",
            10
        )

        c.drawString(
            section_x,
            ry + 8,
            label
        )


        c.setFillColor(SLATE_900)

        c.setFont(
            "Helvetica-Bold",
            11
        )

        c.drawString(
            card_x + card_w / 2 - 10,
            ry + 8,
            str(value)
        )


    # =========================
    # FOOTER
    # =========================

    footer_y = card_y + 20

    c.setFillColor(SLATE_500)

    c.setFont(
        "Helvetica",
        8.5
    )

    c.drawCentredString(

        W / 2,

        footer_y,

        f"NovaBank AI • Folio: {folio}"
    )


    c.setFillColor(INDIGO)

    c.rect(
        0,
        0,
        W,
        6,
        fill=1,
        stroke=0
    )


    c.save()


    return {

        "folio":
        folio,

        "pdf_path":
        filename
    }


# ── Test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    result = generate_transfer_pdf(
        user_id="usr_92847",
        amount=15_500.00,
        from_account="****  4821",
        to_account="****  9037",
        new_source_balance=84_500.00,
        new_target_balance=32_750.50,
    )
    print("PDF generado:", result["pdf_path"])
    print("Folio:", result["folio"])