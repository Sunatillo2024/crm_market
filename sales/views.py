import json
from decimal import Decimal
from json import JSONDecodeError

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import roles_required
from accounts.models import User
from products.models import Product
from .form import SaleCancelForm          # <-- forms (ko‘plik)

from .models import Sale
from .services import cancel_sale, complete_sale   # <-- to‘g‘ri manba


@roles_required(User.Role.OWNER, User.Role.CASHIER)
def pos(request):
    return render(request, "pos/index.html")


@roles_required(User.Role.OWNER, User.Role.CASHIER)
@require_GET
def product_search(request):
    store = request.user.store
    query = request.GET.get("q", "").strip()[:100]
    products = Product.objects.filter(store=store, is_active=True)

    if query:
        products = (
            products.filter(Q(name__icontains=query) | Q(barcode__icontains=query))
            .annotate(search_priority=Case(When(barcode=query, then=Value(0)), default=Value(1), output_field=IntegerField()))
            .order_by("search_priority", "name", "pk")
        )
    else:
        products = products.order_by("name", "pk")

    products = products[:20]
    results = [
        {
            "id": p.pk,
            "name": p.name,
            "barcode": p.barcode or "",
            "sale_price": str(p.sale_price),
            "stock_quantity": str(p.stock_quantity),
            "unit": p.unit,
            "unit_label": p.get_unit_display(),
            "is_available": p.stock_quantity > 0,
        }
        for p in products
    ]
    return JsonResponse({"ok": True, "results": results})


@roles_required(User.Role.OWNER, User.Role.CASHIER)
@require_POST
def checkout(request):
    if len(request.body) > 100_000:
        return JsonResponse({"ok": False, "errors": {"request": ["So‘rov hajmi juda katta."]}}, status=413)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "errors": {"request": ["Yuborilgan ma’lumot noto‘g‘ri."]}}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "errors": {"request": ["Yuborilgan ma’lumot noto‘g‘ri."]}}, status=400)

    try:
        sale = complete_sale(
            store=request.user.store,
            cashier=request.user,
            raw_items=payload.get("items"),
            payment_method=payload.get("payment_method"),
            amount_received=payload.get("amount_received"),
        )
    except ValidationError as error:
        if hasattr(error, "error_dict"):
            errors = {field: [str(msg) for msg in msgs] for field, msgs in error.message_dict.items()}
        else:
            errors = {"__all__": [str(msg) for msg in error.messages]}
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "sale": {
                "id": sale.pk,
                "sale_number": sale.sale_number,
                "payment_method": sale.payment_method,
                "payment_method_label": sale.get_payment_method_display(),
                "total": str(sale.total),
                "amount_received": str(sale.amount_received),
                "change_amount": str(sale.change_amount),
                "created_at": sale.created_at.isoformat(),
                "receipt_url": reverse("sales:receipt", kwargs={"pk": sale.pk}),  # <-- qo‘shildi
            },
        },
        status=201,
    )


# ---------- Yordamchi funksiyalar ----------
def get_sales_query_string(request):
    query = request.GET.copy()
    query.pop("page", None)
    return query.urlencode()


def validation_error_text(error):
    if hasattr(error, "message_dict"):
        return " ".join(str(msg) for msgs in error.message_dict.values() for msg in msgs)
    return " ".join(str(msg) for msg in error.messages)


# ---------- Asosiy view’lar ----------
@roles_required(User.Role.OWNER)
def sale_list(request):
    store = request.user.store
    all_sales = Sale.objects.filter(store=store)

    sales = (
        all_sales
        .select_related("cashier")
        .annotate(item_count=Count("items", distinct=True))
    )

    search = request.GET.get("search", "").strip()
    selected_status = request.GET.get("status", "all")
    selected_payment = request.GET.get("payment", "all")
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if selected_status not in {"all", Sale.Status.COMPLETED, Sale.Status.CANCELLED}:
        selected_status = "all"
    if selected_payment not in {"all", Sale.PaymentMethod.CASH, Sale.PaymentMethod.CARD}:
        selected_payment = "all"

    if search:
        sales = sales.filter(
            Q(sale_number__icontains=search) |
            Q(items__product_name__icontains=search) |
            Q(items__barcode__icontains=search)
        ).distinct()

    if selected_status != "all":
        sales = sales.filter(status=selected_status)
    if selected_payment != "all":
        sales = sales.filter(payment_method=selected_payment)

    parsed_date_from = parse_date(date_from)
    parsed_date_to = parse_date(date_to)
    if parsed_date_from:
        sales = sales.filter(created_at__date__gte=parsed_date_from)
    if parsed_date_to:
        sales = sales.filter(created_at__date__lte=parsed_date_to)

    sales = sales.order_by("-created_at", "-pk")
    paginator = Paginator(sales, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    today = timezone.localdate()
    today_completed_sales = all_sales.filter(status=Sale.Status.COMPLETED, created_at__date=today)
    today_total = today_completed_sales.aggregate(total=Sum("total"))["total"] or Decimal("0")

    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_status": selected_status,
        "selected_payment": selected_payment,
        "date_from": date_from,
        "date_to": date_to,
        "page_query": get_sales_query_string(request),
        "today_sales_count": today_completed_sales.count(),
        "today_total": today_total,
        "completed_count": all_sales.filter(status=Sale.Status.COMPLETED).count(),
        "cancelled_count": all_sales.filter(status=Sale.Status.CANCELLED).count(),
    }
    return render(request, "sales/index.html", context)


@roles_required(User.Role.OWNER)
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related("store", "cashier").prefetch_related("items__product"),
        pk=pk,
        store=request.user.store,
    )
    sale_items = list(sale.items.all())
    total_profit = sum((item.profit for item in sale_items), Decimal("0"))
    return render(
        request,
        "sales/detail.html",
        {
            "sale": sale,
            "sale_items": sale_items,
            "total_profit": total_profit,
            "cancel_form": SaleCancelForm(),
        },
    )


@roles_required(User.Role.OWNER, User.Role.CASHIER)
def sale_receipt(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related("store", "cashier").prefetch_related("items__product"),
        pk=pk,
        store=request.user.store,
    )
    back_url = (
        reverse("sales:detail", kwargs={"pk": sale.pk})
        if request.user.role == User.Role.OWNER
        else reverse("sales:pos")
    )
    return render(request, "sales/receipt.html", {"sale": sale, "back_url": back_url})


@roles_required(User.Role.OWNER)
@require_POST
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk, store=request.user.store)
    form = SaleCancelForm(request.POST)

    if not form.is_valid():
        error_message = " ".join(str(err) for field_errors in form.errors.values() for err in field_errors)
        messages.error(request, error_message)
        return redirect("sales:detail", pk=sale.pk)

    try:
        cancelled_sale = cancel_sale(
            sale_id=sale.pk,
            store=request.user.store,
            actor=request.user,
            reason=form.cleaned_data["reason"],
        )
    except ValidationError as error:
        messages.error(request, validation_error_text(error))
    else:
        messages.success(request, f"{cancelled_sale.sale_number} savdosi bekor qilindi. Mahsulotlar omborga qaytarildi.")

    return redirect("sales:detail", pk=sale.pk)