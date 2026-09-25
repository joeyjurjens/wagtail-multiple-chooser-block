from django import forms

from wagtail.images.forms import BaseImageForm


class SourceImageForm(BaseImageForm):
    """An image form with a required field, which Wagtail's bulk upload asks for."""

    source = forms.CharField()
