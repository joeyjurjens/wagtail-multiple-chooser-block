"""
Tests of the editing interface in a browser, since the behaviour of the block
lives in its JavaScript.
"""

import io
import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from wagtail.coreutils import get_supported_content_language_variant
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Collection, Locale, Page
from wagtail.test.utils import WagtailTestUtils

from PIL import Image as PILImage
from playwright.sync_api import expect, sync_playwright

from tests.testapp.models import Author, GalleryPage

# Playwright's synchronous API runs an event loop in the test thread, which
# makes Django refuse database queries from that thread.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


def image_file(color):
    buffer = io.BytesIO()
    PILImage.new("RGB", (40, 40), color=color).save(buffer, format="PNG")
    return SimpleUploadedFile(f"{color}.png", buffer.getvalue(), "image/png")


class EditingTestCase(WagtailTestUtils, StaticLiveServerTestCase):
    """Edits a GalleryPage in the Wagtail admin with a browser."""

    @classmethod
    def setUpClass(cls):
        media_root = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, media_root)
        media_settings = override_settings(MEDIA_ROOT=media_root)
        media_settings.enable()
        cls.addClassCleanup(media_settings.disable)

        super().setUpClass()

        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch()
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        # The database is emptied after each test, including the locale, root
        # page and root collection that Wagtail's migrations create.
        Locale.objects.get_or_create(
            language_code=get_supported_content_language_variant(settings.LANGUAGE_CODE)
        )
        if not Collection.get_first_root_node():
            Collection.add_root(name="Root")
        self.root_page = Page.get_first_root_node() or Page.add_root(instance=Page(title="Root"))
        self.gallery_page = self.root_page.add_child(
            instance=GalleryPage(title="Gallery", slug="gallery")
        )
        self.red, self.green, self.blue, self.black = [
            Image.objects.create(title=color.title(), file=image_file(color))
            for color in ["red", "green", "blue", "black"]
        ]

        self.login()
        browser_context = self.browser.new_context()
        self.addCleanup(browser_context.close)
        browser_context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
                    "url": self.live_server_url,
                }
            ]
        )
        self.page = browser_context.new_page()
        # Fail faster than the default 30 seconds per action, while leaving
        # room for animations when running several test environments at once
        self.page.set_default_timeout(10000)
        self.js_errors = []
        self.page.on("pageerror", lambda error: self.js_errors.append(error))
        self.page.goto(f"{self.live_server_url}/admin/pages/{self.gallery_page.pk}/edit/")

    def add_block(self, label):
        self.page.locator(".c-sf-add-button").first.click()
        self.page.get_by_role("option", name=label, exact=True).click()

    def list_add_buttons(self):
        return self.page.locator("[data-streamfield-list-add]")

    def checkbox(self, obj):
        return self.page.locator(f"[data-multiple-choice-select][value='{obj.pk}']")

    def confirm(self):
        self.page.locator("[data-multiple-choice-submit]").click()
        self.page.locator(".modal").wait_for(state="hidden")

    def pills(self):
        return self.page.locator(".multiple-chooser-block-selection__item")

    def choose(self, *objects, add_button=0):
        """Open the chooser from a "+" button and select the given objects."""
        self.list_add_buttons().nth(add_button).click()
        for obj in objects:
            self.checkbox(obj).check()
        # The selected items are listed as pills, by their title
        expect(self.pills()).to_have_text([str(obj) for obj in objects])
        self.confirm()

    def upload_image(self, path, title, add_button=0):
        """Open the chooser from a "+" button and upload a new image in it."""
        self.list_add_buttons().nth(add_button).click()
        modal = self.page.locator(".modal")
        modal.get_by_role("tab", name="Upload").click()
        modal.locator("input[type=file]").set_input_files(path)
        modal.locator("input[name$='title']").fill(title)
        modal.get_by_role("button", name="Upload").click()
        modal.wait_for(state="hidden")

    def save_draft(self):
        self.page.get_by_role("button", name="Save draft").click()
        self.page.locator(".messages .success").wait_for()
        self.assertEqual(self.js_errors, [])

    def get_saved_value(self):
        page = GalleryPage.objects.get(pk=self.gallery_page.pk)
        body = page.get_latest_revision_as_object().body
        self.assertEqual(len(body), 1)
        return body[0].value


