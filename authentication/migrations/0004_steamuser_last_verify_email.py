# Generated by Django 3.1.7 on 2021-03-23 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_auto_20210323_1614'),
    ]

    operations = [
        migrations.AddField(
            model_name='steamuser',
            name='last_verify_email',
            field=models.IntegerField(default=0),
        ),
    ]