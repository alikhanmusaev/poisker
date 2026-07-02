from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.constants import CATEGORIES, CATEGORY_LABELS, CITIES
from app.extensions import contact_post_rate_key, contact_rate_key, limiter
from app.forms import EditPostForm, PostForm
from app.models import Post
from app.services.captcha import (
    captcha_error_message,
    captcha_challenge_meta,
    contact_needs_captcha,
    ensure_captcha_challenge,
    extract_captcha_response,
    is_captcha_locked,
    mark_contact_revealed,
    new_captcha_question,
    verify_captcha,
    verify_captcha_or_error,
)
from app.services.phone import hash_value
from app.services.posts import (
    BlockedPhoneError,
    PostLimitError,
    ValidationError,
    create_post,
    delete_post,
    get_post_by_token,
    get_viewable_post,
    resolve_public_id_view,
    increment_contact_clicks,
    is_post_publicly_visible,
    reveal_post_phone,
    update_post,
)
from app.services.seo import post_public_url
from app.utils.post_display import form_values_for_edit, has_pending_revision, ordered_images
from app.services.storage import upload_image

bp = Blueprint("posts", __name__, url_prefix="/posts")


def _owner_view_url(post, *, external: bool = False) -> str:
    if is_post_publicly_visible(post):
        return post_public_url(post, external=external)
    return url_for(
        "posts.show",
        post_id=post.id,
        token=post.edit_token,
        _external=external,
    )


