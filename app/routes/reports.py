from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import limiter
from app.forms import ReportForm
from app.models import Post, Report
from app.services.phone import hash_value
from app.services.ranking import maybe_auto_hide
from app.services.seo import post_public_url

bp = Blueprint("reports", __name__)


@bp.route("/posts/<post_id>/report", methods=["GET", "POST"])
@limiter.limit("10 per day", methods=["POST"])
def report_post(post_id):
    post = Post.query.filter_by(id=post_id).first_or_404()
    form = ReportForm()
    if form.validate_on_submit():
        token = request.form.get("cf-turnstile-response", "")
        from app.services.captcha import verify_turnstile

        if not verify_turnstile(token, request.remote_addr):
            flash("Подтвердите, что вы не робот", "error")
        else:
            ip_hash = hash_value(request.remote_addr or "unknown")
            existing = Report.query.filter_by(post_id=post_id, ip_hash=ip_hash).first()
            if existing:
                flash("Вы уже отправляли жалобу на это объявление", "error")
            else:
                from app.extensions import db

                report = Report(
                    post_id=post_id,
                    reason=form.reason.data,
                    comment=form.comment.data,
                    ip_hash=ip_hash,
                )
                post.reports_count = (post.reports_count or 0) + 1
                db.session.add(report)
                db.session.commit()
                maybe_auto_hide(post)
                flash("Жалоба отправлена. Спасибо!", "success")
                return redirect(post_public_url(post))
    return render_template("reports/form.html", form=form, post=post)
