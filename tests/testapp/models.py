from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.blocks import CharBlock, PageChooserBlock, StructBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageBlock, ImageChooserBlock
from wagtail.models import Page
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.snippets.models import register_snippet
from wagtail_multiple_chooser_block.blocks import MultipleChooserBlock
from wagtail_multiple_chooser_block.contrib.bulk_upload.blocks import (
    BulkUploadDocumentChooserBlock,
    BulkUploadImageBlock,
)


class CaptionedImageBlock(StructBlock):
    image = ImageChooserBlock()
    caption = CharBlock(required=False)


@register_snippet
class Author(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class GalleryPage(Page):
    body = StreamField(
        [
            ("images", MultipleChooserBlock(ImageChooserBlock())),
            (
                "captioned_images",
                MultipleChooserBlock(CaptionedImageBlock(), chooser_field_name="image"),
            ),
            (
                "image_blocks",
                MultipleChooserBlock(ImageBlock(), chooser_field_name="image"),
            ),
            ("documents", MultipleChooserBlock(DocumentChooserBlock())),
            ("pages", MultipleChooserBlock(PageChooserBlock())),
            ("authors", MultipleChooserBlock(SnippetChooserBlock(Author))),
            (
                "unique_images",
                MultipleChooserBlock(ImageChooserBlock(), allow_duplicates=False),
            ),
            ("three_images", MultipleChooserBlock(ImageChooserBlock(), max_num=3)),
            (
                "bulk_images",
                MultipleChooserBlock(BulkUploadImageBlock(), chooser_field_name="image"),
            ),
            ("bulk_documents", MultipleChooserBlock(BulkUploadDocumentChooserBlock())),
        ],
        blank=True,
    )

    content_panels = [*Page.content_panels, FieldPanel("body")]
