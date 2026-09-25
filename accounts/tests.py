from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.employee_forms import (
    CashierCreateForm,
    CashierPasswordResetForm,
    CashierUpdateForm,
)
from accounts.models import User
from audit.models import AuditLog
from stores.models import Store


PASSWORD = "StrongPass!234"


def make_store(name="Test Market"):
    return Store.objects.create(name=name)


def make_user(*, store, role, username, password=PASSWORD, **extra):
    return User.objects.create_user(
        username=username,
        password=password,
        role=role,
        store=store,
        **extra,
    )


def cashier_form_data(**overrides):
    data = {
        "first_name": "Aziz",
        "last_name": "Karimov",
        "username": "aziz_cashier",
        "phone": "+996555123456",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }

    data.update(overrides)

    return data


class UserModelTests(TestCase):
    def setUp(self):
        self.store = make_store()

    def test_non_superuser_requires_role_and_store(self):
        user = User(username="tmpuser", password="x")

        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_cashier_with_role_and_store_is_valid(self):
        cashier = User(
            username="cashier1",
            password="x",
            role=User.Role.CASHIER,
            store=self.store,
        )

        cashier.full_clean()

    def test_role_helpers(self):
        owner = make_user(
            store=self.store,
            role=User.Role.OWNER,
            username="owner1",
        )

        self.assertTrue(owner.is_owner)
        self.assertFalse(owner.is_cashier)
        self.assertIn("owner1", str(owner))


class CashierFormTests(TestCase):
    def setUp(self):
        self.store = make_store()

    def test_form_creates_cashier_with_hashed_password(self):
        form = CashierCreateForm(
            data=cashier_form_data(),
            store=self.store,
        )

        self.assertTrue(form.is_valid(), form.errors)

        created = form.save()

        self.assertEqual(created.role, User.Role.CASHIER)
        self.assertEqual(created.store, self.store)
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertTrue(created.is_active)
        self.assertTrue(created.check_password(PASSWORD))

    def test_duplicate_username_is_rejected(self):
        make_user(
            store=self.store,
            role=User.Role.CASHIER,
            username="aziz_cashier",
        )

        form = CashierCreateForm(
            data=cashier_form_data(username="AZIZ_CASHIER"),
            store=self.store,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_password_mismatch_is_rejected(self):
        form = CashierCreateForm(
            data=cashier_form_data(password2="AnotherPass!234"),
            store=self.store,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_update_form_rejects_foreign_username(self):
        make_user(
            store=self.store,
            role=User.Role.CASHIER,
            username="first",
        )

        second = make_user(
            store=self.store,
            role=User.Role.CASHIER,
            username="second",
        )

        form = CashierUpdateForm(
            data={
                "first_name": "A",
                "last_name": "B",
                "username": "first",
                "phone": "",
            },
            instance=second,
            store=self.store,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_password_reset_form_changes_password(self):
        cashier = make_user(
            store=self.store,
            role=User.Role.CASHIER,
            username="cash",
        )

        form = CashierPasswordResetForm(
            data={
                "password1": "NewStrongPass!234",
                "password2": "NewStrongPass!234",
            },
            user=cashier,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        cashier.refresh_from_db()
        self.assertTrue(cashier.check_password("NewStrongPass!234"))


class HomeRedirectTests(TestCase):
    def setUp(self):
        self.store = make_store()

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("accounts:home"))

        self.assertRedirects(response, reverse("accounts:login"))

    def test_owner_redirected_to_dashboard(self):
        owner = make_user(
            store=self.store,
            role=User.Role.OWNER,
            username="owner",
        )

        self.client.force_login(owner)

        response = self.client.get(reverse("accounts:home"))

        self.assertRedirects(response, reverse("stores:dashboard"))

    def test_cashier_redirected_to_pos(self):
        cashier = make_user(
            store=self.store,
            role=User.Role.CASHIER,
            username="cashier",
        )

        self.client.force_login(cashier)

        response = self.client.get(reverse("accounts:home"))

        self.assertRedirects(response, reverse("sales:pos"))


class EmployeeViewTests(TestCase):
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

    def test_owner_sees_cashier_list(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("employees:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.cashier.username)

    def test_cashier_is_forbidden(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("employees:list"))

        self.assertEqual(response.status_code, 403)

    def test_create_view_creates_cashier_and_audit_log(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("employees:create"))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("employees:create"),
            cashier_form_data(),
        )

        self.assertRedirects(response, reverse("employees:list"))

        created = User.objects.get(username="aziz_cashier")

        self.assertEqual(created.role, User.Role.CASHIER)
        self.assertEqual(created.store, self.store)

        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.CASHIER_CREATED,
                target_user=created,
            ).exists()
        )

    def test_toggle_status_blocks_and_unblocks(self):
        self.client.force_login(self.owner)

        self.client.post(
            reverse("employees:toggle_status", args=[self.cashier.pk])
        )

        self.cashier.refresh_from_db()
        self.assertFalse(self.cashier.is_active)

        self.client.post(
            reverse("employees:toggle_status", args=[self.cashier.pk])
        )

        self.cashier.refresh_from_db()
        self.assertTrue(self.cashier.is_active)

        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.CASHIER_BLOCKED,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.CASHIER_ACTIVATED,
            ).exists()
        )
