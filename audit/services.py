from .models import AuditLog


def record_audit_log(
    *,
    store,
    actor,
    action,
    description,
    target_user=None,
    sale=None,
    metadata=None,
):
    audit_log = AuditLog(
        store=store,
        actor=actor,
        target_user=target_user,
        sale=sale,
        action=action,
        description=str(
            description,
        ).strip(),
        metadata=metadata or {},
    )

    audit_log.full_clean()
    audit_log.save()

    return audit_log