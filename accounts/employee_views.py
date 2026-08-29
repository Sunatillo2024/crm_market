from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import roles_required
from audit.models import AuditLog
from audit.services import record_audit_log

from .employee_forms import (
    CashierCreateForm,
    CashierPasswordResetForm,
    CashierUpdateForm,
)
from .models import User


def get_cashier_or_404(*, store, pk):
    return get_object_or_404(
        User,
        pk=pk,
        store=store,
        role=User.Role.CASHIER,
    )


@roles_required(User.Role.OWNER)
def cashier_list(request):
    store = request.user.store
    cashiers = User.objects.filter(
        store=store,
        role=User.Role.CASHIER
    ).order_by("username")

    return render(
        request,
        "accounts/employees/list.html",
        {"cashiers": cashiers}
    )


@roles_required(User.Role.OWNER)
def cashier_create(request):
    store = request.user.store

    if request.method == "POST":
        form = CashierCreateForm(
            request.POST,
            store=store,
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    cashier = form.save()

                    record_audit_log(
                        store=store,
                        actor=request.user,
                        action=AuditLog.Action.CASHIER_CREATED,
                        target_user=cashier,
                        description=f"{cashier} kassir sifatida yaratildi.",
                        metadata={"username": cashier.username},
                    )
            except IntegrityError:
                form.add_error(
                    "username",
                    "Bu login oldin ro‘yxatdan o‘tgan.",
                )
            else:
                messages.success(
                    request,
                    f"Yangi kassir {cashier} yaratildi.",
                )
                return redirect("employees:list")
    else:
        form = CashierCreateForm(store=store)

    return render(
        request,
        "accounts/employees/create.html",
        {"form": form},
    )


@roles_required(User.Role.OWNER)
def cashier_update(request, pk):
    store = request.user.store
    cashier = get_cashier_or_404(store=store, pk=pk)

    if request.method == "POST":
        form = CashierUpdateForm(
            request.POST,
            instance=cashier,
            store=store,
        )

        if form.is_valid():
            changed_fields = list(form.changed_data)

            try:
                with transaction.atomic():
                    cashier = form.save()

                    record_audit_log(
                        store=store,
                        actor=request.user,
                        action=AuditLog.Action.CASHIER_UPDATED,
                        target_user=cashier,
                        description=f"{cashier} ma’lumotlari yangilandi.",
                        metadata={"changed_fields": changed_fields},
                    )
            except IntegrityError:
                form.add_error(
                    "username",
                    "Bu login boshqa foydalanuvchiga tegishli.",
                )
            else:
                messages.success(
                    request,
                    f"{cashier} ma’lumotlari yangilandi.",
                )
                return redirect("employees:list")
    else:
        form = CashierUpdateForm(
            instance=cashier,
            store=store,
        )

    return render(
        request,
        "accounts/employees/update.html",
        {
            "cashier": cashier,
            "form": form,
        },
    )


@roles_required(User.Role.OWNER)
def cashier_password_reset(request, pk):
    cashier = get_cashier_or_404(
        store=request.user.store,
        pk=pk,
    )

    if request.method == "POST":
        form = CashierPasswordResetForm(
            request.POST,
            user=cashier,
        )

        if form.is_valid():
            with transaction.atomic():
                form.save()

                record_audit_log(
                    store=request.user.store,
                    actor=request.user,
                    action=AuditLog.Action.CASHIER_PASSWORD_CHANGED,
                    target_user=cashier,
                    description=f"{cashier} uchun parol yangilandi.",
                )

            messages.success(
                request,
                f"{cashier} uchun yangi parol saqlandi.",
            )

            return redirect("employees:list")
    else:
        form = CashierPasswordResetForm(user=cashier)

    return render(
        request,
        "accounts/employees/password.html",
        {
            "cashier": cashier,
            "form": form,
        },
    )


@roles_required(User.Role.OWNER)
@require_POST
def cashier_toggle_status(request, pk):
    store = request.user.store

    with transaction.atomic():
        cashier = get_object_or_404(
            User.objects.select_for_update(),
            pk=pk,
            store=store,
            role=User.Role.CASHIER,
        )

        cashier.is_active = not cashier.is_active
        cashier.full_clean()
        cashier.save(update_fields=["is_active"])

        if cashier.is_active:
            audit_action = AuditLog.Action.CASHIER_ACTIVATED
            audit_description = f"{cashier} faollashtirildi."
        else:
            audit_action = AuditLog.Action.CASHIER_BLOCKED
            audit_description = f"{cashier} bloklandi."

        record_audit_log(
            store=store,
            actor=request.user,
            action=audit_action,
            target_user=cashier,
            description=audit_description,
        )

    if cashier.is_active:
        messages.success(
            request,
            f"{cashier} faollashtirildi.",
        )
    else:
        messages.warning(
            request,
            f"{cashier} bloklandi. U endi tizimga kira olmaydi.",
        )

    return redirect("employees:list")