class TestMultipleChooserBlockEditing(EditingTestCase):
    def test_starts_empty(self):
        self.add_block("Images")
        # No empty chooser, only the "+" button to open the chooser with
        expect(self.list_add_buttons()).to_have_count(1)
        expect(self.page.locator("[id$='-chooser']")).to_have_count(0)

    def test_choose_multiple(self):
        self.add_block("Images")
        self.choose(self.green, self.red, self.blue)
        self.save_draft()
        self.assertCountEqual(self.get_saved_value(), [self.red, self.green, self.blue])

    def test_choose_one(self):
        self.add_block("Images")
        self.choose(self.red)
        self.save_draft()
        self.assertEqual(list(self.get_saved_value()), [self.red])

    def test_upload_in_chooser(self):
        # An upload in the chooser returns a single item
        path = os.path.join(tempfile.mkdtemp(), "white.png")
        self.addCleanup(shutil.rmtree, os.path.dirname(path))
        PILImage.new("RGB", (40, 40), color="white").save(path)

        self.add_block("Images")
        self.choose(self.red)
        self.upload_image(path, "White", add_button=1)
        self.save_draft()
        self.assertEqual([image.title for image in self.get_saved_value()], ["Red", "White"])

    def test_insert_at_position(self):
        self.add_block("Images")
        self.choose(self.red)
        self.choose(self.blue, add_button=1)
        self.choose(self.green, add_button=1)
        self.save_draft()
        self.assertEqual(list(self.get_saved_value()), [self.red, self.green, self.blue])

    def test_struct_block(self):
        self.add_block("Captioned images")
        self.choose(self.red, self.green)
        self.page.locator("input[name$='-caption']").first.fill("A caption")
        self.save_draft()
        value = self.get_saved_value()
        self.assertCountEqual([item["image"] for item in value], [self.red, self.green])
        self.assertCountEqual([item["caption"] for item in value], ["A caption", ""])

    def test_image_block(self):
        self.add_block("Image blocks")
        self.choose(self.red, self.green)
        # ImageBlock requires alt text, unless the image is decorative
        for checkbox in self.page.locator("input[name$='-decorative']").all():
            checkbox.check()
        self.save_draft()
        self.assertCountEqual(
            [image.pk for image in self.get_saved_value()],
            [self.red.pk, self.green.pk],
        )

    def test_documents(self):
        documents = [
            Document.objects.create(
                title=title,
                file=SimpleUploadedFile(f"{title}.txt", b"Content", "text/plain"),
            )
            for title in ["Menu", "Price list"]
        ]
        self.add_block("Documents")
        self.choose(*documents)
        self.save_draft()
        self.assertCountEqual(self.get_saved_value(), documents)

    def test_pages(self):
        # Top level pages, which the page chooser shows first
        pages = [
            self.root_page.add_child(instance=Page(title=title, slug=title.lower()))
            for title in ["About", "Contact"]
        ]
        self.add_block("Pages")
        self.choose(*pages)
        self.save_draft()
        self.assertCountEqual(
            [page.pk for page in self.get_saved_value()], [page.pk for page in pages]
        )

    def test_snippets(self):
        authors = [Author.objects.create(name=name) for name in ["Ada", "Grace"]]
        self.add_block("Authors")
        self.choose(*authors)
        self.save_draft()
        self.assertCountEqual(self.get_saved_value(), authors)

    def test_duplicates_allowed_by_default(self):
        self.add_block("Images")
        self.choose(self.red)
        self.choose(self.red, add_button=1)
        self.save_draft()
        self.assertEqual(list(self.get_saved_value()), [self.red, self.red])

    def test_allow_duplicates_false(self):
        self.add_block("Unique images")
        self.choose(self.red)

        # The items in the list can't be selected again
        self.list_add_buttons().nth(1).click()
        expect(self.checkbox(self.red)).to_be_disabled()
        self.checkbox(self.green).check()
        self.confirm()

        self.save_draft()
        self.assertEqual(list(self.get_saved_value()), [self.red, self.green])

    def test_max_num(self):
        self.add_block("Three images")
        self.choose(self.red)

        # Only two more items fit, so the others can't be selected
        self.list_add_buttons().first.click()
        self.checkbox(self.green).check()
        self.checkbox(self.blue).check()
        expect(self.checkbox(self.black)).to_be_disabled()
        self.checkbox(self.blue).uncheck()
        expect(self.checkbox(self.black)).to_be_enabled()
        self.checkbox(self.black).check()
        self.confirm()

        self.save_draft()
        self.assertEqual(list(self.get_saved_value()), [self.green, self.black, self.red])

    def test_max_num_disables_add_buttons(self):
        self.add_block("Three images")
        self.choose(self.red, self.green, self.blue)
        expect(self.list_add_buttons()).to_have_count(4)
        for button in self.list_add_buttons().all():
            expect(button).to_be_disabled()

        self.page.get_by_role("button", name="Delete").last.click()
        expect(self.list_add_buttons().first).to_be_enabled()

    def test_edit_existing_value(self):
        self.gallery_page.body = [("images", [self.red, self.green])]
        self.gallery_page.save_revision()
        self.page.reload()
        expect(self.list_add_buttons()).to_have_count(3)

        self.choose(self.blue, self.black, add_button=2)
        self.save_draft()
        self.assertEqual(
            list(self.get_saved_value()), [self.red, self.green, self.blue, self.black]
        )

    def test_selection_kept_when_searching(self):
        self.add_block("Images")
        self.list_add_buttons().first.click()
        self.checkbox(self.red).check()

        search = self.page.locator(".modal #id_q")
        search.fill("Green")
        expect(self.checkbox(self.red)).to_have_count(0)
        self.checkbox(self.green).check()
        expect(self.pills()).to_have_text(["Red", "Green"])
        search.fill("")
        expect(self.checkbox(self.red)).to_be_checked()

        self.confirm()
        self.save_draft()
        self.assertCountEqual(self.get_saved_value(), [self.red, self.green])

    @override_settings(WAGTAILIMAGES_CHOOSER_PAGE_SIZE=2)
    def test_selection_kept_when_paginating(self):
        # The newest images come first: black and blue, then green and red
        self.add_block("Images")
        self.list_add_buttons().first.click()
        self.checkbox(self.black).check()

        modal = self.page.locator(".modal")
        modal.get_by_role("link", name="Next").click()
        self.checkbox(self.red).check()
        modal.get_by_role("link", name="Previous").click()
        expect(self.checkbox(self.black)).to_be_checked()

        self.confirm()
        self.save_draft()
        self.assertCountEqual(self.get_saved_value(), [self.black, self.red])

    def test_remove_selected_item_with_pill(self):
        self.add_block("Images")
        self.list_add_buttons().first.click()
        self.checkbox(self.red).check()
        self.checkbox(self.green).check()

        remove_button = self.pills().filter(has_text="Red").get_by_role("button", name="Clear")
        expect(remove_button).to_have_accessible_description("Red")
        remove_button.click()
        expect(self.pills()).to_have_text(["Green"])
        expect(self.checkbox(self.red)).not_to_be_checked()

        self.confirm()
        self.save_draft()
        self.assertEqual(list(self.get_saved_value()), [self.green])


