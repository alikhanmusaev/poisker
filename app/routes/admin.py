from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db, limiter, login_manager
from app.forms import AdminLoginForm
from app.models import AdminUser, BlockedPhone, Post, Promotion, Report, utcnow
from app.services.posts import delete_post
from app.services.ranking import apply_promotion, start_of_today_msk
from app.services.search import index_post, remove_post_from_index

bp = Blueprint("admin", __name__, url_prefix="/admin")


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
    reports_pending = Report.query.count()
    promos_pending = Promotion.query.filter_by(status="pending").count()
    total_posts = Post.query.filter_by(status="published").count()
    revenue = db.session.query(func.coalesce(func.sum(Promotion.amount), 0)).filter(
        Promotion.status == "paid"
    ).scalar()
    return render_template(
        "admin/dashboard.html",
        posts_today=posts_today,
        reports_pending=reports_pending,
        promos_pending=promos_pending,
        total_posts=total_posts,
        revenue=revenue,
    )


@bp.route("/posts")
@login_required
def posts_list():
    status = request.args.get("status", "")
    city = request.args.get("city", "")
    q = Post.query
    if status:
        q = q.filter_by(status=status)
    if city:
        q = q.filter_by(city=city)
    posts = q.order_by(Post.created_at.desc()).limit(100).all()
    return render_template("admin/posts.html", posts=posts)


@bp.route("/posts/<post_id>/hide", methods=["POST"])
@login_required
def hide_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.status = "hidden"
    db.session.commit()
    remove_post_from_index(post.id)
    flash("Объявление скрыто", "success")
    return redirect(url_for("admin.posts_list"))


@bp.route("/posts/<post_id>/publish", methods=["POST"])
@login_required
def publish_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.status = "published"
    db.session.commit()
    index_post(post)
    flash("Объявление опубликовано", "success")
    return redirect(url_for("admin.posts_list"))


@bp.route("/posts/<post_id>/delete", methods=["POST"])
@login_required
def delete_post_admin(post_id):
    post = Post.query.get_or_404(post_id)
    delete_post(post)
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
        db.session.commit()
        remove_post_from_index(post.id)
    flash("Номер заблокирован", "success")
    return redirect(url_for("admin.posts_list"))


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
    flash("Продвижение активировано", "success")
    return redirect(url_for("admin.promotions_list"))
