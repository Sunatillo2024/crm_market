from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from products.models import Product
from sales.models import Sale

from .models import StockMovement


@transaction.atomic
def register_stock_movement(
    *,
    store,
    product_id,
    actor,
    movement_type,
    quantity,
    note="",
    allow_inactive=False,
):
    if actor is None:
        raise ValidationError(
            {
                "created_by": (
                    "Ombor harakatini bajargan foydalanuvchi aniqlanmadi."
                ),
            }
        )

    if actor.store_id != store.pk:
        raise ValidationError(
            {
                "created_by": (
                    "Foydalanuvchi ushbu marketga tegishli emas."
                ),
            }
        )

    if movement_type not in StockMovement.MovementType.values:
        raise ValidationError(
            {
                "movement_type": (
                    "Noto‘g‘ri ombor harakati turi."
                ),
            }
        )

    try:
        quantity = Decimal(
            str(quantity),
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as error:
        raise ValidationError(
            {
                "quantity": (
                    "Miqdor noto‘g‘ri kiritilgan."
                ),
            }
        ) from error

    if not quantity.is_finite():
        raise ValidationError(
            {
                "quantity": (
                    "Miqdor noto‘g‘ri kiritilgan."
                ),
            }
        )

    product_query = Product.objects.select_for_update().filter(
        pk=product_id,
        store=store,
    )

    if not allow_inactive:
        product_query = product_query.filter(
            is_active=True,
        )

    try:
        product = product_query.get()
    except Product.DoesNotExist as error:
        raise ValidationError(
            {
                "product": (
                    "Mahsulot topilmadi yoki undan foydalanishga ruxsat yo‘q."
                ),
            }
        ) from error

    stock_field = product._meta.get_field(
        "stock_quantity",
    )

    try:
        quantity = stock_field.clean(
            quantity,
            product,
        )
    except ValidationError as error:
        raise ValidationError(
            {
                "quantity": error.messages,
            }
        ) from error

    if product.unit == Product.Unit.PIECE:
        if quantity % Decimal("1") != 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Dona mahsulot miqdori butun son bo‘lishi kerak."
                    ),
                }
            )

    quantity_before = product.stock_quantity

    if movement_type == StockMovement.MovementType.OPENING:
        if quantity <= 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Boshlang‘ich qoldiq 0 dan katta bo‘lishi kerak."
                    ),
                }
            )

        if quantity_before != 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Boshlang‘ich qoldiq faqat qoldig‘i 0 mahsulotga beriladi."
                    ),
                }
            )

        if StockMovement.objects.filter(
            product=product,
        ).exists():
            raise ValidationError(
                {
                    "product": (
                        "Ushbu mahsulot uchun ombor tarixi allaqachon mavjud."
                    ),
                }
            )

        quantity_after = quantity
        movement_quantity = quantity

    elif movement_type in {
        StockMovement.MovementType.IN,
        StockMovement.MovementType.SALE_CANCEL,
    }:
        if quantity <= 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Kirim miqdori 0 dan katta bo‘lishi kerak."
                    ),
                }
            )

        quantity_after = (
            quantity_before
            + quantity
        )

        movement_quantity = quantity

    elif movement_type in {
        StockMovement.MovementType.OUT,
        StockMovement.MovementType.SALE,
    }:
        if quantity <= 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Chiqim miqdori 0 dan katta bo‘lishi kerak."
                    ),
                }
            )

        if quantity > quantity_before:
            raise ValidationError(
                {
                    "quantity": (
                        f"Omborda yetarli mahsulot yo‘q. "
                        f"Mavjud qoldiq: {quantity_before}."
                    ),
                }
            )

        quantity_after = (
            quantity_before
            - quantity
        )

        movement_quantity = quantity

    else:
        quantity_after = quantity

        if quantity_after == quantity_before:
            raise ValidationError(
                {
                    "quantity": (
                        "Yangi qoldiq hozirgi qoldiqdan farq qilishi kerak."
                    ),
                }
            )

        movement_quantity = abs(
            quantity_after
            - quantity_before
        )

    try:
        quantity_after = stock_field.clean(
            quantity_after,
            product,
        )
    except ValidationError as error:
        raise ValidationError(
            {
                "quantity": error.messages,
            }
        ) from error

    movement = StockMovement(
        store=store,
        product=product,
        movement_type=movement_type,
        quantity=movement_quantity,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        created_by=actor,
        note=note.strip(),
    )

    movement.full_clean()

    product.stock_quantity = quantity_after

    product.save(
        update_fields=[
            "stock_quantity",
            "updated_at",
        ]
    )

    movement.save()

    return movement


@transaction.atomic
def cancel_sale(
    *,
    sale_id,
    store,
    actor,
    reason,
):
    if actor is None:
        raise ValidationError(
            {
                "actor": (
                    "Savdoni bekor qiluvchi foydalanuvchi aniqlanmadi."
                ),
            }
        )

    if actor.store_id != store.pk:
        raise ValidationError(
            {
                "actor": (
                    "Foydalanuvchi ushbu marketga tegishli emas."
                ),
            }
        )

    reason = str(
        reason or "",
    ).strip()

    if len(reason) < 3:
        raise ValidationError(
            {
                "reason": (
                    "Bekor qilish sababini kiriting."
                ),
            }
        )

    if len(reason) > 500:
        raise ValidationError(
            {
                "reason": (
                    "Bekor qilish sababi 500 belgidan oshmasligi kerak."
                ),
            }
        )

    try:
        sale = (
            Sale.objects.select_for_update()
            .select_related(
                "store",
                "cashier",
            )
            .get(
                pk=sale_id,
                store=store,
            )
        )
    except Sale.DoesNotExist as error:
        raise ValidationError(
            {
                "sale": (
                    "Savdo topilmadi."
                ),
            }
        ) from error

    if sale.status == Sale.Status.CANCELLED:
        raise ValidationError(
            {
                "sale": (
                    "Bu savdo oldin bekor qilingan."
                ),
            }
        )

    sale_items = list(
        sale.items.select_related(
            "product",
        ).order_by(
            "product_id",
            "pk",
        )
    )

    if not sale_items:
        raise ValidationError(
            {
                "sale": (
                    "Savdoda mahsulotlar mavjud emas."
                ),
            }
        )

    product_ids = sorted(
        {
            item.product_id
            for item in sale_items
        }
    )

    locked_products = list(
        Product.objects.select_for_update()
        .filter(
            pk__in=product_ids,
            store=store,
        )
        .order_by(
            "pk",
        )
    )

    if len(locked_products) != len(product_ids):
        raise ValidationError(
            {
                "sale": (
                    "Savdodagi mahsulotlardan biri topilmadi."
                ),
            }
        )

    for item in sale_items:
        register_stock_movement(
            store=store,
            product_id=item.product_id,
            actor=actor,
            movement_type=(
                StockMovement.MovementType.SALE_CANCEL
            ),
            quantity=item.quantity,
            note=(
                f"{sale.sale_number} savdosi bekor qilindi. "
                f"Sabab: {reason}"
            ),
            allow_inactive=True,
        )

    sale.status = Sale.Status.CANCELLED
    sale.cancelled_by = actor
    sale.cancelled_at = timezone.now()
    sale.cancellation_reason = reason

    sale.full_clean()

    sale.save(
        update_fields=[
            "status",
            "cancelled_by",
            "cancelled_at",
            "cancellation_reason",
        ]
    )

    return sale