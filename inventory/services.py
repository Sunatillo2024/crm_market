from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from products.models import Product

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

    try:
        product = Product.objects.select_for_update().get(
            pk=product_id,
            store=store,
            is_active=True,
        )
    except Product.DoesNotExist as error:
        raise ValidationError(
            {
                "product": (
                    "Mahsulot topilmadi yoki arxivlangan."
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

    elif movement_type == StockMovement.MovementType.IN:
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