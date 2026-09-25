from wagtail import hooks

from .viewsets import (
    bulk_upload_document_chooser_viewset,
    bulk_upload_image_chooser_viewset,
)


@hooks.register("register_admin_viewset")
def register_bulk_upload_image_chooser_viewset():
    return bulk_upload_image_chooser_viewset


@hooks.register("register_admin_viewset")
def register_bulk_upload_document_chooser_viewset():
    return bulk_upload_document_chooser_viewset
