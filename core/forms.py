"""Shared anti-bot honeypot field for public forms."""

from django import forms


class HoneypotFormMixin:
    """Invisible ``website`` field — bots that fill it are rejected."""

    honeypot_field_name = "website"

    def _init_honeypot(self):
        self.fields[self.honeypot_field_name] = forms.CharField(
            required=False,
            label="",
            widget=forms.TextInput(
                attrs={
                    "class": "hp-field",
                    "tabindex": "-1",
                    "autocomplete": "off",
                    "aria-hidden": "true",
                }
            ),
        )

    def clean_website(self):
        value = (self.cleaned_data.get(self.honeypot_field_name) or "").strip()
        if value:
            raise forms.ValidationError("Обнаружена подозрительная активность.")
        return ""
