# Generated by Django 3.0.13 on 2021-03-14 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hyperkitty', '0021_add_owners_mods'),
    ]

    operations = [
        migrations.AddField(
            model_name='mailinglist',
            name='archive_rendering_mode',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
