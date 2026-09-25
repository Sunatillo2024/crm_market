from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from audit.models import AuditLog
from audit.services import record_audit_log
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


class AuditLogServiceTests(TestCase):
    def setUp(self):
        self.store = make_store()
        self.other_store = make_store("Market B")
        self.owner = make_user(
            store=self.store,
            role=User.Role.OWNER,
            username="owner",
        )

    def test_record_audit_log_strips_description(self):
        log = record_audit_log(
            store=self.store,
            actor=self.owner,
            action=AuditLog.Action.CASHIER_CREATED,
            description="   Kassir yaratildi   ",
            metadata={"username": "aziz"},
        )

        self.assertIsNotNone(log.pk)
        self.assertEqual(log.description, "Kassir yaratildi")
        self.assertEqual(log.metadata, {"username": "aziz"})
        self.assertEqual(log.store, self.store)

    def test_actor_from_another_store_is_rejected(self):
        stranger = make_user(
            store=self.other_store,
            role=User.Role.OWNER,
            username="stranger",
        )

        with self.assertRaises(ValidationError):
            record_audit_log(
                store=self.store,
                actor=stranger,
                action=AuditLog.Action.CASHIER_CREATED,
                description="Ruxsatsiz yozuv",
            )

    def test_empty_description_is_rejected(self):
        with self.assertRaises(ValidationError):
            record_audit_log(
                store=self.store,
                actor=self.owner,
                action=AuditLog.Action.CASHIER_CREATED,
                description="    ",
            )


class AuditListViewTests(TestCase):
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

        record_audit_log(
            store=self.store,
            actor=self.owner,
            action=AuditLog.Action.CASHIER_CREATED,
            target_user=self.cashier,
            description="Yangi kassir qo‘shildi.",
        )

    def test_owner_sees_activity_list(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("audit:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yangi kassir qo‘shildi.")

    def test_action_filter(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("audit:list"),
            {"action": AuditLog.Action.CASHIER_CREATED},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yangi kassir qo‘shildi.")

    def test_cashier_is_forbidden(self):
        self.client.force_login(self.cashier)

        response = self.client.get(reverse("audit:list"))

        self.assertEqual(response.status_code, 403)
