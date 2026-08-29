from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .form import SaleCancelForm
from inventory.models import StockMovement
from inventory.services import register_stock_movement
from products.models import Product

from .models import MONEY_STEP, Sale, SaleItem

MAX_SALE_ITEMS = 100


def parse_decimal(value, *, field_name, error_message):
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValidationError({field_name: error_message}) from error
    if not decimal_value.is_finite():
        raise ValidationError({field_name: error_message})
    return decimal_value


def generate_sale_number():
    date_part = timezone.localdate().strftime("%Y%m%d")
    random_part = uuid4().hex[:10].upper()
    return f"S-{date_part}-{random_part}"


@transaction.atomic
def complete_sale(*, store, cashier, raw_items, payment_method, amount_received=None):
    """Savdoni yakunlash – mavjud funksiya (toʻliq holda saqlang)"""
    if cashier is None:
        raise ValidationError({"cashier": "Kassir aniqlanmadi."})
    if cashier.store_id != store.pk:
        raise ValidationError({"cashier": "Kassir ushbu marketga tegishli emas."})

    if not isinstance(raw_items, list):
        raise ValidationError({"items": "Savat ma’lumotlari noto‘g‘ri."})
    if not raw_items:
        raise ValidationError({"items": "Savat bo‘sh."})
    if len(raw_items) > MAX_SALE_ITEMS:
        raise ValidationError(
            {"items": f"Bitta savdoda ko‘pi bilan {MAX_SALE_ITEMS} xil mahsulot bo‘lishi mumkin."}
        )

    combined_items = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValidationError({"items": "Savatdagi mahsulot ma’lumoti noto‘g‘ri."})

        raw_product_id = raw_item.get("product_id")
        if isinstance(raw_product_id, bool):
            raise ValidationError({"items": "Mahsulot identifikatori noto‘g‘ri."})
        try:
            product_id = int(raw_product_id)
        except (TypeError, ValueError):
            raise ValidationError({"items": "Mahsulot identifikatori noto‘g‘ri."})
        if product_id <= 0:
            raise ValidationError({"items": "Mahsulot identifikatori noto‘g‘ri."})

        quantity = parse_decimal(
            raw_item.get("quantity"),
            field_name="items",
            error_message="Mahsulot miqdori noto‘g‘ri."
        )
        if quantity <= 0:
            raise ValidationError({"items": "Mahsulot miqdori 0 dan katta bo‘lishi kerak."})

        combined_items[product_id] = combined_items.get(product_id, Decimal("0")) + quantity

    product_ids = sorted(combined_items.keys())
    products = list(
        Product.objects.select_for_update()
        .filter(pk__in=product_ids, store=store, is_active=True)
        .order_by("pk")
    )
    product_map = {p.pk: p for p in products}

    if len(product_map) != len(product_ids):
        raise ValidationError({"items": "Savatdagi mahsulotlardan biri topilmadi yoki arxivlangan."})

    prepared_items = []
    total = Decimal("0")

    for product_id in product_ids:
        product = product_map[product_id]
        quantity = combined_items[product_id]

        stock_field = product._meta.get_field("stock_quantity")
        try:
            quantity = stock_field.clean(quantity, product)
        except ValidationError as error:
            raise ValidationError(
                {"items": [f"{product.name}: {msg}" for msg in error.messages]}
            )

        if product.unit == Product.Unit.PIECE and quantity % Decimal("1") != 0:
            raise ValidationError(
                {"items": f"{product.name}: dona mahsulot miqdori butun son bo‘lishi kerak."}
            )

        if quantity > product.stock_quantity:
            raise ValidationError(
                {"items": f"{product.name} omborda yetarli emas. Mavjud: {product.stock_quantity} {product.get_unit_display()}."}
            )

        line_total = (quantity * product.sale_price).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
        total += line_total
        prepared_items.append({"product": product, "quantity": quantity, "line_total": line_total})

    total = total.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    if total <= 0:
        raise ValidationError({"items": "Savdo summasi 0 dan katta bo‘lishi kerak."})

    if payment_method not in Sale.PaymentMethod.values:
        raise ValidationError({"payment_method": "Noto‘g‘ri to‘lov turi."})

    if payment_method == Sale.PaymentMethod.CASH:
        amount_received = parse_decimal(
            amount_received,
            field_name="amount_received",
            error_message="Mijoz bergan summani kiriting."
        )
        received_field = Sale._meta.get_field("amount_received")
        try:
            amount_received = received_field.clean(amount_received, None)
        except ValidationError as error:
            raise ValidationError({"amount_received": error.messages})

        amount_received = amount_received.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
        if amount_received < total:
            missing_amount = (total - amount_received).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
            raise ValidationError(
                {"amount_received": f"Mijoz bergan pul yetarli emas. Yana {missing_amount} som kerak."}
            )
        change_amount = (amount_received - total).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    else:
        amount_received = total
        change_amount = Decimal("0")

    sale = Sale(
        store=store,
        cashier=cashier,
        sale_number=generate_sale_number(),
        status=Sale.Status.COMPLETED,
        payment_method=payment_method,
        total=total,
        amount_received=amount_received,
        change_amount=change_amount,
    )
    sale.full_clean()
    sale.save()

    for prepared_item in prepared_items:
        product = prepared_item["product"]
        quantity = prepared_item["quantity"]
        sale_item = SaleItem(
            sale=sale,
            product=product,
            product_name=product.name,
            barcode=product.barcode or "",
            unit=product.unit,
            quantity=quantity,
            unit_price=product.sale_price,
            purchase_price=product.purchase_price,
            line_total=prepared_item["line_total"],
        )
        sale_item.full_clean()
        sale_item.save()

        register_stock_movement(
            store=store,
            product_id=product.pk,
            actor=cashier,
            movement_type=StockMovement.MovementType.SALE,
            quantity=quantity,
            note=f"{sale.sale_number} raqamli savdo."
        )

    return sale


