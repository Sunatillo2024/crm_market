def current_store(request):
    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return {
            "current_store": None,
        }

    if not getattr(user, "store_id", None):
        return {
            "current_store": None,
        }

    return {
        "current_store": user.store,
    }
