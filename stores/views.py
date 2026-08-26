from decimal import Decimal

from django.db.models import F
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import roles_required
from accounts.models import User
from products.models import Product


@roles_required(User.Role.OWNER)
def dashboard(request):
    store = request.user.store

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

    metric_cards = [
        {
            "title": "Bugungi tushum",
            "value": Decimal("0"),
            "suffix": "som",
            "icon": "bi-wallet2",
            "color": "blue",
        },
        {
            "title": "Bugungi savdolar",
            "value": 0,
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
            "value": Decimal("0"),
            "suffix": "som",
            "icon": "bi-graph-up-arrow",
            "color": "teal",
        },
    ]

    context = {
        "store": store,
        "today": timezone.localdate(),
        "metric_cards": metric_cards,
        "cashiers": cashiers[:5],
        "cashier_count": cashiers.count(),
        "active_cashier_count": active_cashier_count,
        "recent_sales": [],
        "low_stock_products": low_stock_products.order_by(
            "stock_quantity",
        )[:5],
        "payment_summary": {
            "cash": Decimal("0"),
            "transfer": Decimal("0"),
        },
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )