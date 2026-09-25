import os
import tempfile

SECRET_KEY = "test-secret-key-not-for-production"

INSTALLED_APPS = [
    "wagtail_multiple_chooser_block",
    "wagtail_multiple_chooser_block.contrib.bulk_upload",
    "tests.testapp",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        # A file, so the live server's threads each get their own connection.
        # Requests at the same time, like autosave and preview, fail otherwise.
        # In a temporary directory, so test runs in parallel don't share it.
        "TEST": {"NAME": os.path.join(tempfile.mkdtemp(), "test.sqlite3")},
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

USE_TZ = True

WAGTAIL_SITE_NAME = "Test"
WAGTAILADMIN_BASE_URL = "http://testserver"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