def _ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@bp.route("/new", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def create():
    form = PostForm()
    errors = []
    is_ajax = _ajax_request()

    if form.validate_on_submit():
        token = extract_captcha_response()
        if not verify_captcha(token, request.remote_addr):
            errors.append(captcha_error_message())
        else:
            try:
                images = []
                files = request.files.getlist("images")
                for f in files[:5]:
                    if f and f.filename:
                        images.append(upload_image(f))
                cover_index = request.form.get("cover_index", type=int)
                if cover_index is None:
                    cover_index = 0
                data = {
                    "title": form.title.data,
                    "seller_name": form.seller_name.data,
                    "body": form.body.data,
                    "category": form.category.data,
                    "city": form.city.data,
                    "phone": form.phone.data,
                    "price": form.price.data,
                    "images": images,
                    "cover_index": cover_index,
                }
                ip_hash = hash_value(request.remote_addr or "unknown")
                post = create_post(data, ip_hash=ip_hash)
                edit_url = url_for("posts.edit", post_id=post.id, token=post.edit_token, _external=True)
                if is_ajax:
                    return {
                        "ok": True,
                        "post_id": post.id,
                        "edit_url": edit_url,
                        "view_url": _owner_view_url(post, external=True),
                        "title": post.title,
                        "status": post.status,
                        "moderation_pending": post.status == "pending",
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
                current_app.logger.exception("Post create failed")
                errors.append("Ошибка загрузки. Попробуйте позже.")

    if request.method == "POST":
        if not errors:
            for field_errors in form.errors.values():
                errors.extend(field_errors)
        if is_ajax:
            payload = {"ok": False, "errors": errors or ["Проверьте поля формы"]}
            if any("робот" in err.lower() or "попыток" in err.lower() for err in errors):
                payload.update(captcha_challenge_meta())
            return payload, 400

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
    view_url = _owner_view_url(post, external=True)
    return render_template(
        "posts/success.html",
        post=post,
        post_id=post.id,
        title=post.title,
        edit_url=edit_url,
        view_url=view_url,
        moderation_pending=post.status == "pending",
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
    if post.status == "deleted":
        return {"ok": False, "deleted": True}, 410

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
    from flask import abort, redirect, render_template

    from app.routes.post_detail import build_show_context, render_gone_page
    from app.services.seo import post_public_url

    token = request.args.get("token", "")
    action, post = resolve_public_id_view(post_id, token=token or None)
    if action == "not_found":
        abort(404)
    if action == "gone":
        return render_gone_page()
    if action == "redirect":
        return redirect(post_public_url(post), code=301)

    owner_preview = action == "owner_preview"

    ctx = build_show_context(post, owner_preview=owner_preview, owner_token=token or None)
    if owner_preview:
        ctx["robots"] = "noindex, nofollow"
    if is_post_publicly_visible(post):
        from app.services.posts import increment_views

        increment_views(post)
    return render_template("posts/show.html", **ctx)


@bp.route("/<post_id>/contact", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["CONTACT_RATE_LIMIT"], key_func=contact_rate_key, methods=["POST"])
@limiter.limit("20 per hour", key_func=contact_post_rate_key, methods=["POST"])
def contact(post_id):
    from flask import abort, jsonify

    if request.method == "GET":
        return {"error": "Используйте POST для раскрытия телефона"}, 405

    token = request.args.get("token", "") or request.form.get("token", "")
    post = get_viewable_post(post_id, token=token or None)
    if not post:
        abort(404)
    if post.status == "pending" and not (token and get_post_by_token(post_id, token)):
        abort(404)

    if contact_needs_captcha(post_id):
        answer = extract_captcha_response()
        ok, error, _question = verify_captcha_or_error(answer, request.remote_addr)
        if not ok:
            payload = {
                "error": error or captcha_error_message(),
                "captcha_required": True,
            }
            payload.update(captcha_challenge_meta())
            return jsonify(payload), 403

    phone = reveal_post_phone(post)
    if not phone:
        return jsonify({"error": "Телефон недоступен для этого объявления"}), 404

    mark_contact_revealed(post_id)
    increment_contact_clicks(post)
    return jsonify({"phone": phone})


@bp.route("/<post_id>/edit", methods=["GET", "POST"])
def edit(post_id):
    token = request.args.get("token", "") or request.form.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404

    form = EditPostForm()
    edit_values = form_values_for_edit(post)
    if request.method == "GET":
        form.title.data = edit_values["title"]
        form.body.data = edit_values["body"]
        form.seller_name.data = post.seller_name
        form.category.data = post.category
        form.city.data = post.city
        form.price.data = post.price

    errors = []
    moderation_notice = False
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

            image_order = [u for u in request.form.getlist("image_order") if u]
            if image_order:
                ordered = [u for u in image_order if u in images]
                images = ordered + [u for u in images if u not in ordered]

            cover_index = request.form.get("cover_index", type=int)
            if cover_index is None:
                cover_index = edit_values["cover_index"]

            data = {
                "title": form.title.data,
                "seller_name": form.seller_name.data,
                "body": form.body.data,
                "category": form.category.data,
                "city": form.city.data,
                "price": form.price.data,
                "images": images,
                "cover_index": cover_index,
            }
            update_post(post, data)
            moderation_notice = has_pending_revision(post)
            flash(
                "Изменения отправлены на проверку. Объявление остаётся онлайн."
                if moderation_notice
                else "Объявление обновлено",
                "success",
            )
            return redirect(url_for("posts.my_posts"))
        except ValidationError as e:
            errors.append(str(e))

    owner_phone = reveal_post_phone(post)
    display_images = ordered_images(post)

    return render_template(
        "posts/edit.html",
        form=form,
        post=post,
        token=token,
        owner_phone=owner_phone,
        errors=errors,
        cities=CITIES,
        categories=CATEGORY_LABELS,
        edit_images=edit_values["images"],
        cover_index=edit_values["cover_index"],
        pending_revision=post.pending_revision,
        moderation_notice=has_pending_revision(post),
        display_images=display_images,
    )


@bp.route("/<post_id>/delete", methods=["POST"])
def remove(post_id):
    token = request.form.get("token", "")
    post = get_post_by_token(post_id, token)
    if not post:
        return render_template("errors/404.html"), 404
    delete_post(post)
    flash("Объявление снято с публикации", "success")
    return redirect(url_for("main.index"))
