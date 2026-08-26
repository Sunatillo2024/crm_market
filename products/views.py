from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import roles_required
from accounts.models import User
from inventory.models import StockMovement
from inventory.services import register_stock_movement

from .forms import ProductCreateForm, ProductUpdateForm
from .models import Product


@roles_required(User.Role.OWNER)
def product_list(request):
    store = request.user.store

    all_products = Product.objects.filter(
        store=store,
    )

    active_products = all_products.filter(
        is_active=True,
    )

    search = request.GET.get("search", "").strip()
    selected_status = request.GET.get("status", "active")
    low_stock = request.GET.get("low_stock") == "1"

    if selected_status not in {"active", "archived", "all"}:
        selected_status = "active"

    products = all_products

    if selected_status == "active":
        products = products.filter(is_active=True)
    elif selected_status == "archived":
        products = products.filter(is_active=False)

    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(barcode__icontains=search)
        )

    if low_stock:
        products = products.filter(
            is_active=True,
            stock_quantity__lte=F("low_stock_threshold"),
        )

    products = products.order_by("name")

    paginator = Paginator(products, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_status": selected_status,
        "low_stock": low_stock,
        "active_count": active_products.count(),
        "archived_count": all_products.filter(
            is_active=False,
        ).count(),
        "low_stock_count": active_products.filter(
            stock_quantity__lte=F("low_stock_threshold"),
        ).count(),
    }

    return render(
        request,
        "products/index.html",
        context,
    )


@roles_required(User.Role.OWNER)
def product_create(request):
    store = request.user.store

    form = ProductCreateForm(
        request.POST or None,
        store=store,
    )

    form.instance.store = store

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            product = form.save(
                commit=False,
            )

            product.store = store

            initial_quantity = product.stock_quantity

            product.stock_quantity = Decimal(
                "0",
            )

            product.save()

            if initial_quantity > 0:
                register_stock_movement(
                    store=store,
                    product_id=product.pk,
                    actor=request.user,
                    movement_type=(
                        StockMovement.MovementType.OPENING
                    ),
                    quantity=initial_quantity,
                    note=(
                        "Mahsulot yaratilgandagi boshlang‘ich qoldiq."
                    ),
                )

        messages.success(
            request,
            f"{product.name} mahsuloti qo‘shildi.",
        )

        return redirect(
            "products:list",
        )

    return render(
        request,
        "products/form.html",
        {
            "form": form,
            "page_title": "Mahsulot qo‘shish",
            "submit_label": "Mahsulotni saqlash",
        },
    )


@roles_required(User.Role.OWNER)
def product_edit(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        store=request.user.store,
        is_active=True,
    )

    form = ProductUpdateForm(
        request.POST or None,
        instance=product,
        store=request.user.store,
    )

    if request.method == "POST" and form.is_valid():
        product = form.save()

        messages.success(
            request,
            f"{product.name} mahsuloti yangilandi.",
        )

        return redirect("products:list")

    return render(
        request,
        "products/form.html",
        {
            "form": form,
            "product": product,
            "page_title": "Mahsulotni tahrirlash",
            "submit_label": "O‘zgarishlarni saqlash",
        },
    )


@roles_required(User.Role.OWNER)
@require_POST
def product_archive(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        store=request.user.store,
        is_active=True,
    )

    product.is_active = False
    product.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    messages.success(
        request,
        f"{product.name} mahsuloti arxivlandi.",
    )

    return redirect("products:list")