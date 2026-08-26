from django.shortcuts import render

from accounts.decorators import roles_required
from accounts.models import User


@roles_required(User.Role.OWNER, User.Role.CASHIER)
def pos(request):
    return render(
        request,
        "sales/pos.html",
        {
            "store": request.user.store,
        },
    )