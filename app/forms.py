from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.constants import (
    CATEGORIES,
    CATEGORY_LABELS,
    CITIES,
    POST_BODY_MAX_LEN,
    POST_BODY_MIN_LEN,
    POST_TITLE_DB_MAX_LEN,
    POST_TITLE_MAX_LEN,
    POST_TITLE_MIN_LEN,
    REPORT_REASONS,
)


class PostForm(FlaskForm):
    title = StringField(
        "Заголовок",
        validators=[DataRequired(), Length(min=POST_TITLE_MIN_LEN, max=POST_TITLE_MAX_LEN)],
    )
    seller_name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=80)])
    body = TextAreaField(
        "Описание",
        validators=[DataRequired(), Length(min=POST_BODY_MIN_LEN, max=POST_BODY_MAX_LEN)],
    )
    category = SelectField(
        "Категория",
        choices=[(k, v) for k, v in CATEGORY_LABELS.items()],
        validators=[DataRequired()],
    )
    city = SelectField(
        "Город",
        choices=[(k, v) for k, v in CITIES.items()],
        validators=[DataRequired()],
    )
    phone = StringField("Телефон", validators=[DataRequired(), Length(min=10, max=20)])
    price = IntegerField("Цена, ₽", validators=[Optional()])


class EditPostForm(FlaskForm):
    title = StringField(
        "Заголовок",
        validators=[DataRequired(), Length(min=POST_TITLE_MIN_LEN, max=POST_TITLE_DB_MAX_LEN)],
    )
    seller_name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=80)])
    body = TextAreaField(
        "Описание",
        validators=[DataRequired(), Length(min=POST_BODY_MIN_LEN, max=POST_BODY_MAX_LEN)],
    )
    category = SelectField(
        "Категория",
        choices=[(k, v) for k, v in CATEGORY_LABELS.items()],
        validators=[DataRequired()],
    )
    city = SelectField(
        "Город",
        choices=[(k, v) for k, v in CITIES.items()],
        validators=[DataRequired()],
    )
    price = IntegerField("Цена, ₽", validators=[Optional()])


class ReportForm(FlaskForm):
    reason = SelectField(
        "Причина",
        choices=[(k, v) for k, v in REPORT_REASONS.items()],
        validators=[DataRequired()],
    )
    comment = TextAreaField("Комментарий", validators=[Optional(), Length(max=500)])


class AdminLoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
