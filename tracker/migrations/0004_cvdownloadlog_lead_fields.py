from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_cvdownloadlog_visitorlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='cvdownloadlog',
            name='visitor_name',
            field=models.CharField(default='', max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cvdownloadlog',
            name='organization',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='cvdownloadlog',
            name='email',
            field=models.EmailField(default='', max_length=254),
            preserve_default=False,
        ),
    ]
