from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date

from accounts.decorators import roles_required
from accounts.models import User
from products.models import Product

from .forms import StockMovementForm
from .models import StockMovement
from .services import register_stock_movement


def get_pagination_query(request):
    query = request.GET.copy()

    query.pop(
        "page",
        None,
    )

    return query.urlencode()


@roles_required(User.Role.OWNER)
def inventory_list(request):
    store = request.user.store

    active_products = Product.objects.filter(
        store=store,
        is_active=True,
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    selected_stock_status = request.GET.get(
        "stock",
        "all",
    )

    if selected_stock_status not in {
        "all",
        "low",
        "out",
    }:
        selected_stock_status = "all"

    products = active_products

    if search:
        products = products.filter(
            Q(
                name__icontains=search,
            )
            | Q(
                barcode__icontains=search,
            )
        )

    if selected_stock_status == "low":
        products = products.filter(
            stock_quantity__lte=F(
                "low_stock_threshold",
            ),
        )

    elif selected_stock_status == "out":
        products = products.filter(
            stock_quantity=0,
        )

    products = products.order_by(
        "name",
        "pk",
    )

    paginator = Paginator(
        products,
        20,
    )

    page_obj = paginator.get_page(
        request.GET.get(
            "page",
        ),
    )

    inventory_value_expression = ExpressionWrapper(
        F(
            "stock_quantity",
        )
        * F(
            "purchase_price",
        ),
        output_field=DecimalField(
            max_digits=30,
            decimal_places=5,
        ),
    )

    inventory_value = active_products.aggregate(
        total=Sum(
            inventory_value_expression,
        ),
    )["total"]

    if inventory_value is None:
        inventory_value = Decimal(
            "0",
        )

    recent_movements = (
        StockMovement.objects.filter(
            store=store,
        )
        .select_related(
            "product",
            "created_by",
        )
        .order_by(
            "-created_at",
            "-pk",
        )[:8]
    )

    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_stock_status": selected_stock_status,
        "page_query": get_pagination_query(
            request,
        ),
        "active_products_count": active_products.count(),
        "low_stock_count": active_products.filter(
            stock_quantity__lte=F(
                "low_stock_threshold",
            ),
        ).count(),
        "out_of_stock_count": active_products.filter(
            stock_quantity=0,
        ).count(),
        "inventory_value": inventory_value,
        "recent_movements": recent_movements,
    }

    return render(
        request,
        "inventory/index.html",
        context,
    )


@roles_required(User.Role.OWNER)
def movement_create(request):
    store = request.user.store

    allowed_types = {
        StockMovement.MovementType.IN,
        StockMovement.MovementType.OUT,
        StockMovement.MovementType.ADJUSTMENT,
    }

    requested_type = request.GET.get(
        "type",
        StockMovement.MovementType.IN,
    )

    if requested_type not in allowed_types:
        requested_type = StockMovement.MovementType.IN

    initial = {
        "movement_type": requested_type,
    }

    requested_product = request.GET.get(
        "product",
        "",
    )

    if requested_product.isdigit():
        initial["product"] = int(
            requested_product,
        )

    form = StockMovementForm(
        (
            request.POST
            if request.method == "POST"
            else None
        ),
        store=store,
        initial=initial,
    )

    if request.method == "POST" and form.is_valid():
        try:
            movement = register_stock_movement(
                store=store,
                product_id=form.cleaned_data["product"].pk,
                actor=request.user,
                movement_type=form.cleaned_data["movement_type"],
                quantity=form.cleaned_data["quantity"],
                note=form.cleaned_data["note"],
            )

        except ValidationError as error:
            if hasattr(
                error,
                "error_dict",
            ):
                for field_name, field_errors in error.error_dict.items():
                    form.add_error(
                        (
                            field_name
                            if field_name in form.fields
                            else None
                        ),
                        field_errors,
                    )
            else:
                form.add_error(
                    None,
                    error,
                )

        else:
            messages.success(
                request,
                (
                    f"{movement.product.name}: "
                    f"qoldiq "
                    f"{movement.quantity_before} "
                    f"dan "
                    f"{movement.quantity_after} "
                    f"ga o‘zgardi."
                ),
            )

            return redirect(
                "inventory:list",
            )

    return render(
        request,
        "inventory/movement_form.html",
        {
            "form": form,
        },
    )


@roles_required(User.Role.OWNER)
def movement_history(request):
    store = request.user.store

    movements = (
        StockMovement.objects.filter(
            store=store,
        )
        .select_related(
            "product",
            "created_by",
        )
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    selected_type = request.GET.get(
        "type",
        "",
    ).strip()

    if selected_type not in StockMovement.MovementType.values:
        selected_type = ""

    selected_product_raw = request.GET.get(
        "product",
        "",
    ).strip()

    selected_product_id = None

    if selected_product_raw.isdigit():
        selected_product_id = int(
            selected_product_raw,
        )

    date_from = request.GET.get(
        "date_from",
        "",
    ).strip()

    date_to = request.GET.get(
        "date_to",
        "",
    ).strip()

    if search:
        movements = movements.filter(
            Q(
                product__name__icontains=search,
            )
            | Q(
                product__barcode__icontains=search,
            )
            | Q(
                note__icontains=search,
            )
        )

    if selected_type:
        movements = movements.filter(
            movement_type=selected_type,
        )

    if selected_product_id is not None:
        movements = movements.filter(
            product_id=selected_product_id,
        )

    parsed_date_from = parse_date(
        date_from,
    )

    parsed_date_to = parse_date(
        date_to,
    )

    if parsed_date_from:
        movements = movements.filter(
            created_at__date__gte=parsed_date_from,
        )

    if parsed_date_to:
        movements = movements.filter(
            created_at__date__lte=parsed_date_to,
        )

    movements = movements.order_by(
        "-created_at",
        "-pk",
    )

    paginator = Paginator(
        movements,
        30,
    )

    page_obj = paginator.get_page(
        request.GET.get(
            "page",
        ),
    )

    product_options = Product.objects.filter(
        store=store,
    ).order_by(
        "name",
        "pk",
    )

    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_type": selected_type,
        "selected_product_id": selected_product_id,
        "date_from": date_from,
        "date_to": date_to,
        "movement_choices": StockMovement.MovementType.choices,
        "product_options": product_options,
        "page_query": get_pagination_query(
            request,
        ),
    }

    return render(
        request,
        "inventory/history.html",
        context,
    )