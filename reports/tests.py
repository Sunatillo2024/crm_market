from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from products.models import Product
from sales.models import Sale
from sales.services import complete_sale
from stores.models import Store


PASSWORD = "StrongPass!234"


class ReportViewTests(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="Market A")

        self.owner = User.objects.create_user(
            username="owner",
            password=PASSWORD,
            role=User.Role.OWNER,
            store=self.store,
        )
        self.cashier = User.objects.create_user(
            username="cashier",
            password=PASSWORD,
            role=User.Role.CASHIER,
            store=self.store,
        )

        self.product = Product.objects.create(
            store=self.store,
            name="Cola",
            purchase_price=Decimal("80"),
            sale_price=Decimal("100"),
            stock_quantity=Decimal("10"),
        )

        complete_sale(
            store=self.store,
            cashier=self.cashier,
            raw_items=[{"product_id": self.product.pk, "quantity": "2"}],
            payment_method=Sale.PaymentMethod.CASH,
            amount_received="300",
        )

    def test_index_renders_for_owner(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("reports:index"))

        self.assertEqual(response.status_code, 200)

    def test_index_forbidden_for_cashier(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("reports:index"))

        self.assertEqual(response.status_code, 403)

    def test_period_filter_renders(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("reports:index"),
            {"period": "today"},
        )

        self.assertEqual(response.status_code, 200)

    def test_csv_export(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("reports:export_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

        decoded = response.content.decode("utf-8")
        self.assertIn("Savdo raqami", decoded)
        self.assertIn("Cola", decoded)

    def test_excel_export(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("reports:export_excel"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"PK"))
