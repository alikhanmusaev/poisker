from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.constants import CATEGORIES, CATEGORY_LABELS, CITIES
from app.extensions import limiter
from app.forms import EditPostForm, PostForm
from app.models import Post
from app.routes.post_detail import render_show_page
from app.services.captcha import verify_turnstile
from app.services.phone import hash_value
from app.services.posts import (
    BlockedPhoneError,
    PostLimitError,
    ValidationError,
    create_post,
    delete_post,
    get_post_by_token,
    get_public_post,
    increment_contact_clicks,
    reveal_post_phone,
    update_post,
)
from app.services.seo import post_public_url
from app.services.storage import upload_image

bp = Blueprint("posts", __name__, url_prefix="/posts")


def _ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@bp.route("/new", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def create():
    form = PostForm()
    errors = []
    is_ajax = _ajax_request()

    if form.validate_on_submit():
        token = request.form.get("cf-turnstile-response", "")
        if not verify_turnstile(token, request.remote_addr):
            errors.append("Подтвердите, что вы не робот")
        else:
            try:
                images = []
                files = request.files.getlist("images")
                for f in files[:5]:
                    if f and f.filename:
                        images.append(upload_image(f))
                data = {
                    "title": form.title.data,
                    "seller_name": form.seller_name.data,
                    "body": form.body.data,
                    "category": form.category.data,
                    "city": form.city.data,
                    "phone": form.phone.data,
                    "price": form.price.data,
                    "images": images,
                }
                ip_hash = hash_value(request.remote_addr or "unknown")
                post = create_post(data, ip_hash=ip_hash)
                edit_url = url_for("posts.edit", post_id=post.id, token=post.edit_token, _external=True)
                if is_ajax:
                    return {
                        "ok": True,
                        "post_id": post.id,
                        "edit_url": edit_url,
                        "view_url": post_public_url(post, external=True),
                        "title": post.title,
                    }
                return redirect(url_for("posts.success", post_id=post.id, token=post.edit_token))
            except PostLimitError:
                errors.append("С этого номера сегодня уже опубликовано объявление. Попробуйте завтра или отредактируйте существующее.")
            except BlockedPhoneError as e:
                errors.append(str(e))
            except ValidationError as e:
                errors.append(str(e))
            except ValueError as e:
                errors.append(str(e))
            except Exception:
                errors.append("Ошибка загрузки. Попробуйте позже.")

    if request.method == "POST":
        if not errors:
            for field_errors in form.errors.values():
                errors.extend(field_errors)
        if is_ajax:
            return {"ok": False, "errors": errors or ["Проверьте поля формы"]}, 400

    return render_template(
        "posts/create.html",
        form=form,
        errors=errors,
        cities=CITIES,
        categories=CATEGORY_LABELS,
    )


@bp.route("/my")
def my_posts():
    return render_template("posts/my.html")


@bp.route("/<post_id>/success")
def success(post_id):
    token = request.args.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404
    edit_url = url_for("posts.edit", post_id=post.id, token=token, _external=True)
    view_url = post_public_url(post, external=True)
    return render_template(
        "posts/success.html",
        post=post,
        post_id=post.id,
        title=post.title,
        edit_url=edit_url,
        view_url=view_url,
    )


@bp.route("/<post_id>/meta")
@limiter.limit("120 per minute")
def meta(post_id):
    from datetime import timezone

    from app.models import utcnow

    token = request.args.get("token", "")
    post = Post.query.filter_by(id=post_id).first()
    if not post:
        return {"ok": False}, 404

    can_edit = bool(token and get_post_by_token(post_id, token))
    if post.status != "published" and not can_edit:
        return {"ok": False}, 404

    now = utcnow()
    expires_at = post.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    expired = post.status == "expired" or bool(expires_at and expires_at < now)
    return {
        "ok": True,
        "title": post.title,
        "status": post.status,
        "expired": expired,
        "expires_at": post.expires_at.isoformat() if post.expires_at else None,
        "can_edit": can_edit,
    }


@bp.route("/<post_id>")
@limiter.limit("120 per minute")
def show(post_id):
    post = get_public_post(post_id)
    if not post:
        from flask import abort

        abort(404)
    if post.slug:
        return redirect(post_public_url(post), code=301)
    return render_show_page(post)


@bp.route("/<post_id>/contact")
@limiter.limit("30 per hour")
def contact(post_id):
    post = get_public_post(post_id)
    if not post:
        from flask import abort

        abort(404)
    phone = reveal_post_phone(post)
    if not phone:
        return {"error": "Телефон недоступен для этого объявления"}, 404
    increment_contact_clicks(post)
    return {"phone": phone}


@bp.route("/<post_id>/edit", methods=["GET", "POST"])
def edit(post_id):
    token = request.args.get("token", "") or request.form.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404

    form = EditPostForm(obj=post)
    errors = []
    if request.method == "POST" and form.validate_on_submit():
        try:
            images = list(post.images or [])
            remove_urls = set(request.form.getlist("remove_images"))
            if remove_urls:
                images = [img for img in images if img not in remove_urls]
            files = request.files.getlist("images")
            remaining_slots = max(0, 5 - len(images))
            for f in files[:remaining_slots]:
                if f and f.filename:
                    images.append(upload_image(f))
            data = {
                "title": form.title.data,
                "seller_name": form.seller_name.data,
                "body": form.body.data,
                "category": form.category.data,
                "city": form.city.data,
                "price": form.price.data,
                "images": images,
            }
            update_post(post, data)
            flash("Объявление обновлено", "success")
            return redirect(url_for("posts.edit", post_id=post.id, token=token))
        except ValidationError as e:
            errors.append(str(e))

    return render_template(
        "posts/edit.html",
        form=form,
        post=post,
        token=token,
        errors=errors,
        cities=CITIES,
        categories=CATEGORY_LABELS,
    )


@bp.route("/<post_id>/delete", methods=["POST"])
def remove(post_id):
    token = request.form.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404
    delete_post(post)
    flash("Объявление удалено", "success")
    return redirect(url_for("main.index"))
