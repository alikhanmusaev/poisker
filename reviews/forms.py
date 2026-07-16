from django import forms

from reviews.models import SellerReview


class SellerReviewForm(forms.ModelForm):
    class Meta:
        model = SellerReview
        fields = ("rating", "comment")
        labels = {
            "rating": "Оценка",
            "comment": "Комментарий",
        }
        widgets = {
            "rating": forms.RadioSelect(
                choices=[(i, f"{i}") for i in range(1, 6)],
                attrs={"class": "review-rating-input"},
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "input textarea-input",
                    "rows": 4,
                    "placeholder": "Как прошла сделка? Что важно знать другим покупателям?",
                    "maxlength": 1000,
                }
            ),
        }

    def clean_comment(self):
        return (self.cleaned_data.get("comment") or "").strip()


class SellerReviewReplyForm(forms.Form):
    reply_text = forms.CharField(
        label="Ответ",
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "class": "input textarea-input",
                "rows": 3,
                "placeholder": "Ответьте покупателю…",
                "maxlength": 1000,
            }
        ),
    )

    def clean_reply_text(self):
        return (self.cleaned_data.get("reply_text") or "").strip()
