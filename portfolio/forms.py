"""Public-facing forms for the portfolio. Just the CV download gate for
now — visitors type in who they are before the file is served."""
from django import forms


class CVDownloadRequestForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'autofocus': True}))
    organization = forms.CharField(max_length=120, required=False, label='Organization (optional)')
    email = forms.EmailField(max_length=254)
