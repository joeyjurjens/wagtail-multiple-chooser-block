import json

from django.contrib.staticfiles import finders
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

from wagtail.documents.views.chooser import DocumentChooseView
from wagtail.documents.views.multiple import AddView as DocumentAddView
from wagtail.documents.views.multiple import (
    CreateFromUploadedDocumentView as DocumentCreateFromUploadView,
)
from wagtail.images.models import AbstractImage
from wagtail.images.views.chooser import ImageChooseView
from wagtail.images.views.multiple import AddView as ImageAddView
from wagtail.images.views.multiple import (
    CreateFromUploadedImageView as ImageCreateFromUploadView,
)


def get_added_message(item):
    # The messages of Wagtail's views for adding an item, so they're translated
    if isinstance(item, AbstractImage):
        return _("Image '%(image_title)s' added.") % {"image_title": item.title}
    return _("Document '%(document_title)s' added.") % {"document_title": item.title}


class BulkUploadChooseViewMixin:
    """
    In multiple selection mode, the chooser's upload tab has Wagtail's bulk
    upload, as on its "Add images" and "Add documents" views, instead of the
    form for a single file.
    """

    #: The view for uploading multiple files, and its URL name, from the viewset
    add_multiple_view_class = None
    add_multiple_url_name = None
    #: The template for the upload tab with the bulk upload
    bulk_upload_template_name = None

    @property
    def creation_form_template_name(self):
        if self.is_multiple_choice:
            return self.bulk_upload_template_name
        return super().creation_form_template_name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.is_multiple_choice and context.get("creation_form"):
            # The upload view checks the permissions and provides the context
            response = self.add_multiple_view_class.as_view()(self.request)
            context["bulk_upload"] = response.context_data
            context["bulk_upload_url"] = reverse(self.add_multiple_url_name)
            # This script moved from wagtailimages to wagtailadmin after Wagtail 7.0
            context["fileupload_validate_js"] = next(
                path
                for path in [
                    "wagtailadmin/js/vendor/jquery.fileupload-validate.js",
                    "wagtailimages/js/vendor/jquery.fileupload-validate.js",
                ]
                if finders.find(path)
            )
        return context


class BulkUploadAddViewMixin:
    """
    Wagtail's bulk upload, with a message for an uploaded item instead of the
    form to edit it, as the chooser's upload form for a single item has none.
    The form for an upload that can't be saved as an item yet, such as for a
    required field of a custom model, is still shown.
    """

    def get_edit_object_response_data(self):
        data = super().get_edit_object_response_data()
        del data["form"]
        # A duplicate has a message for each choice
        if not data.get("duplicate"):
            data["message"] = get_added_message(self.object)
        return data


class BulkUploadCreateFromUploadViewMixin:
    """Saves an upload with its form, with a message for the item it becomes."""

    def post(self, request, *args, **kwargs):
        data = json.loads(super().post(request, *args, **kwargs).content)
        if data["success"]:
            data["message"] = get_added_message(self.object)
        return JsonResponse(data)


class BulkUploadImageAddView(BulkUploadAddViewMixin, ImageAddView):
    """
    A duplicate image can be replaced by the existing image, as in Wagtail's
    image chooser.
    """

    def get_confirm_duplicate_upload_response(self, duplicates):
        return render_to_string(
            "wagtail_multiple_chooser_block/bulk_upload/confirm_duplicate_upload.html",
            {
                "existing_image": duplicates[0],
                "existing_message": get_added_message(duplicates[0]),
                "new_message": get_added_message(self.object),
                "delete_action": reverse(self.delete_object_url_name, args=(self.object.id,)),
            },
            request=self.request,
        )


class BulkUploadDocumentAddView(BulkUploadAddViewMixin, DocumentAddView):
    pass


class BulkUploadImageCreateFromUploadView(
    BulkUploadCreateFromUploadViewMixin, ImageCreateFromUploadView
):
    pass


class BulkUploadDocumentCreateFromUploadView(
    BulkUploadCreateFromUploadViewMixin, DocumentCreateFromUploadView
):
    pass


class BulkUploadImageChooseView(BulkUploadChooseViewMixin, ImageChooseView):
    bulk_upload_template_name = "wagtail_multiple_chooser_block/bulk_upload/images.html"


class BulkUploadDocumentChooseView(BulkUploadChooseViewMixin, DocumentChooseView):
    bulk_upload_template_name = "wagtail_multiple_chooser_block/bulk_upload/documents.html"
