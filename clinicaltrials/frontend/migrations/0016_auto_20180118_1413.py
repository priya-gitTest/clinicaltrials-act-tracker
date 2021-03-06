# Generated by Django 2.0 on 2018-01-18 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0015_auto_20180117_1307'),
    ]

    operations = [
        migrations.AddField(
            model_name='trial',
            name='is_pact',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='trial',
            name='status',
            field=models.CharField(choices=[('overdue', 'Overdue'), ('ongoing', 'Ongoing'), ('reported', 'Reported'), ('reported-late', 'Reported (late)'), ('unknown', 'Unknown')], default='unknown', max_length=20),
        ),
    ]