class TestBulkUpload(EditingTestCase):
    """The bulk upload contrib app: Wagtail's bulk upload in the chooser."""

    def setUp(self):
        super().setUp()
        self.upload_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.upload_dir)

    def upload_file(self, name, content=None):
        path = os.path.join(self.upload_dir, name)
        if content is None:
            # A colour of its own, or Wagtail sees a duplicate
            color = tuple(ord(character) * 7 % 256 for character in name[:3])
            PILImage.new("RGB", (40, 40), color=color).save(path)
        else:
            with open(path, "w") as file:
                file.write(content)
        return path

    def upload(self, *paths):
        """Upload files with the bulk upload in the chooser's upload tab."""
        self.page.locator(".modal").get_by_role("tab", name="Upload").click()
        self.page.locator(".modal #fileupload").set_input_files(list(paths))

    def rows(self, status=""):
        return self.page.locator(f"#upload-list > li{status}")

    def messages(self):
        """The messages of the uploads that add an item."""
        return self.rows(".upload-success").locator(".status-msg.success")

    def confirm_uploads(self):
        self.page.locator("[data-multiple-chooser-block-bulk-upload] [type=submit]").click()
        self.page.locator(".modal").wait_for(state="hidden")

    def check_decorative(self):
        # ImageBlock requires alt text, unless the image is decorative
        for checkbox in self.page.locator("input[name$='-decorative']").all():
            checkbox.check()

    def test_upload_images(self):
        self.add_block("Bulk images")
        self.list_add_buttons().first.click()
        self.checkbox(self.red).check()

        # Once uploaded, the images are added along with the selected image
        self.upload(self.upload_file("sourdough.png"), self.upload_file("rye.png"))
        self.page.locator(".modal").wait_for(state="hidden")

        self.check_decorative()
        self.save_draft()
        titles = [image.title for image in self.get_saved_value()]
        self.assertEqual(len(titles), 3)
        self.assertIn("Red", titles)
        self.assertEqual(Image.objects.count(), 6)

    def test_invalid_file(self):
        self.add_block("Bulk images")
        self.list_add_buttons().first.click()
        self.upload(
            self.upload_file("sourdough.png"),
            self.upload_file("notes.txt", "Not an image"),
        )
        # The chooser stays open with the status of each upload
        expect(self.messages()).to_have_text(["Image 'sourdough' added."])
        expect(self.rows(".upload-failure")).to_have_count(1)
        self.confirm_uploads()

        self.check_decorative()
        self.save_draft()
        self.assertEqual(len(self.get_saved_value()), 1)

    @override_settings(WAGTAILIMAGES_IMAGE_FORM_BASE="tests.testapp.forms.SourceImageForm")
    def test_fill_in_upload_form(self):
        self.add_block("Bulk images")
        self.list_add_buttons().first.click()
        self.upload(self.upload_file("sourdough.png"))
        # The image is saved once its form is filled in, and its row stays
        self.page.get_by_label("Source").fill("Bakery")
        self.page.get_by_role("button", name="Update").click()
        expect(self.messages()).to_have_text(["Image 'sourdough.png' added."])
        expect(self.page.get_by_label("Source")).to_have_count(0)
        self.confirm_uploads()

        self.check_decorative()
        self.save_draft()
        titles = [image.title for image in self.get_saved_value()]
        self.assertEqual(titles, ["sourdough.png"])

    def test_duplicates(self):
        self.add_block("Bulk images")
        self.list_add_buttons().first.click()
        red = self.upload_file("red.png")
        with open(red, "wb") as file:
            file.write(image_file("red").read())
        self.red.get_file_hash()
        # The same colour as sourdough.png, and the same file as the Red image
        self.upload(self.upload_file("sourdough.png"), self.upload_file("sour.png"), red)
        # The choice of Wagtail's image chooser, after which the row shows the image used
        self.rows().nth(1).get_by_role("button", name="Use new image").click()
        self.rows().nth(2).get_by_role("button", name="Use existing and delete new").click()
        expect(self.messages()).to_have_text(
            ["Image 'sourdough' added.", "Image 'sour' added.", "Image 'Red' added."]
        )
        expect(self.rows().nth(2).locator(".left")).to_contain_text("Red")
        self.confirm_uploads()

        self.check_decorative()
        self.save_draft()
        titles = [image.title for image in self.get_saved_value()]
        self.assertCountEqual(titles, ["sourdough", "sour", "Red"])
        # As in Wagtail's chooser, the new image is deleted when using the existing one
        self.assertEqual(Image.objects.count(), 6)

    def test_upload_documents(self):
        self.add_block("Bulk documents")
        self.list_add_buttons().first.click()
        self.upload(
            self.upload_file("menu.txt", "Menu"),
            self.upload_file("prices.txt", "Prices"),
        )
        self.page.locator(".modal").wait_for(state="hidden")

        self.save_draft()
        self.assertEqual(len(self.get_saved_value()), 2)
        self.assertEqual(Document.objects.count(), 2)
