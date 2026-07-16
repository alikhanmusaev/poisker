from django import forms


class MessageForm(forms.Form):
    body = forms.CharField(
        label="Сообщение",
        required=False,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "input textarea-input message-compose-input",
                "rows": 3,
                "placeholder": "Напишите сообщение…",
                "autocomplete": "off",
            }
        ),
    )
    image = forms.ImageField(
        label="Фото",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "message-compose-file",
                "accept": "image/jpeg,image/png,image/webp",
                "id": "id_image",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        body = (cleaned.get("body") or "").strip()
        image = cleaned.get("image")
        if not body and not image:
            raise forms.ValidationError("Введите текст или прикрепите фото.")
        cleaned["body"] = body
        return cleaned
