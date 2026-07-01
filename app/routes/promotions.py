from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.constants import PROMOTION_TYPES
from app.extensions import db
from app.models import Promotion
from app.services.posts import get_post_by_token

bp = Blueprint("promotions", __name__)


@bp.route("/posts/<post_id>/promote", methods=["GET", "POST"])
def promote(post_id):
    token = request.args.get("token", "") or request.form.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404

    promo_type = request.form.get("type", "boost_24h")
    if request.method == "POST" and promo_type in PROMOTION_TYPES:
        amount = current_app.config["PROMOTION_BOOST_24H_AMOUNT"]
        if promo_type == "top_7d":
            amount = amount * 5
        promo = Promotion(
            post_id=post.id,
            type=promo_type,
            amount=amount,
            status="pending",
        )
        db.session.add(promo)
        db.session.commit()
        flash("Заявка создана. Оплатите по инструкции ниже.", "success")
        return redirect(url_for("promotions.promote_status", promo_id=promo.id, token=token))

    return render_template(
        "promotions/form.html",
        post=post,
        token=token,
        promotion_types=PROMOTION_TYPES,
        amount=current_app.config["PROMOTION_BOOST_24H_AMOUNT"],
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
