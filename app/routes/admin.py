from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.constants import (
    CATEGORIES,
    CATEGORY_LABELS,
    CITIES,
    POST_STATUS_LABELS,
    PROMOTION_TYPES,
    REPORT_REASONS,
    REPORT_STATUS_LABELS,
)
from app.extensions import db, limiter, login_manager
from app.forms import AdminLoginForm, BlockPhoneForm
from app.models import AdminAuditLog, AdminUser, BlockedPhone, Post, Promotion, Report, utcnow
from app.services.admin_panel import (
    blocked_phone_rows,
    count_posts_by_status,
    count_reports,
    filter_posts_query,
    filter_promotions_query,
    filter_reports_query,
    paginate_query,
    revision_diff,
)
from app.services.audit import log_admin_action_from_request
from app.services.phone import hash_phone, validate_phone
from app.services.posts import apply_pending_revision, delete_post, reject_pending_revision
from app.services.ranking import apply_promotion, start_of_today_msk
from app.services.search import index_post, remove_post_from_index

bp = Blueprint("admin", __name__, url_prefix="/admin")

ACTION_LABELS = {
    "hide": "Скрытие объявления",
    "publish": "Публикация объявления",
    "delete": "Удаление объявления",
    "block_phone": "Блокировка номера",
    "approve_promotion": "Одобрение продвижения",
    "reject_promotion": "Отклонение продвижения",
    "approve_revision": "Одобрение правок",
    "reject_revision": "Отклонение правок",
    "unblock_phone": "Разблокировка номера",
    "mark_report_reviewed": "Жалоба рассмотрена",
}

ADMIN_NAV = (
    ("admin.dashboard", "Обзор", "layout-dashboard"),
    ("admin.posts_list", "Объявления", "list"),
    ("admin.moderation_list", "Модерация", "shield-check"),
    ("admin.reports_list", "Жалобы", "flag"),
    ("admin.deleted_list", "Удалённые", "trash-2"),
    ("admin.blocked_phones_list", "Заблокированные номера", "phone-off"),
    ("admin.promotions_list", "Поднятия", "trending-up"),
    ("admin.audit_list", "Логи", "scroll-text"),
    ("admin.settings", "Настройки", "settings"),
)


@bp.context_processor
def admin_template_helpers():
    from app.routes.media import resolve_image_url
    from app.utils.post_display import cover_image, ordered_images

    def admin_page_url(page: int) -> str:
        if not request.endpoint:
            return "#"
        params = request.args.to_dict(flat=True)
        params["page"] = page
        return url_for(request.endpoint, **params)

    return {
        "admin_page_url": admin_page_url,
        "cover_image": cover_image,
        "ordered_images": ordered_images,
        "image_url": resolve_image_url,
    }


@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


def _redirect_back(fallback_endpoint: str, **kwargs):
    target = request.referrer
    if target and target.startswith(request.host_url):
        return redirect(target)
    return redirect(url_for(fallback_endpoint, **kwargs))