@transaction.atomic
def cancel_sale(*, sale_id, store, actor, reason):
    """
    Savdoni bekor qilish:
    - statusni CANCELLED ga o‘zgartiradi
    - cancelled_by, cancelled_at, cancellation_reason maydonlarini to‘ldiradi
    - har bir mahsulotni omborga qaytaradi (IN movement)
    """
    try:
        sale = Sale.objects.select_for_update().get(pk=sale_id, store=store)
    except Sale.DoesNotExist:
        raise ValidationError("Savdo topilmadi.")

    if sale.status == Sale.Status.CANCELLED:
        raise ValidationError("Bu savdo allaqachon bekor qilingan.")

    if sale.status != Sale.Status.COMPLETED:
        raise ValidationError("Faqat yakunlangan savdolarni bekor qilish mumkin.")

    sale.status = Sale.Status.CANCELLED
    sale.cancelled_by = actor
    sale.cancelled_at = timezone.now()
    sale.cancellation_reason = reason
    sale.full_clean()
    sale.save()

    sale_items = SaleItem.objects.filter(sale=sale).select_related("product")
    for item in sale_items:
        register_stock_movement(
            store=store,
            product_id=item.product_id,
            actor=actor,
            movement_type=StockMovement.MovementType.IN,
            quantity=item.quantity,
            note=f"{sale.sale_number} savdosi bekor qilindi: {reason}"
        )

    return sale

@transaction.atomic
def cancel_sale(*, sale_id, store, actor, reason):
    try:
        sale = Sale.objects.select_for_update().get(pk=sale_id, store=store)
    except Sale.DoesNotExist:
        raise ValidationError("Savdo topilmadi.")

    if sale.status == Sale.Status.CANCELLED:
        raise ValidationError("Bu savdo allaqachon bekor qilingan.")
    if sale.status != Sale.Status.COMPLETED:
        raise ValidationError("Faqat yakunlangan savdolarni bekor qilish mumkin.")

    sale.status = Sale.Status.CANCELLED
    sale.cancelled_by = actor
    sale.cancelled_at = timezone.now()
    sale.cancellation_reason = reason
    sale.full_clean()
    sale.save()

    for item in SaleItem.objects.filter(sale=sale).select_related("product"):
        register_stock_movement(
            store=store,
            product_id=item.product_id,
            actor=actor,
            movement_type=StockMovement.MovementType.IN,   # yoki ADJUSTMENT
            quantity=item.quantity,
            note=f"{sale.sale_number} savdosi bekor qilindi: {reason}",
        )

    return sale