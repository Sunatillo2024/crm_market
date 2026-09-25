from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from audit.models import AuditLog
from inventory.models import StockMovement
from inventory.services import register_stock_movement
from products.models import Product
from stores.models import Store


PASSWORD = "StrongPass!234"


def make_store(name="Market A"):
    return Store.objects.create(name=name)


def make_user(*, store, role, username):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        role=role,
        store=store,
    )


class StockMovementServiceTests(TestCase):
    def setUp(self):
        self.store = make_store()
        self.other_store = make_store("Market B")
        self.owner = make_user(
            store=self.store,
            role=User.Role.OWNER,
            username="owner",
        )
        self.product = Product.objects.create(
            store=self.store,
            name="Cola",
            purchase_price=Decimal("80"),
            sale_price=Decimal("100"),
            stock_quantity=Decimal("0"),
        )

    def register(self, movement_type, quantity, **kwargs):
        return register_stock_movement(
            store=self.store,
            product_id=self.product.pk,
            actor=self.owner,
            movement_type=movement_type,
            quantity=Decimal(str(quantity)),
            **kwargs,
        )

    def test_opening_sets_stock_and_creates_history(self):
        movement = self.register(
            StockMovement.MovementType.OPENING,
            "5",
        )

        self.product.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, Decimal("5.000"))
        self.assertEqual(movement.quantity_before, Decimal("0.000"))
        self.assertEqual(movement.quantity_after, Decimal("5.000"))

        self.assertTrue(
            AuditLog.objects.filter(
                store=self.store,
                actor=self.owner,
                action=AuditLog.Action.STOCK_MOVEMENT,
                metadata__product_id=self.product.pk,
            ).exists()
        )

    def test_second_opening_is_rejected(self):
        self.register(StockMovement.MovementType.OPENING, "5")

        with self.assertRaises(ValidationError):
            self.register(StockMovement.MovementType.OPENING, "3")

    def test_in_then_out_updates_stock(self):
        self.register(StockMovement.MovementType.IN, "10")
        movement = self.register(StockMovement.MovementType.OUT, "4")

        self.product.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, Decimal("6.000"))
        self.assertEqual(movement.quantity_after, Decimal("6.000"))

    def test_out_above_stock_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.register(StockMovement.MovementType.OUT, "5")

    def test_adjustment_uses_absolute_quantity(self):
        self.register(StockMovement.MovementType.IN, "10")
        movement = self.register(StockMovement.MovementType.ADJUSTMENT, "7")

        self.product.refresh_from_db()

        self.assertEqual(self.product.stock_quantity, Decimal("7.000"))
        self.assertEqual(movement.quantity, Decimal("3.000"))

    def test_actor_from_another_store_is_rejected(self):
        stranger = make_user(
            store=self.other_store,
            role=User.Role.OWNER,
            username="stranger",
        )

        with self.assertRaises(ValidationError):
            register_stock_movement(
                store=self.store,
                product_id=self.product.pk,
                actor=stranger,
                movement_type=StockMovement.MovementType.IN,
                quantity=Decimal("1"),
            )

    def test_inactive_product_is_rejected_unless_allowed(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            self.register(StockMovement.MovementType.IN, "1")

        movement = self.register(
            StockMovement.MovementType.IN,
            "1",
            allow_inactive=True,
        )

        self.assertEqual(movement.quantity_after, Decimal("1.000"))

    def test_unknown_movement_type_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.register("unknown", "1")


class InventoryViewTests(TestCase):
    def setUp(self):
        self.store = make_store()
        self.owner = make_user(
            store=self.store,
            role=User.Role.OWNER,
            username="owner",
        )
        self.cashier = make_user(
            store=self.store,
            role=User.Role.CASHIER,
            username="cashier",
        )
        self.product = Product.objects.create(
            store=self.store,
            name="Cola",
            purchase_price=Decimal("80"),
            sale_price=Decimal("100"),
            stock_quantity=Decimal("3"),
        )

    def test_inventory_list_renders(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("inventory:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cola")

    def test_movement_create_increases_stock(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("inventory:movement_create"),
            {
                "product": self.product.pk,
                "movement_type": StockMovement.MovementType.IN,
                "quantity": "5",
                "note": "Yangi kirim",
            },
        )

        self.assertRedirects(response, reverse("inventory:list"))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("8.000"))

    def test_movement_history_renders(self):
        register_stock_movement(
            store=self.store,
            product_id=self.product.pk,
            actor=self.owner,
            movement_type=StockMovement.MovementType.IN,
            quantity=Decimal("2"),
            note="Tarix testi",
        )

        self.client.force_login(self.owner)

        response = self.client.get(reverse("inventory:history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cola")
        self.assertContains(response, "Kirim")
        self.assertContains(response, "Tarix testi")

    def test_cashier_is_forbidden(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("inventory:list"))

        self.assertEqual(response.status_code, 403)
