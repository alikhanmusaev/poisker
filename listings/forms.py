from django import forms

from listings.constants import (
    CATEGORY_LABELS,
    CITIES,
    CONDITION_CHOICES,
    POST_BODY_MAX_LEN,
    POST_BODY_MIN_LEN,
    POST_TITLE_MAX_LEN,
    POST_TITLE_MIN_LEN,
    REPORT_REASONS,
)
from core.forms import HoneypotFormMixin


class PostForm(HoneypotFormMixin, forms.Form):
    title = forms.CharField(
        label="Заголовок",
        min_length=POST_TITLE_MIN_LEN,
        max_length=POST_TITLE_MAX_LEN,
        widget=forms.TextInput(attrs={"class": "input"}),
    )
    body = forms.CharField(
        label="Описание",
        min_length=POST_BODY_MIN_LEN,
        max_length=POST_BODY_MAX_LEN,
        widget=forms.Textarea(attrs={"class": "input textarea-input", "rows": 6}),
    )
    category = forms.ChoiceField(
        label="Категория",
        choices=[("", "Выберите категорию")] + list(CATEGORY_LABELS.items()),
        widget=forms.Select(attrs={"class": "input select-input"}),
    )
    settlement_id = forms.IntegerField(
        label="Город / населённый пункт",
        min_value=1,
        widget=forms.HiddenInput(attrs={"id": "settlement_id"}),
        error_messages={
            "required": "Выберите город из подсказок",
        },
    )
    city = forms.CharField(required=False, widget=forms.HiddenInput(attrs={"id": "city"}))
    condition = forms.ChoiceField(
        label="Состояние",
        choices=CONDITION_CHOICES,
        initial="used",
        widget=forms.RadioSelect(),
    )
    price = forms.IntegerField(
        label="Цена, ₽",
        required=False,
        min_value=0,
        help_text="Оставьте пустым — цена будет «По договорённости».",
        widget=forms.NumberInput(attrs={"class": "input", "placeholder": "По договорённости"}),
    )
    images = forms.FileField(
        label="Фото",
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/*"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_honeypot()


class DraftPostForm(HoneypotFormMixin, forms.Form):
    """Relaxed validation for saving incomplete listings as drafts."""

    title = forms.CharField(
        label="Заголовок",
        required=False,
        max_length=POST_TITLE_MAX_LEN,
        widget=forms.TextInput(attrs={"class": "input"}),
    )
    body = forms.CharField(
        label="Описание",
        required=False,
        max_length=POST_BODY_MAX_LEN,
        widget=forms.Textarea(attrs={"class": "input textarea-input", "rows": 6}),
    )
    category = forms.ChoiceField(
        label="Категория",
        required=False,
        choices=[("", "Выберите категорию")] + list(CATEGORY_LABELS.items()),
        widget=forms.Select(attrs={"class": "input select-input"}),
    )
    settlement_id = forms.IntegerField(
        label="Город / населённый пункт",
        required=False,
        min_value=1,
        widget=forms.HiddenInput(attrs={"id": "settlement_id"}),
    )
    city = forms.CharField(required=False, widget=forms.HiddenInput(attrs={"id": "city"}))
    condition = forms.ChoiceField(
        label="Состояние",
        required=False,
        choices=CONDITION_CHOICES,
        initial="used",
        widget=forms.RadioSelect(),
    )
    price = forms.IntegerField(
        label="Цена, ₽",
        required=False,
        min_value=0,
        help_text="Оставьте пустым — цена будет «По договорённости».",
        widget=forms.NumberInput(attrs={"class": "input", "placeholder": "По договорённости"}),
    )
    images = forms.FileField(
        label="Фото",
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/*"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_honeypot()


class EditPostForm(PostForm):
    pass


class EditDraftPostForm(DraftPostForm):
    pass


class ReportForm(HoneypotFormMixin, forms.Form):
    reason = forms.ChoiceField(
        label="Причина",
        choices=[("", "Выберите причину")] + list(REPORT_REASONS.items()),
        widget=forms.Select(attrs={"class": "input select-input"}),
    )
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"class": "input textarea-input", "rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_honeypot()
