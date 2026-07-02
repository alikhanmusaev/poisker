from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.constants import PROMOTION_TYPES
from app.extensions import db
from app.models import Promotion
from app.services.posts import get_post_by_token

bp = Blueprint("promotions", __name__)


@bp.route("/posts/<post_id>/promote", methods=["GET", "POST"])
def promote(post_id):
    return render_template("errors/404.html"), 404


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