def _posts_filters_from_request():
    return {
        "status": request.args.get("status", "all"),
        "q": request.args.get("q", ""),
        "city": request.args.get("city", ""),
        "category": request.args.get("category", ""),
        "has_photo": request.args.get("has_photo") in ("1", "true", "yes"),
        "has_reports": request.args.get("has_reports") in ("1", "true", "yes"),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
        "page": max(request.args.get("page", 1, type=int), 1),
    }


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Неверный логин или пароль", "error")
    return render_template("admin/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@bp.route("/")
@login_required
def dashboard():
    today_start = start_of_today_msk()
    status_counts = count_posts_by_status()
    return render_template(
        "admin/dashboard.html",
        status_counts=status_counts,
        posts_today=Post.query.filter(Post.created_at >= today_start).count(),
        reports_total=count_reports(),
        reports_new=count_reports(new_only=True),
        promos_pending=Promotion.query.filter_by(status="pending").count(),
        admin_nav=ADMIN_NAV,
    )


@bp.route("/posts")
@login_required
def posts_list():
    filters = _posts_filters_from_request()
    query = filter_posts_query(
        status=filters["status"],
        q=filters["q"],
        city=filters["city"],
        category=filters["category"],
        has_photo=filters["has_photo"],
        has_reports=filters["has_reports"],
        date_from=filters["date_from"],
        date_to=filters["date_to"],
    )
    pagination = paginate_query(query, filters["page"])
    return render_template(
        "admin/posts.html",
        posts=pagination.items,
        pagination=pagination,
        filters=filters,
        status_labels=POST_STATUS_LABELS,
        admin_nav=ADMIN_NAV,
    )


@bp.route("/moderation")
@login_required
def moderation_list():
    from sqlalchemy import or_

    page = max(request.args.get("page", 1, type=int), 1)
    query = Post.query.filter(
        or_(Post.status == "pending", Post.pending_revision.isnot(None))
    ).order_by(Post.updated_at.desc())
    pagination = paginate_query(query, page, per_page=20)
    items = [{"post": post, "diff": revision_diff(post)} for post in pagination.items]
    return render_template(
        "admin/moderation.html",
        items=items,
        pagination=pagination,
        status_labels=POST_STATUS_LABELS,
        admin_nav=ADMIN_NAV,
    )


@bp.route("/deleted")
@login_required
def deleted_list():
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = paginate_query(filter_posts_query(status="deleted"), page)
    return render_template(
        "admin/deleted.html",
        posts=pagination.items,
        pagination=pagination,
        status_labels=POST_STATUS_LABELS,
        admin_nav=ADMIN_NAV,
    )


@bp.route("/settings")
@login_required
def settings():
    from flask import current_app

    cfg = current_app.config
    return render_template(
        "admin/settings.html",
        settings={
            "REQUIRE_CAPTCHA": cfg.get("REQUIRE_CAPTCHA"),
            "CONTACT_SOFT_LIMIT": cfg.get("CONTACT_SOFT_LIMIT"),
            "RATELIMIT_ENABLED": cfg.get("RATELIMIT_ENABLED"),
            "SCHEDULER_ENABLED": cfg.get("SCHEDULER_ENABLED"),
            "APP_DOMAIN": cfg.get("APP_DOMAIN"),
        },
        admin_nav=ADMIN_NAV,
    )


@bp.route("/posts/<post_id>/preview")
@login_required
def post_preview(post_id):
    post = Post.query.get_or_404(post_id)
    from app.routes.post_detail import build_show_context

    ctx = build_show_context(post)
    ctx["robots"] = "noindex, nofollow"
    ctx["admin_preview"] = True
    ctx["back_url"] = url_for("admin.posts_list")
    return render_template("posts/show.html", **ctx)


@bp.route("/posts/<post_id>/hide", methods=["POST"])
@login_required
def hide_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.status = "hidden"
    post.updated_at = utcnow()
    db.session.commit()
    remove_post_from_index(post.id)
    log_admin_action_from_request("hide", target_type="post", target_id=post_id)
    flash("Объявление скрыто", "success")
    return _redirect_back("admin.posts_list")


@bp.route("/posts/<post_id>/publish", methods=["POST"])
@login_required
def publish_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.status = "published"
    if not post.bumped_at:
        post.bumped_at = utcnow()
    post.updated_at = utcnow()
    db.session.commit()
    index_post(post)
    log_admin_action_from_request("publish", target_type="post", target_id=post_id)
    flash("Объявление опубликовано", "success")
    return _redirect_back("admin.posts_list")


@bp.route("/posts/<post_id>/delete", methods=["POST"])
@login_required
def delete_post_admin(post_id):
    post = Post.query.get_or_404(post_id)
    delete_post(post)
    log_admin_action_from_request("delete", target_type="post", target_id=post_id)
    flash("Объявление удалено", "success")
    return _redirect_back("admin.posts_list")


@bp.route("/posts/<post_id>/block-phone", methods=["POST"])
@login_required
def block_phone(post_id):
    post = Post.query.get_or_404(post_id)
    existing = BlockedPhone.query.filter_by(phone_hash=post.phone_hash).first()
    if not existing:
        blocked = BlockedPhone(phone_hash=post.phone_hash, reason=f"Заблокировано через объявление {post_id[:8]}")
        db.session.add(blocked)
    if post.status != "deleted":
        post.status = "hidden"
        post.updated_at = utcnow()
        db.session.commit()
        remove_post_from_index(post.id)
    else:
        db.session.commit()
    log_admin_action_from_request("block_phone", target_type="post", target_id=post_id)
    flash("Номер заблокирован", "success")
    return _redirect_back("admin.posts_list")


@bp.route("/posts/<post_id>/approve-revision", methods=["POST"])
@login_required
def approve_revision(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.pending_revision:
        flash("Нет правок на проверке", "error")
        return _redirect_back("admin.moderation_list")
    apply_pending_revision(post)
    log_admin_action_from_request("approve_revision", target_type="post", target_id=post_id)
    flash("Правки опубликованы", "success")
    return _redirect_back("admin.moderation_list")


@bp.route("/posts/<post_id>/reject-revision", methods=["POST"])
@login_required
def reject_revision(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.pending_revision:
        flash("Нет правок на проверке", "error")
        return _redirect_back("admin.moderation_list")
    reject_pending_revision(post)
    log_admin_action_from_request("reject_revision", target_type="post", target_id=post_id)
    flash("Правки отклонены", "success")
    return _redirect_back("admin.moderation_list")


@bp.route("/blocked-phones", methods=["GET", "POST"])
@login_required
def blocked_phones_list():
    form = BlockPhoneForm()
    if form.validate_on_submit():
        try:
            phone = validate_phone(form.phone.data)
            phone_hash = hash_phone(phone)
            existing = BlockedPhone.query.filter_by(phone_hash=phone_hash).first()
            if existing:
                flash("Этот номер уже заблокирован", "error")
            else:
                reason = (form.reason.data or "").strip() or "Заблокировано вручную"
                db.session.add(BlockedPhone(phone_hash=phone_hash, reason=reason))
                db.session.commit()
                log_admin_action_from_request("block_phone", target_type="phone_hash", target_id=phone_hash[:16])
                flash("Номер заблокирован", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.blocked_phones_list"))

    page = max(request.args.get("page", 1, type=int), 1)
    rows, pagination = blocked_phone_rows(page)
    return render_template(
        "admin/blocked_phones.html",
        rows=rows,
        pagination=pagination,
        form=form,
        admin_nav=ADMIN_NAV,
    )


@bp.route("/blocked-phones/<int:blocked_id>/unblock", methods=["POST"])
@login_required
def unblock_phone(blocked_id):
    blocked = BlockedPhone.query.get_or_404(blocked_id)
    db.session.delete(blocked)
    db.session.commit()
    log_admin_action_from_request("unblock_phone", target_type="blocked_phone", target_id=blocked_id)
    flash("Номер разблокирован", "success")
    return redirect(url_for("admin.blocked_phones_list"))


@bp.route("/reports")
@login_required
def reports_list():
    status = request.args.get("status", "new")
    reason = request.args.get("reason", "")
    date_from = request.args.get("date_from", "")
    page = max(request.args.get("page", 1, type=int), 1)
    query = filter_reports_query(status=status, reason=reason or None, date_from=date_from or None)
    pagination = paginate_query(query, page, per_page=40)
    return render_template(
        "admin/reports.html",
        reports=pagination.items,
        pagination=pagination,
        status=status,
        reason=reason,
        date_from=date_from,
        report_reasons=REPORT_REASONS,
        report_status_labels=REPORT_STATUS_LABELS,
        status_labels=POST_STATUS_LABELS,
        admin_nav=ADMIN_NAV,
    )


@bp.route("/reports/<int:report_id>/review", methods=["POST"])
@login_required
def mark_report_reviewed(report_id):
    report = Report.query.get_or_404(report_id)
    report.status = "reviewed"
    report.reviewed_at = utcnow()
    db.session.commit()
    log_admin_action_from_request("mark_report_reviewed", target_type="report", target_id=report_id)
    flash("Жалоба отмечена как рассмотренная", "success")
    return _redirect_back("admin.reports_list")


@bp.route("/promotions")
@login_required
def promotions_list():
    status = request.args.get("status", "pending")
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = paginate_query(filter_promotions_query(status), page, per_page=40)
    return render_template(
        "admin/promotions.html",
        promos=pagination.items,
        pagination=pagination,
        status=status,
        promotion_types=PROMOTION_TYPES,
        admin_nav=ADMIN_NAV,
    )


@bp.route("/promotions/<int:promo_id>/approve", methods=["POST"])
@login_required
def approve_promotion(promo_id):
    promo = Promotion.query.get_or_404(promo_id)
    if promo.status != "pending":
        flash("Заявка уже обработана", "error")
        return redirect(url_for("admin.promotions_list"))
    promo.status = "paid"
    promo.starts_at = utcnow()
    _, _, hours = PROMOTION_TYPES.get(promo.type, ("", 1.5, 24))
    promo.ends_at = utcnow() + timedelta(hours=hours)
    db.session.commit()
    apply_promotion(promo.post, promo.type)
    index_post(promo.post)
    log_admin_action_from_request("approve_promotion", target_type="promotion", target_id=promo_id)
    flash("Продвижение активировано", "success")
    return redirect(url_for("admin.promotions_list", status="pending"))


@bp.route("/promotions/<int:promo_id>/reject", methods=["POST"])
@login_required
def reject_promotion(promo_id):
    promo = Promotion.query.get_or_404(promo_id)
    if promo.status != "pending":
        flash("Заявка уже обработана", "error")
        return redirect(url_for("admin.promotions_list"))
    promo.status = "rejected"
    db.session.commit()
    log_admin_action_from_request("reject_promotion", target_type="promotion", target_id=promo_id)
    flash("Заявка отклонена", "success")
    return redirect(url_for("admin.promotions_list", status="pending"))


@bp.route("/audit")
@login_required
def audit_list():
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    admin_ids = {log.admin_id for log in pagination.items}
    admins = {
        user.id: user.username
        for user in AdminUser.query.filter(AdminUser.id.in_(admin_ids)).all()
    } if admin_ids else {}
    return render_template(
        "admin/audit.html",
        logs=pagination.items,
        pagination=pagination,
        admins=admins,
        action_labels=ACTION_LABELS,
        admin_nav=ADMIN_NAV,
    )
