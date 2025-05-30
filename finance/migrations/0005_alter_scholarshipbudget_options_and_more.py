# Generated by Django 5.2 on 2025-05-23 11:27

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0003_alter_document_options_document_document_type_and_more'),
        ('finance', '0004_remove_scholarshipbudget_books_allowance_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='scholarshipbudget',
            options={'ordering': ['-created_at'], 'verbose_name': 'ميزانية ابتعاث', 'verbose_name_plural': 'ميزانيات الابتعاث'},
        ),
        migrations.AlterModelOptions(
            name='yearlyscholarshipcosts',
            options={'ordering': ['budget', 'year_number'], 'verbose_name': 'التكاليف السنوية للابتعاث', 'verbose_name_plural': 'التكاليف السنوية للابتعاث'},
        ),
        migrations.AddField(
            model_name='scholarshipbudget',
            name='health_insurance',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='تكلفة التأمين الصحي لجميع السنوات', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='التأمين الصحي'),
        ),
        migrations.AddField(
            model_name='scholarshipbudget',
            name='monthly_stipend',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='إجمالي المخصصات الشهرية لجميع السنوات', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='المخصص الشهري'),
        ),
        migrations.AddField(
            model_name='scholarshipbudget',
            name='other_expenses',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='التأمين على الحياة، النسبة الإضافية، رسوم الفيزا، إلخ', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='مصاريف أخرى'),
        ),
        migrations.AddField(
            model_name='scholarshipbudget',
            name='travel_allowance',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='تكلفة تذاكر السفر', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='مخصص السفر'),
        ),
        migrations.AddField(
            model_name='scholarshipbudget',
            name='tuition_fees',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='إجمالي الرسوم الدراسية بالدينار الأردني', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='الرسوم الدراسية'),
        ),
        migrations.AddField(
            model_name='yearlyscholarshipcosts',
            name='notes',
            field=models.TextField(blank=True, help_text='ملاحظات خاصة بهذه السنة الدراسية', verbose_name='ملاحظات'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='academic_year',
            field=models.CharField(help_text='السنة الدراسية (مثال: 2024-2025)', max_length=20, verbose_name='السنة الدراسية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_budgets', to=settings.AUTH_USER_MODEL, verbose_name='أنشأ بواسطة'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='end_date',
            field=models.DateField(help_text='تاريخ انتهاء صرف الميزانية', verbose_name='تاريخ النهاية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='exchange_rate',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.7100'), help_text='سعر صرف العملة الأجنبية مقابل الدينار الأردني', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.0001'))], verbose_name='سعر الصرف'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='fiscal_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scholarship_budgets', to='finance.fiscalyear', verbose_name='السنة المالية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='foreign_currency',
            field=models.CharField(default='GBP', help_text='رمز العملة الأجنبية (مثل: GBP, USD, EUR)', max_length=3, verbose_name='العملة الأجنبية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='is_current',
            field=models.BooleanField(default=True, help_text='هل هذه هي السنة الدراسية الحالية للمبتعث؟', verbose_name='السنة الحالية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='notes',
            field=models.TextField(blank=True, default=1, help_text='ملاحظات إضافية حول الميزانية', verbose_name='ملاحظات'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='start_date',
            field=models.DateField(help_text='تاريخ بداية صرف الميزانية', verbose_name='تاريخ البداية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='status',
            field=models.CharField(choices=[('draft', 'مسودة'), ('pending', 'قيد المراجعة'), ('active', 'نشطة'), ('closed', 'مغلقة'), ('cancelled', 'ملغية')], default='draft', max_length=20, verbose_name='حالة الميزانية'),
        ),
        migrations.AlterField(
            model_name='scholarshipbudget',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, help_text='إجمالي مبلغ الميزانية بالدينار الأردني', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='إجمالي الميزانية'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='academic_year',
            field=models.CharField(help_text='السنة الدراسية (مثال: 2024-2025)', max_length=20, verbose_name='السنة الدراسية'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='health_insurance',
            field=models.DecimalField(decimal_places=2, default=Decimal('500.00'), help_text='تكلفة التأمين الصحي للسنة بالدينار الأردني', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='التأمين الصحي'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='monthly_allowance',
            field=models.DecimalField(decimal_places=2, default=Decimal('1000.00'), help_text='المبلغ الشهري للمعيشة بالدينار الأردني', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='المخصص الشهري'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='monthly_duration',
            field=models.PositiveSmallIntegerField(default=12, help_text='عدد أشهر صرف المخصص الشهري', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)], verbose_name='عدد الأشهر'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='travel_tickets',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='تكلفة تذاكر السفر للسنة بالدينار الأردني', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='تذاكر السفر'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='tuition_fees_foreign',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='الرسوم الدراسية بالعملة الأجنبية', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='الرسوم الدراسية (عملة أجنبية)'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='tuition_fees_local',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='الرسوم الدراسية بالدينار الأردني', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='الرسوم الدراسية (دينار أردني)'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='visa_fees',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='رسوم الحصول على الفيزا بالدينار الأردني', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='رسوم الفيزا'),
        ),
        migrations.AlterField(
            model_name='yearlyscholarshipcosts',
            name='year_number',
            field=models.PositiveSmallIntegerField(help_text='رقم السنة الدراسية (1، 2، 3، إلخ)', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='رقم السنة'),
        ),
        migrations.AddIndex(
            model_name='scholarshipbudget',
            index=models.Index(fields=['status'], name='finance_sch_status_8e3020_idx'),
        ),
        migrations.AddIndex(
            model_name='scholarshipbudget',
            index=models.Index(fields=['fiscal_year'], name='finance_sch_fiscal__57fd32_idx'),
        ),
        migrations.AddIndex(
            model_name='scholarshipbudget',
            index=models.Index(fields=['academic_year'], name='finance_sch_academi_40e5f1_idx'),
        ),
        migrations.AddIndex(
            model_name='scholarshipbudget',
            index=models.Index(fields=['created_at'], name='finance_sch_created_adb441_idx'),
        ),
        migrations.AddIndex(
            model_name='yearlyscholarshipcosts',
            index=models.Index(fields=['budget', 'year_number'], name='finance_yea_budget__8966c4_idx'),
        ),
        migrations.AddIndex(
            model_name='yearlyscholarshipcosts',
            index=models.Index(fields=['fiscal_year'], name='finance_yea_fiscal__73d031_idx'),
        ),
        migrations.AddIndex(
            model_name='yearlyscholarshipcosts',
            index=models.Index(fields=['academic_year'], name='finance_yea_academi_1b9dcb_idx'),
        ),
    ]
