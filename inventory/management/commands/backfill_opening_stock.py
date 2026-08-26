from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import StockMovement
from products.models import Product


class Command(BaseCommand):
    help = (
        "Oldin yaratilgan mahsulotlar uchun boshlang‘ich ombor tarixini yaratadi."
    )

    def handle(
        self,
        *args,
        **options,
    ):
        created_count = 0
        skipped_count = 0

        product_ids = list(
            Product.objects.filter(
                is_active=True,
                stock_quantity__gt=0,
            ).values_list(
                "pk",
                flat=True,
            )
        )

        for product_id in product_ids:
            with transaction.atomic():
                product = (
                    Product.objects.select_for_update()
                    .select_related(
                        "store",
                    )
                    .get(
                        pk=product_id,
                    )
                )

                if product.stock_quantity <= 0:
                    skipped_count += 1
                    continue

                if StockMovement.objects.filter(
                    product=product,
                ).exists():
                    skipped_count += 1
                    continue

                movement = StockMovement(
                    store=product.store,
                    product=product,
                    movement_type=(
                        StockMovement.MovementType.OPENING
                    ),
                    quantity=product.stock_quantity,
                    quantity_before=Decimal(
                        "0",
                    ),
                    quantity_after=product.stock_quantity,
                    created_by=None,
                    note=(
                        "Ombor tizimi ishga tushirilishidan oldingi qoldiq."
                    ),
                )

                movement.full_clean()
                movement.save()

                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"Boshlang‘ich tarix yaratildi: "
                    f"{created_count} ta."
                ),
            )
        )

        self.stdout.write(
            (
                f"O‘tkazib yuborildi: "
                f"{skipped_count} ta."
            ),
        )