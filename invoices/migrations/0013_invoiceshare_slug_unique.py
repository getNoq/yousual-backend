from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0012_backfill_share_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceshare',
            name='slug',
            field=models.CharField(blank=True, db_index=True, max_length=12, unique=True),
        ),
    ]