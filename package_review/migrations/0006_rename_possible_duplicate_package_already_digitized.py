# Generated by Django 5.1.1 on 2024-10-15 20:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('package_review', '0005_package_undated_object'),
    ]

    operations = [
        migrations.RenameField(
            model_name='package',
            old_name='possible_duplicate',
            new_name='already_digitized',
        ),
    ]
