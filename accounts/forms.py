from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm, UserCreationForm

from accounts.models import User
from core.forms import HoneypotFormMixin
from core.phone import ensure_phone_available, validate_phone


def _style_auth_fields(form):
    for name, field in form.fields.items():
        if name == getattr(form, "honeypot_field_name", None):
            continue
        widget = field.widget
        existing = widget.attrs.get("class", "")
        if "input" not in existing.split() and "hp-field" not in existing.split():
            widget.attrs["class"] = f"{existing} input".strip()


class RegistrationForm(HoneypotFormMixin, UserCreationForm):
    display_name = forms.CharField(
        label="Имя",
        max_length=80,
        widget=forms.TextInput(attrs={"class": "input", "autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "input", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        label="Телефон для связи",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "type": "tel",
                "autocomplete": "tel",
                "placeholder": "+7 (999) 123-45-67",
            }
        ),
    )
    password1 = forms.CharField(
        label="Пароль",
        help_text="Не менее 8 символов.",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Повтор пароля",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("display_name", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_honeypot()
        _style_auth_fields(self)

    def clean_phone(self):
        return ensure_phone_available(self.cleaned_data.get("phone", ""))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.display_name = self.cleaned_data["display_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        user.phone = self.cleaned_data["phone"]
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "input", "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "current-password"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        _style_auth_fields(self)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").strip().lower()
        password = cleaned.get("password")
        if email and password:
            user = authenticate(self.request, email=email, password=password)
            if user is None:
                raise forms.ValidationError("Неверный email или пароль.")
            if user.is_blocked:
                raise forms.ValidationError("Аккаунт заблокирован.")
            if not user.is_active:
                raise forms.ValidationError("Аккаунт деактивирован.")
            self.user_cache = user
        return cleaned

    def get_user(self):
        return self.user_cache


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "phone")
        labels = {"display_name": "Имя", "phone": "Телефон для связи"}
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "input"}),
            "phone": forms.TextInput(
                attrs={
                    "class": "input",
                    "type": "tel",
                    "autocomplete": "tel",
                    "placeholder": "+7 (999) 123-45-67",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = True
        _style_auth_fields(self)

    def clean_phone(self):
        user_id = self.instance.pk if self.instance else None
        return ensure_phone_available(self.cleaned_data.get("phone", ""), exclude_user_id=user_id)


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Email"
        self.fields["email"].widget.attrs.update(
            {"class": "input", "autocomplete": "email", "placeholder": "you@example.com"}
        )


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Новый пароль"
        self.fields["new_password2"].label = "Повтор пароля"
        _style_auth_fields(self)


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Текущий пароль"
        self.fields["new_password1"].label = "Новый пароль"
        self.fields["new_password2"].label = "Повтор пароля"
        _style_auth_fields(self)
