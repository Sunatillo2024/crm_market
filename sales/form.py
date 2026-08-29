from django import forms

class SaleCancelForm(forms.Form):
    reason = forms.CharField(
        label="Bekor qilish sababi",
        min_length=3,
        max_length=500,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Masalan: mahsulot xato kiritildi yoki mijoz savdodan voz kechdi."
            }
        ),
    )