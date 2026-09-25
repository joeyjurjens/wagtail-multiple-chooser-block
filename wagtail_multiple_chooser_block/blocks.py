from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from wagtail.admin.staticfiles import versioned_static
from wagtail.blocks import ChooserBlock, ListBlock, StructBlock
from wagtail.blocks.list_block import ListBlockAdapter

try:
    from wagtail.admin.telepath import register
except ImportError:  # Wagtail 7.0
    from wagtail.telepath import register


class MultipleChooserBlock(ListBlock):
    """
    A ListBlock where adding items opens the chooser in multiple selection mode,
    as MultipleChooserPanel does for inline models. Each chosen object becomes
    an item of the list.

    The child block is a chooser block, or a StructBlock containing one. In the
    latter case, `chooser_field_name` names the chooser block.
    """

    class Meta:
        chooser_field_name = None
        allow_duplicates = True
        # ListBlock starts with one empty item, which here would be a chooser
        # without a value. Items are added through the chooser instead.
        default = []

    def __init__(self, child_block, **kwargs):
        super().__init__(child_block, **kwargs)
        # Report configuration errors on startup, as MultipleChooserPanel does.
        self.chooser_block = self.get_chooser_block()

    def get_chooser_block(self):
        name = self.meta.chooser_field_name

        if isinstance(self.child_block, StructBlock):
            if name is None:
                raise ImproperlyConfigured(
                    "MultipleChooserBlock with a StructBlock child must specify a "
                    "chooser_field_name argument"
                )
            try:
                block = self.child_block.child_blocks[name]
            except KeyError:
                raise ImproperlyConfigured(
                    f"MultipleChooserBlock's chooser_field_name {name!r} is not a "
                    f"child block of {type(self.child_block).__name__}"
                ) from None
        elif name is not None:
            raise ImproperlyConfigured(
                "MultipleChooserBlock's chooser_field_name only applies to a StructBlock child"
            )
        else:
            block = self.child_block

        if not isinstance(block, ChooserBlock):
            raise ImproperlyConfigured(
                "MultipleChooserBlock needs a chooser block, such as "
                f"ImageChooserBlock, got {type(block).__name__}"
            )
        return block


class MultipleChooserBlockAdapter(ListBlockAdapter):
    js_constructor = "wagtail_multiple_chooser_block.blocks.MultipleChooserBlock"

    def js_args(self, block):
        name, child_block, initial_child_state, meta = super().js_args(block)
        meta["chooserFieldName"] = block.meta.chooser_field_name
        meta["allowDuplicates"] = block.meta.allow_duplicates
        meta["strings"] = {
            # ListBlock's own strings, which Wagtail 7 passes here
            **meta.get("strings", {}),
            # Wagtail's own label for removing a pill, which is translated
            "CLEAR": _("Clear"),
        }
        return [name, child_block, initial_child_state, meta]

    @cached_property
    def media(self):
        listblock_media = super().media
        return forms.Media(
            js=[
                *listblock_media._js,
                versioned_static("wagtail_multiple_chooser_block/js/multiple-chooser-block.js"),
            ],
            css={
                **listblock_media._css,
                "all": [
                    *listblock_media._css.get("all", []),
                    versioned_static(
                        "wagtail_multiple_chooser_block/css/multiple-chooser-block.css"
                    ),
                ],
            },
        )


register(MultipleChooserBlockAdapter(), MultipleChooserBlock)
