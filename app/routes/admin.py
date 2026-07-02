from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db, limiter, login_manager
from app.forms import AdminLoginForm
from app.models import AdminAuditLog, AdminUser, BlockedPhone, Post, Promotion, Report, utcnow
from app.services.audit import log_admin_action_from_request
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
    "approve_revision": "Одобрение правок",
    "reject_revision": "Отклонение правок",
    "unblock_phone": "Разблокировка номера",
}


@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
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
    from sqlalchemy import func

    today_start = start_of_today_msk()
    posts_today = Post.query.filter(Post.created_at >= today_start).count()
    posts_pending = Post.query.filter_by(status="pending").count()
    revisions_pending = Post.query.filter(Post.pending_revision.isnot(None)).count()
    reports_pending = Report.query.count()
    promos_pending = Promotion.query.filter_by(status="pending").count()
    total_posts = Post.query.filter_by(status="published").count()
    revenue = db.session.query(func.coalesce(func.sum(Promotion.amount), 0)).filter(
        Promotion.status == "paid"
    ).scalar()
    return render_template(
        "admin/dashboard.html",
        posts_today=posts_today,
        posts_pending=posts_pending,
        revisions_pending=revisions_pending,
        reports_pending=reports_pending,
        promos_pending=promos_pending,
        total_posts=total_posts,
        revenue=revenue,
    )


@bp.route("/posts")
@login_required
def posts_list():
    status = request.args.get("status", "pending")
    city = request.args.get("city", "")
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 50
    q = Post.query
    if status == "revisions":
        q = q.filter(Post.pending_revision.isnot(None))
    elif status and status != "all":
        q = q.filter_by(status=status)
    if city:
        q = q.filter_by(city=city)
    pagination = q.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    from app.constants import POST_STATUS_LABELS

    return render_template(
        "admin/posts.html",
        posts=pagination.items,
        pagination=pagination,
        status=status,
        status_labels=POST_STATUS_LABELS,
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
    return redirect(url_for("admin.posts_list"))


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
    return redirect(request.referrer or url_for("admin.posts_list"))


@bp.route("/posts/<post_id>/delete", methods=["POST"])
@login_required
def delete_post_admin(post_id):
    post = Post.query.get_or_404(post_id)
    delete_post(post)
    log_admin_action_from_request("delete", target_type="post", target_id=post_id)
    flash("Объявление удалено", "success")
    return redirect(url_for("admin.posts_list"))


@bp.route("/posts/<post_id>/block-phone", methods=["POST"])
@login_required
def block_phone(post_id):
    post = Post.query.get_or_404(post_id)
    existing = BlockedPhone.query.filter_by(phone_hash=post.phone_hash).first()
    if not existing:
        blocked = BlockedPhone(phone_hash=post.phone_hash, reason=f"Blocked via post {post_id}")
        db.session.add(blocked)
        post.status = "hidden"
        post.updated_at = utcnow()
        db.session.commit()
        remove_post_from_index(post.id)
    log_admin_action_from_request("block_phone", target_type="post", target_id=post_id)
    flash("Номер заблокирован", "success")
    return redirect(url_for("admin.posts_list"))


@bp.route("/posts/<post_id>/approve-revision", methods=["POST"])
@login_required
def approve_revision(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.pending_revision:
        flash("Нет правок на проверке", "error")
        return redirect(request.referrer or url_for("admin.posts_list", status="revisions"))
    apply_pending_revision(post)
    log_admin_action_from_request("approve_revision", target_type="post", target_id=post_id)
    flash("Правки опубликованы", "success")
    return redirect(request.referrer or url_for("admin.posts_list", status="revisions"))


@bp.route("/posts/<post_id>/reject-revision", methods=["POST"])
@login_required
def reject_revision(post_id):
    post = Post.query.get_or_404(post_id)
    if not post.pending_revision:
        flash("Нет правок на проверке", "error")
        return redirect(request.referrer or url_for("admin.posts_list", status="revisions"))
    reject_pending_revision(post)
    log_admin_action_from_request("reject_revision", target_type="post", target_id=post_id)
    flash("Правки отклонены", "success")
    return redirect(request.referrer or url_for("admin.posts_list", status="revisions"))


@bp.route("/blocked-phones")
@login_required
def blocked_phones_list():
    page = max(request.args.get("page", 1, type=int), 1)
    pagination = BlockedPhone.query.order_by(BlockedPhone.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/blocked_phones.html", blocked=pagination.items, pagination=pagination)


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
    reports = (
        Report.query.order_by(Report.created_at.desc()).limit(100).all()
    )
    return render_template("admin/reports.html", reports=reports)


@bp.route("/promotions")
@login_required
def promotions_list():
    status = request.args.get("status", "pending")
    promos = Promotion.query.filter_by(status=status).order_by(Promotion.created_at.desc()).all()
    return render_template("admin/promotions.html", promos=promos)


@bp.route("/promotions/<int:promo_id>/approve", methods=["POST"])
@login_required
def approve_promotion(promo_id):
    promo = Promotion.query.get_or_404(promo_id)
    if promo.status != "pending":
        flash("Заявка уже обработана", "error")
        return redirect(url_for("admin.promotions_list"))
    promo.status = "paid"
    promo.starts_at = utcnow()
    from app.constants import PROMOTION_TYPES

    _, _, hours = PROMOTION_TYPES.get(promo.type, ("", 1.5, 24))
    from datetime import timedelta

    promo.ends_at = utcnow() + timedelta(hours=hours)
    db.session.commit()
    apply_promotion(promo.post, promo.type)
    index_post(promo.post)
    log_admin_action_from_request("approve_promotion", target_type="promotion", target_id=promo_id)
    flash("Продвижение активировано", "success")
    return redirect(url_for("admin.promotions_list"))


@bp.route("/audit")
@login_required
def audit_list():
    logs = (
        AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(100).all()
    )
    admin_ids = {log.admin_id for log in logs}
    admins = {
        user.id: user.username
        for user in AdminUser.query.filter(AdminUser.id.in_(admin_ids)).all()
    } if admin_ids else {}
    return render_template(
        "admin/audit.html",
        logs=logs,
        admins=admins,
        action_labels=ACTION_LABELS,
    )
