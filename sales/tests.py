import json
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from audit.models import AuditLog
from inventory.models import StockMovement
from products.models import Product
from sales.models import Sale
from sales.services import cancel_sale, complete_sale
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


class SaleServiceTestCase(TestCase):
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
            barcode="111",
            purchase_price=Decimal("80"),
            sale_price=Decimal("100"),
            stock_quantity=Decimal("10"),
        )

    def checkout(
        self,
        *,
        quantity="2",
        payment_method=Sale.PaymentMethod.CASH,
        amount_received="500",
    ):
        return complete_sale(
            store=self.store,
            cashier=self.cashier,
            raw_items=[
                {
                    "product_id": self.product.pk,
                    "quantity": quantity,
                }
            ],
            payment_method=payment_method,
            amount_received=amount_received,
        )


class CompleteSaleTests(SaleServiceTestCase):
    def test_cash_payment_creates_sale_item_and_movement(self):
        sale = self.checkout()

        self.assertEqual(sale.total, Decimal("200.00"))
        self.assertEqual(sale.amount_received, Decimal("500.00"))
        self.assertEqual(sale.change_amount, Decimal("300.00"))
        self.assertEqual(sale.status, Sale.Status.COMPLETED)
        self.assertEqual(sale.items.count(), 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("8.000"))

        self.assertTrue(
            StockMovement.objects.filter(
                product=self.product,
                movement_type=StockMovement.MovementType.SALE,
            ).exists()
        )

    def test_card_payment_uses_exact_amount(self):
        sale = self.checkout(
            payment_method=Sale.PaymentMethod.CARD,
            amount_received=None,
        )

        self.assertEqual(sale.amount_received, sale.total)
        self.assertEqual(sale.change_amount, Decimal("0.00"))

    def test_insufficient_cash_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.checkout(quantity="1", amount_received="50")

    def test_insufficient_stock_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.checkout(quantity="99", amount_received="99999")

    def test_empty_cart_is_rejected(self):
        with self.assertRaises(ValidationError):
            complete_sale(
                store=self.store,
                cashier=self.cashier,
                raw_items=[],
                payment_method=Sale.PaymentMethod.CASH,
                amount_received="100",
            )

    def test_invalid_payment_method_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.checkout(payment_method="crypto")

    def test_sale_number_is_unique(self):
        first = self.checkout(quantity="1", amount_received="100")
        second = self.checkout(quantity="1", amount_received="100")

        self.assertNotEqual(first.sale_number, second.sale_number)


class CancelSaleTests(SaleServiceTestCase):
    def test_cancel_restores_stock_and_records_details(self):
        sale = self.checkout()
        item = sale.items.get()

        cancelled = cancel_sale(
            sale_id=sale.pk,
            store=self.store,
            actor=self.owner,
            reason="Mijoz savdodan voz kechdi",
        )

        self.assertEqual(cancelled.status, Sale.Status.CANCELLED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("10.000"))

        item.refresh_from_db()
        self.assertEqual(item.cancelled_by, self.owner)
        self.assertIsNotNone(item.cancelled_at)
        self.assertEqual(
            item.cancellation_reason,
            "Mijoz savdodan voz kechdi",
        )

        self.assertTrue(
            StockMovement.objects.filter(
                product=self.product,
                movement_type=StockMovement.MovementType.SALE_CANCEL,
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.SALE_CANCELLED,
                sale=sale,
            ).exists()
        )

    def test_cancel_twice_is_rejected(self):
        sale = self.checkout()

        cancel_sale(
            sale_id=sale.pk,
            store=self.store,
            actor=self.owner,
            reason="Bekor qilindi",
        )

        with self.assertRaises(ValidationError):
            cancel_sale(
                sale_id=sale.pk,
                store=self.store,
                actor=self.owner,
                reason="Yana bekor qilish",
            )

    def test_short_reason_is_rejected(self):
        sale = self.checkout()

        with self.assertRaises(ValidationError):
            cancel_sale(
                sale_id=sale.pk,
                store=self.store,
                actor=self.owner,
                reason="ab",
            )

    def test_actor_from_another_store_is_rejected(self):
        sale = self.checkout()
        stranger = make_user(
            store=make_store("Market B"),
            role=User.Role.OWNER,
            username="stranger",
        )

        with self.assertRaises(ValidationError):
            cancel_sale(
                sale_id=sale.pk,
                store=self.store,
                actor=stranger,
                reason="Bekor qilindi",
            )


class PosViewTests(SaleServiceTestCase):
    def test_pos_page_renders(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("sales:pos"))

        self.assertEqual(response.status_code, 200)

    def test_product_search_returns_json(self):
        self.client.force_login(self.cashier)

        response = self.client.get(
            reverse("sales:product_search"),
            {"q": "Cola"},
        )

        payload = response.json()

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["results"][0]["name"], "Cola")
        self.assertEqual(payload["results"][0]["sale_price"], "100.00")

    def test_checkout_endpoint_creates_sale(self):
        self.client.force_login(self.cashier)

        response = self.client.post(
            reverse("sales:checkout"),
            data=json.dumps(
                {
                    "items": [
                        {
                            "product_id": self.product.pk,
                            "quantity": "1",
                        }
                    ],
                    "payment_method": "cash",
                    "amount_received": "200",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        payload = response.json()

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["sale"]["total"], "100.00")
        self.assertEqual(Sale.objects.count(), 1)

    def test_checkout_endpoint_rejects_invalid_json(self):
        self.client.force_login(self.cashier)

        response = self.client.post(
            reverse("sales:checkout"),
            data="{",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_checkout_endpoint_rejects_empty_cart(self):
        self.client.force_login(self.cashier)

        response = self.client.post(
            reverse("sales:checkout"),
            data=json.dumps(
                {
                    "items": [],
                    "payment_method": "cash",
                    "amount_received": "10",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_cashier_cannot_open_sale_list(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("sales:list"))

        self.assertEqual(response.status_code, 403)


class SaleOwnerViewTests(SaleServiceTestCase):
    def test_sale_list_renders(self):
        sale = self.checkout()
        self.client.force_login(self.owner)

        response = self.client.get(reverse("sales:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, sale.sale_number)

    def test_sale_detail_renders(self):
        sale = self.checkout()
        self.client.force_login(self.owner)

        response = self.client.get(reverse("sales:detail", args=[sale.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cola")

    def test_receipt_renders(self):
        sale = self.checkout()
        self.client.force_login(self.owner)

        response = self.client.get(reverse("sales:receipt", args=[sale.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, sale.sale_number)

    def test_cancel_view_cancels_sale(self):
        sale = self.checkout()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("sales:cancel", args=[sale.pk]),
            {"reason": "Xato kiritilgan mahsulot"},
        )

        self.assertRedirects(
            response,
            reverse("sales:detail", args=[sale.pk]),
        )

        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.CANCELLED)
