from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import roles_required
from accounts.models import User
from products.models import Product
from sales.models import Sale, SaleItem


@roles_required(User.Role.OWNER)
def dashboard(request):
    store = request.user.store
    today = timezone.localdate()

    active_products = Product.objects.filter(
        store=store,
        is_active=True,
    )
    low_stock_products = active_products.filter(
        stock_quantity__lte=F("low_stock_threshold"),
    )

    cashiers = User.objects.filter(
        store=store,
        role=User.Role.CASHIER,
    ).order_by(
        "first_name",
        "username",
    )

    active_cashier_count = cashiers.filter(
        is_active=True,
    ).count()

    today_sales = Sale.objects.filter(
        store=store,
        status=Sale.Status.COMPLETED,
        created_at__date=today,
    )
    today_summary = today_sales.aggregate(
        total=Sum("total"),
        count=Count("id"),
    )
    today_total = today_summary["total"] or Decimal("0")
    today_sale_count = today_summary["count"] or 0

    profit_expression = ExpressionWrapper(
        (F("unit_price") - F("purchase_price")) * F("quantity"),
        output_field=DecimalField(
            max_digits=24,
            decimal_places=4,
        ),
    )
    today_profit = (
        SaleItem.objects.filter(
            sale__in=today_sales,
        )
        .aggregate(total=Sum(profit_expression))["total"]
        or Decimal("0")
    )

    cash_total = (
        today_sales.filter(
            payment_method=Sale.PaymentMethod.CASH,
        )
        .aggregate(total=Sum("total"))["total"]
        or Decimal("0")
    )
    card_total = (
        today_sales.filter(
            payment_method=Sale.PaymentMethod.CARD,
        )
        .aggregate(total=Sum("total"))["total"]
        or Decimal("0")
    )

    metric_cards = [
        {
            "title": "Bugungi tushum",
            "value": today_total,
            "suffix": "som",
            "icon": "bi-wallet2",
            "color": "blue",
        },
        {
            "title": "Bugungi savdolar",
            "value": today_sale_count,
            "suffix": "ta",
            "icon": "bi-bag-check",
            "color": "green",
        },
        {
            "title": "Mahsulotlar",
            "value": active_products.count(),
            "suffix": "ta",
            "icon": "bi-box-seam",
            "color": "purple",
        },
        {
            "title": "Kam qolganlar",
            "value": low_stock_products.count(),
            "suffix": "ta",
            "icon": "bi-exclamation-triangle",
            "color": "orange",
        },
        {
            "title": "Bugungi foyda",
            "value": today_profit,
            "suffix": "som",
            "icon": "bi-graph-up-arrow",
            "color": "teal",
        },
    ]

    context = {
        "store": store,
        "today": today,
        "metric_cards": metric_cards,
        "cashiers": cashiers[:5],
        "cashier_count": cashiers.count(),
        "active_cashier_count": active_cashier_count,
        "recent_sales": (
            Sale.objects.filter(store=store)
            .select_related("cashier")
            .order_by("-created_at", "-pk")[:5]
        ),
        "low_stock_products": low_stock_products.order_by(
            "stock_quantity",
        )[:5],
        "payment_summary": {
            "cash": cash_total,
            "card": card_total,
        },
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )