from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from accounts.decorators import roles_required
from accounts.models import User

from .models import AuditLog


def get_pagination_query(request):
    query = request.GET.copy()

    query.pop(
        "page",
        None,
    )

    return query.urlencode()


@roles_required(User.Role.OWNER)
def audit_list(request):
    store = request.user.store

    logs = AuditLog.objects.filter(
        store=store,
    ).select_related(
        "actor",
        "target_user",
        "sale",
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    selected_action = request.GET.get(
        "action",
        "all",
    ).strip()

    if selected_action not in AuditLog.Action.values:
        selected_action = "all"

    date_from = request.GET.get(
        "date_from",
        "",
    ).strip()

    date_to = request.GET.get(
        "date_to",
        "",
    ).strip()

    if search:
        logs = logs.filter(
            Q(
                description__icontains=search,
            )
            | Q(
                actor__username__icontains=search,
            )
            | Q(
                actor__first_name__icontains=search,
            )
            | Q(
                actor__last_name__icontains=search,
            )
            | Q(
                target_user__username__icontains=search,
            )
            | Q(
                sale__sale_number__icontains=search,
            )
        )

    if selected_action != "all":
        logs = logs.filter(
            action=selected_action,
        )

    parsed_date_from = parse_date(
        date_from,
    )

    parsed_date_to = parse_date(
        date_to,
    )

    if parsed_date_from:
        logs = logs.filter(
            created_at__date__gte=parsed_date_from,
        )

    if parsed_date_to:
        logs = logs.filter(
            created_at__date__lte=parsed_date_to,
        )

    logs = logs.order_by(
        "-created_at",
        "-pk",
    )

    paginator = Paginator(
        logs,
        30,
    )

    page_obj = paginator.get_page(
        request.GET.get(
            "page",
        ),
    )

    context = {
        "page_obj": page_obj,
        "search": search,
        "selected_action": selected_action,
        "action_choices": AuditLog.Action.choices,
        "date_from": date_from,
        "date_to": date_to,
        "page_query": get_pagination_query(
            request,
        ),
    }

    return render(
        request,
        "audit/index.html",
        context,
    )
