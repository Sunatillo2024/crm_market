from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from products.models import Product
from sales.models import Sale
from sales.services import complete_sale


from accounts.models import User
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


class StoreDashboardTests(TestCase):
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

    def test_owner_can_open_dashboard(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("stores:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.store.name)

    def test_dashboard_uses_today_sale_metrics(self):
        product = Product.objects.create(
            store=self.store,
            name="Cola",
            purchase_price=Decimal("80"),
            sale_price=Decimal("100"),
            stock_quantity=Decimal("10"),
        )

        complete_sale(
            store=self.store,
            cashier=self.cashier,
            raw_items=[{"product_id": product.pk, "quantity": "2"}],
            payment_method=Sale.PaymentMethod.CASH,
            amount_received="500",
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse("stores:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["metric_cards"][0]["value"],
            Decimal("200.00"),
        )
        self.assertEqual(
            response.context["metric_cards"][1]["value"],
            1,
        )
        self.assertEqual(
            response.context["metric_cards"][4]["value"],
            Decimal("40"),
        )
        self.assertEqual(
            response.context["payment_summary"]["cash"],
            Decimal("200.00"),
        )
        self.assertEqual(
            response.context["payment_summary"]["card"],
            Decimal("0"),
        )
        self.assertEqual(len(response.context["recent_sales"]), 1)

    def test_cashier_is_forbidden(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("stores:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("stores:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_inactive_store_blocks_access(self):
        self.store.is_active = False
        self.store.save(update_fields=["is_active"])

        self.client.force_login(self.owner)

        response = self.client.get(reverse("stores:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_store_str(self):
        self.assertEqual(str(self.store), "Market A")
