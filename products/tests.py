from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from inventory.models import StockMovement
from products.forms import ProductCreateForm
from products.models import Product
from stores.models import Store


PASSWORD = "StrongPass!234"


def make_store(name="Market A"):
    return Store.objects.create(name=name)


def make_owner(store, username="owner"):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        role=User.Role.OWNER,
        store=store,
    )


def make_product(store, **overrides):
    data = {
        "store": store,
        "name": "Coca-Cola 1L",
        "purchase_price": Decimal("80"),
        "sale_price": Decimal("100"),
        "stock_quantity": Decimal("10"),
        "unit": Product.Unit.PIECE,
        "low_stock_threshold": Decimal("2"),
    }

    data.update(overrides)

    return Product.objects.create(**data)


class ProductModelTests(TestCase):
    def setUp(self):
        self.store = make_store()

    def test_piece_stock_must_be_whole_number(self):
        product = Product(
            store=self.store,
            name="Coca-Cola",
            purchase_price=Decimal("80"),
            sale_price=Decimal("100"),
            stock_quantity=Decimal("1.500"),
            unit=Product.Unit.PIECE,
        )

        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_kg_product_allows_fraction(self):
        product = Product(
            store=self.store,
            name="Olma",
            purchase_price=Decimal("30"),
            sale_price=Decimal("45"),
            stock_quantity=Decimal("1.500"),
            unit=Product.Unit.KG,
        )

        product.full_clean()

    def test_is_low_stock_property(self):
        product = make_product(self.store, stock_quantity=Decimal("1"))

        self.assertTrue(product.is_low_stock)

    def test_barcode_is_normalised(self):
        product = make_product(self.store, barcode="   111  ")

        self.assertEqual(product.barcode, "111")


class ProductFormTests(TestCase):
    def setUp(self):
        self.store = make_store()

    def form_data(self, **overrides):
        data = {
            "name": "Coca-Cola 1L",
            "barcode": "4780012345678",
            "purchase_price": "80",
            "sale_price": "100",
            "stock_quantity": "10",
            "unit": Product.Unit.PIECE,
            "low_stock_threshold": "2",
        }

        data.update(overrides)

        return data

    def test_duplicate_active_barcode_is_rejected(self):
        make_product(self.store, barcode="111")

        form = ProductCreateForm(
            data=self.form_data(barcode="111"),
            store=self.store,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("barcode", form.errors)

    def test_fractional_piece_quantity_is_rejected(self):
        form = ProductCreateForm(
            data=self.form_data(stock_quantity="1.5"),
            store=self.store,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("stock_quantity", form.errors)


class ProductViewTests(TestCase):
    def setUp(self):
        self.store = make_store()
        self.owner = make_owner(self.store)
        self.client.force_login(self.owner)

    def test_create_product_registers_opening_stock(self):
        response = self.client.post(
            reverse("products:create"),
            {
                "name": "Coca-Cola 1L",
                "barcode": "4780012345678",
                "purchase_price": "80",
                "sale_price": "100",
                "stock_quantity": "10",
                "unit": Product.Unit.PIECE,
                "low_stock_threshold": "2",
            },
        )

        self.assertRedirects(response, reverse("products:list"))

        product = Product.objects.get(name="Coca-Cola 1L")
        self.assertEqual(product.stock_quantity, Decimal("10.000"))

        movement = StockMovement.objects.get(product=product)
        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.OPENING,
        )
        self.assertEqual(movement.quantity_before, Decimal("0.000"))
        self.assertEqual(movement.quantity_after, Decimal("10.000"))

    def test_list_view_and_low_stock_filter(self):
        make_product(self.store, name="Kam qolgan", stock_quantity=Decimal("1"))
        make_product(
            self.store,
            name="Yetarli",
            barcode="222",
            stock_quantity=Decimal("50"),
        )

        response = self.client.get(reverse("products:list"), {"low_stock": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kam qolgan")
        self.assertNotContains(response, "Yetarli")

    def test_archive_product(self):
        product = make_product(self.store)

        response = self.client.post(
            reverse("products:archive", args=[product.pk])
        )

        self.assertRedirects(response, reverse("products:list"))

        product.refresh_from_db()
        self.assertFalse(product.is_active)

    def test_cashier_cannot_create_product(self):
        cashier = User.objects.create_user(
            username="cashier",
            password=PASSWORD,
            role=User.Role.CASHIER,
            store=self.store,
        )

        self.client.force_login(cashier)

        response = self.client.post(
            reverse("products:create"),
            {"name": "X"},
        )

        self.assertEqual(response.status_code, 403)
