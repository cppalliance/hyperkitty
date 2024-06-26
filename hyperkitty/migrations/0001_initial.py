# -*- coding: utf-8 -*-
# flake8: noqa
import zoneinfo

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


TIMEZONES = sorted([(tz, tz) for tz in zoneinfo.available_timezones()])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('counter', models.SmallIntegerField()),
                ('name', models.CharField(max_length=255)),
                ('content_type', models.CharField(max_length=255)),
                ('encoding', models.CharField(max_length=255, null=True)),
                ('size', models.IntegerField()),
                ('content', models.BinaryField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message_id', models.CharField(max_length=255, db_index=True)),
                ('message_id_hash', models.CharField(max_length=255, db_index=True)),
                ('subject', models.CharField(max_length='512', db_index=True)),
                ('content', models.TextField()),
                ('date', models.DateTimeField(db_index=True)),
                ('timezone', models.SmallIntegerField()),
                ('in_reply_to', models.CharField(max_length=255, null=True, blank=True)),
                ('archived_date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('thread_depth', models.IntegerField(default=0)),
                ('thread_order', models.IntegerField(default=0, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LastView',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('view_date', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MailingList',
            fields=[
                ('name', models.CharField(max_length=254, serialize=False, primary_key=True)),
                ('display_name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('subject_prefix', models.CharField(max_length=255)),
                ('archive_policy', models.IntegerField(default=2, choices=[(0, 'never'), (1, 'private'), (2, 'public')])),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('karma', models.IntegerField(default=1)),
                ('timezone', models.CharField(default='', max_length=100, choices=TIMEZONES)),
                ('user', models.OneToOneField(related_name='hyperkitty_profile', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sender',
            fields=[
                ('address', models.EmailField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('mailman_id', models.CharField(max_length=255, null=True, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, db_index=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tagging',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.ForeignKey(to='hyperkitty.Tag', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Thread',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('thread_id', models.CharField(max_length=255, db_index=True)),
                ('date_active', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ThreadCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, db_index=True)),
                ('color', models.CharField(max_length=7)),
            ],
            options={
                'verbose_name_plural': 'Thread categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.SmallIntegerField(db_index=True)),
                ('email', models.ForeignKey(related_name='votes', to='hyperkitty.Email', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='votes', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set([('email', 'user')]),
        ),
        migrations.AddField(
            model_name='thread',
            name='category',
            field=models.ForeignKey(related_name='threads', to='hyperkitty.ThreadCategory', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thread',
            name='mailinglist',
            field=models.ForeignKey(related_name='threads', to='hyperkitty.MailingList', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='thread',
            unique_together=set([('mailinglist', 'thread_id')]),
        ),
        migrations.AddField(
            model_name='tagging',
            name='thread',
            field=models.ForeignKey(to='hyperkitty.Thread', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='tagging',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='tag',
            name='threads',
            field=models.ManyToManyField(related_name='tags', through='hyperkitty.Tagging', to='hyperkitty.Thread'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='tag',
            name='users',
            field=models.ManyToManyField(related_name='tags', through='hyperkitty.Tagging', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='lastview',
            name='thread',
            field=models.ForeignKey(related_name='lastviews', to='hyperkitty.Thread', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='lastview',
            name='user',
            field=models.ForeignKey(related_name='lastviews', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='favorite',
            name='thread',
            field=models.ForeignKey(related_name='favorites', to='hyperkitty.Thread', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='favorite',
            name='user',
            field=models.ForeignKey(related_name='favorites', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='email',
            name='mailinglist',
            field=models.ForeignKey(related_name='emails', to='hyperkitty.MailingList', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='email',
            name='parent',
            field=models.ForeignKey(related_name='children',
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    blank=True, to='hyperkitty.Email', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='email',
            name='sender',
            field=models.ForeignKey(related_name='emails', to='hyperkitty.Sender', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='email',
            name='thread',
            field=models.ForeignKey(related_name='emails', to='hyperkitty.Thread', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='email',
            unique_together=set([('mailinglist', 'message_id')]),
        ),
        migrations.AddField(
            model_name='attachment',
            name='email',
            field=models.ForeignKey(related_name='attachments', to='hyperkitty.Email', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='attachment',
            unique_together=set([('email', 'counter')]),
        ),
    ]
