from django.utils.functional import cached_property

from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.documents.widgets import AdminDocumentChooser
from wagtail.images.blocks import ImageBlock, ImageChooserBlock
from wagtail.images.widgets import AdminImageChooser


class BulkUploadImageChooser(AdminImageChooser):
    chooser_modal_url_name = "bulk_upload_image_chooser:choose"


class BulkUploadDocumentChooser(AdminDocumentChooser):
    chooser_modal_url_name = "bulk_upload_document_chooser:choose"


class BulkUploadImageChooserBlock(ImageChooserBlock):
    """An ImageChooserBlock whose chooser can upload multiple images at once."""

    @cached_property
    def widget(self):
        return BulkUploadImageChooser()


class BulkUploadImageBlock(ImageBlock):
    """An ImageBlock whose chooser can upload multiple images at once."""

    def __init__(self, required=True, **kwargs):
        super().__init__(required=required, **kwargs)
        # ImageBlock creates its image chooser block in its constructor
        image = BulkUploadImageChooserBlock(required=required)
        image.set_name("image")
        self.child_blocks["image"] = image

    def deconstruct(self):
        # ImageBlock always deconstructs as an ImageBlock
        return (
            "wagtail_multiple_chooser_block.contrib.bulk_upload.blocks.BulkUploadImageBlock",
            [],
            self._constructor_kwargs,
        )


class BulkUploadDocumentChooserBlock(DocumentChooserBlock):
    """A DocumentChooserBlock whose chooser can upload multiple documents at once."""

    @cached_property
    def widget(self):
        return BulkUploadDocumentChooser()
