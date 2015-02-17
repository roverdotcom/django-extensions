import pytest

import django
from django.db import models
from django.test import TestCase
from django_extensions.db.fields import AutoSlugField

from .testapp.models import ChildSluggedTestModel, SluggedTestModel


if django.VERSION >= (1, 7):
    from django.db import migrations  # NOQA
    from django.db.migrations.writer import MigrationWriter  # NOQA
    from django.utils import six  # NOQA
    import django_extensions  # NOQA


@pytest.mark.usefixtures("admin_user")
class AutoSlugFieldTest(TestCase):
    def tearDown(self):
        super(AutoSlugFieldTest, self).tearDown()

        SluggedTestModel.objects.all().delete()

    def testAutoCreateSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()
        self.assertEqual(m.slug, 'foo')

    def testAutoCreateNextSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()

        m = SluggedTestModel(title='foo')
        m.save()
        self.assertEqual(m.slug, 'foo-2')

    def testAutoCreateSlugWithNumber(self):
        m = SluggedTestModel(title='foo 2012')
        m.save()
        self.assertEqual(m.slug, 'foo-2012')

    def testAutoUpdateSlugWithNumber(self):
        m = SluggedTestModel(title='foo 2012')
        m.save()
        m.save()
        self.assertEqual(m.slug, 'foo-2012')

    def testUpdateSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()
        self.assertEqual(m.slug, 'foo')

        # update m instance without using `save'
        SluggedTestModel.objects.filter(pk=m.pk).update(slug='foo-2012')
        # update m instance with new data from the db
        m = SluggedTestModel.objects.get(pk=m.pk)
        self.assertEqual(m.slug, 'foo-2012')

        m.save()
        self.assertEqual(m.title, 'foo')
        self.assertEqual(m.slug, 'foo-2012')

        # Check slug is not overwrite
        m.title = 'bar'
        m.save()
        self.assertEqual(m.title, 'bar')
        self.assertEqual(m.slug, 'foo-2012')

    def testSimpleSlugSource(self):
        m = SluggedTestModel(title='-foo')
        m.save()
        self.assertEqual(m.slug, 'foo')

        n = SluggedTestModel(title='-foo')
        n.save()
        self.assertEqual(n.slug, 'foo-2')

        n.save()
        self.assertEqual(n.slug, 'foo-2')

    def testEmptySlugSource(self):
        # regression test

        m = SluggedTestModel(title='')
        m.save()
        self.assertEqual(m.slug, '-2')

        n = SluggedTestModel(title='')
        n.save()
        self.assertEqual(n.slug, '-3')

        n.save()
        self.assertEqual(n.slug, '-3')

    def testInheritanceCreatesNextSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()

        n = ChildSluggedTestModel(title='foo')
        n.save()
        self.assertEqual(n.slug, 'foo-2')

        o = SluggedTestModel(title='foo')
        o.save()
        self.assertEqual(o.slug, 'foo-3')


@pytest.mark.skipif(django.VERSION < (1, 7),
                    reason="Migrations are handled by south in Django <1.7")
class TestMigration(TestCase):
    def safe_exec(self, string, value=None):
        l = {}
        try:
            exec(string, globals(), l)
        except Exception as e:
            if value:
                self.fail("Could not exec %r (from value %r): %s" % (string.strip(), value, e))
            else:
                self.fail("Could not exec %r: %s" % (string.strip(), e))
        return l

    def test_17_migration(self):
        """
        Tests making migrations with Django 1.7+'s migration framework
        """

        fields = {
            'autoslugfield': AutoSlugField(populate_from='otherfield'),
        }

        migration = type(str("Migration"), (migrations.Migration,), {
            "operations": [
                migrations.CreateModel("MyModel", tuple(fields.items()),
                                       {'populate_from': 'otherfield'},
                                       (models.Model,)),
            ],
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        # It should NOT be unicode.
        self.assertIsInstance(output, six.binary_type,
                              "Migration as_string returned unicode")
        # We don't test the output formatting - that's too fragile.
        # Just make sure it runs for now, and that things look alright.
        result = self.safe_exec(output)
        self.assertIn("Migration", result)
