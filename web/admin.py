"""Страницы администратора: журнал и отмена действия."""
from flask import Blueprint, g, redirect, render_template, request, url_for

from models import ACTION_TITLES
from services.admin_service import AdminService
from services.validators import format_money
from web.helpers import admin_required, audit, flash_result

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/logs")
@admin_required
def logs():
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        limit = 200
    items = AdminService.logs(limit)
    action = (request.args.get("action") or "").strip()
    if action:
        items = [item for item in items if item.action_type == action]
    return render_template(
        "admin/logs.html",
        logs=items,
        actions=ACTION_TITLES,
        current_action=action,
        money=format_money,
    )


@bp.post("/logs/<int:log_id>/undo")
@admin_required
def undo(log_id: int):
    ok, message = AdminService.undo(log_id, g.user.id)
    flash_result(ok, message)
    audit(f"отмена записи {log_id}: {message}")
    return redirect(request.referrer or url_for("admin.logs"))
