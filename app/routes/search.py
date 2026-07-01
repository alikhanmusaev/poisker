from flask import Blueprint, redirect, request, url_for

bp = Blueprint("search", __name__, url_prefix="/search")


@bp.route("/")
def search_redirect():
    return redirect(url_for("main.index", **request.args.to_dict()))


@bp.route("/suggest")
def suggest_redirect():
    return redirect(url_for("main.suggest_view", **request.args.to_dict()))
