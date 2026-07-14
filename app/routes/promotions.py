from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app.constants import PROMOTION_TYPES
from app.extensions import db
from app.models import Promotion
from app.services.posts import get_post_by_token
from app.services.promotions import promotion_amount

bp = Blueprint("promotions", __name__)


@bp.before_request
def require_promotions_enabled():
    if not current_app.config.get("PROMOTIONS_ENABLED", False):
        abort(404)


@bp.route("/posts/<post_id>/promote", methods=["GET", "POST"])
def promote(post_id):
    token = request.args.get("token", "") or request.form.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404

    if post.status != "published":
        flash("Продвижение доступно только для опубликованных объявлений", "error")
        return redirect(url_for("posts.edit", post_id=post.id, token=token))

    pending = Promotion.query.filter_by(post_id=post.id, status="pending").first()
    if pending:
        return redirect(url_for("promotions.promote_status", promo_id=pending.id, token=token))

    if request.method == "POST":
        promo_type = (request.form.get("type") or "").strip()
        if promo_type not in PROMOTION_TYPES:
            flash("Выберите тип продвижения", "error")
        else:
            promo = Promotion(
                post_id=post.id,
                type=promo_type,
                amount=promotion_amount(promo_type),
                status="pending",
            )
            db.session.add(promo)
            db.session.commit()
            flash("Заявка на продвижение принята", "success")
            return redirect(url_for("promotions.promote_status", promo_id=promo.id, token=token))

    return render_template(
        "promotions/form.html",
        post=post,
        token=token,
        promotion_types=PROMOTION_TYPES,
    )


@bp.route("/promotions/<int:promo_id>")
def promote_status(promo_id):
    token = request.args.get("token", "")
    promo = Promotion.query.get_or_404(promo_id)
    post = promo.post
    if not get_post_by_token(post.id, token):
        return render_template("errors/404.html"), 404
    return render_template(
        "promotions/status.html",
        promo=promo,
        post=post,
        token=token,
        promotion_types=PROMOTION_TYPES,
    )
