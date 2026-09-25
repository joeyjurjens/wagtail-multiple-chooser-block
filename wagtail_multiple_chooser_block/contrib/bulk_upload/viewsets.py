from django.urls import path

from wagtail.documents import get_document_model_string
from wagtail.documents.views.chooser import DocumentChooserViewSet
from wagtail.images import get_image_model
from wagtail.images.views.chooser import ImageChooserViewSet

from .views import (
    BulkUploadDocumentAddView,
    BulkUploadDocumentChooseView,
    BulkUploadDocumentCreateFromUploadView,
    BulkUploadImageAddView,
    BulkUploadImageChooseView,
    BulkUploadImageCreateFromUploadView,
)


class BulkUploadChooserViewSetMixin:
    """Adds the views for uploading multiple files to a chooser viewset."""

    add_multiple_view_class = None
    create_from_upload_view_class = None

    def get_common_view_kwargs(self, **kwargs):
        return super().get_common_view_kwargs(
            add_multiple_view_class=self.add_multiple_view_class,
            add_multiple_url_name=self.get_url_name("add_multiple"),
            **kwargs,
        )

    def get_urlpatterns(self):
        # The form of an upload is saved with the view here
        edit_upload_url_name = self.get_url_name("create_from_upload")
        return super().get_urlpatterns() + [
            path(
                "add-multiple/",
                self.add_multiple_view_class.as_view(edit_upload_url_name=edit_upload_url_name),
                name="add_multiple",
            ),
            path(
                "create-from-upload/<int:uploaded_file_id>/",
                self.create_from_upload_view_class.as_view(
                    edit_upload_url_name=edit_upload_url_name
                ),
                name="create_from_upload",
            ),
        ]


class BulkUploadImageChooserViewSet(BulkUploadChooserViewSetMixin, ImageChooserViewSet):
    choose_view_class = BulkUploadImageChooseView
    add_multiple_view_class = BulkUploadImageAddView
    create_from_upload_view_class = BulkUploadImageCreateFromUploadView


class BulkUploadDocumentChooserViewSet(BulkUploadChooserViewSetMixin, DocumentChooserViewSet):
    choose_view_class = BulkUploadDocumentChooseView
    add_multiple_view_class = BulkUploadDocumentAddView
    create_from_upload_view_class = BulkUploadDocumentCreateFromUploadView


bulk_upload_image_chooser_viewset = BulkUploadImageChooserViewSet(
    "bulk_upload_image_chooser",
    model=get_image_model(),
    url_prefix="bulk-upload/image-chooser",
)

bulk_upload_document_chooser_viewset = BulkUploadDocumentChooserViewSet(
    "bulk_upload_document_chooser",
    model=get_document_model_string(),
    url_prefix="bulk-upload/document-chooser",
    # Wagtail's own document chooser registers the widget for the model
    register_widget=False,
)
