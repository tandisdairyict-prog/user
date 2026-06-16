import datetime
from django.core.management.base import BaseCommand
from org_chart.models import (
    Company, Department, Position, Employee, UserPosition,
    Role, RolePermission, PositionRole, AppPermission, UserPermissionOverride
)


class Command(BaseCommand):
    help = 'بارگذاری داده‌های نمونه برای نمودار سازمانی'

    def handle(self, *args, **options):
        self.stdout.write('در حال ایجاد داده‌های نمونه...')

        # Permissions
        perms_data = [
            ('مشاهده گزارش منابع انسانی', 'hr.view_report', 'hr'),
            ('ویرایش اطلاعات پرسنلی', 'hr.edit_employee', 'hr'),
            ('تخصیص پست سازمانی', 'hr.assign_position', 'hr'),
            ('مشاهده گزارش مالی', 'finance.view_report', 'finance'),
            ('تایید پرداخت', 'finance.approve_payment', 'finance'),
            ('مدیریت کاربران', 'admin.manage_users', 'admin'),
            ('مدیریت نقش‌ها', 'admin.manage_roles', 'admin'),
            ('دسترسی به پنل مدیریت', 'admin.panel_access', 'admin'),
            ('مشاهده لاگ سیستم', 'it.view_logs', 'it'),
            ('مدیریت زیرساخت', 'it.manage_infra', 'it'),
            ('مشاهده گزارش کلی', 'report.view_all', 'report'),
            ('صدور گزارش اکسل', 'report.export_excel', 'report'),
        ]
        permissions = {}
        for name, codename, category in perms_data:
            p, _ = AppPermission.objects.get_or_create(
                codename=codename,
                defaults={'name': name, 'category': category}
            )
            permissions[codename] = p
        self.stdout.write('  دسترسی‌ها ایجاد شدند.')

        # Roles
        roles_data = [
            ('مدیر ارشد', 'CEO', [
                'admin.manage_users', 'admin.manage_roles', 'admin.panel_access',
                'hr.view_report', 'finance.view_report', 'report.view_all', 'report.export_excel',
            ]),
            ('مدیر', 'MANAGER', [
                'hr.view_report', 'hr.edit_employee', 'hr.assign_position',
                'finance.view_report', 'report.view_all', 'report.export_excel',
            ]),
            ('سرپرست', 'SUPERVISOR', [
                'hr.view_report', 'hr.edit_employee',
                'report.view_all',
            ]),
            ('کارشناس ارشد', 'SENIOR_EXPERT', [
                'hr.view_report', 'report.view_all', 'report.export_excel',
            ]),
            ('کارشناس', 'EXPERT', [
                'hr.view_report', 'report.view_all',
            ]),
            ('مدیر IT', 'IT_MANAGER', [
                'it.view_logs', 'it.manage_infra', 'admin.panel_access',
                'report.view_all',
            ]),
            ('کارشناس شبکه', 'NETWORK_EXPERT', [
                'it.view_logs', 'it.manage_infra',
            ]),
        ]
        roles = {}
        for name, code, perm_codes in roles_data:
            role, created = Role.objects.get_or_create(code=code, defaults={'name': name})
            roles[code] = role
            for pc in perm_codes:
                if pc in permissions:
                    RolePermission.objects.get_or_create(role=role, permission=permissions[pc])
        self.stdout.write('  نقش‌ها ایجاد شدند.')

        # Company
        company, _ = Company.objects.get_or_create(
            name='شرکت فناوری اطلاعات ایران',
            defaults={
                'name_en': 'Iran Information Technology Co.',
                'registration_number': '۱۴۰۰۵۳۲۱',
                'website': 'https://itic.ir',
                'description': 'شرکت پیشرو در حوزه فناوری اطلاعات ایران',
                'is_active': True,
            }
        )
        self.stdout.write(f'  شرکت: {company.name}')

        # Departments
        it_dept, _ = Department.objects.get_or_create(
            code='IT',
            defaults={
                'company': company, 'name': 'فناوری اطلاعات',
                'description': 'واحد فناوری اطلاعات و زیرساخت', 'order': 1
            }
        )
        dev_dept, _ = Department.objects.get_or_create(
            code='IT-DEV',
            defaults={
                'company': company, 'parent': it_dept,
                'name': 'توسعه نرم‌افزار',
                'description': 'تیم توسعه و برنامه‌نویسی', 'order': 1
            }
        )
        infra_dept, _ = Department.objects.get_or_create(
            code='IT-INFRA',
            defaults={
                'company': company, 'parent': it_dept,
                'name': 'زیرساخت و شبکه',
                'description': 'تیم زیرساخت، شبکه و سرور', 'order': 2
            }
        )
        hr_dept, _ = Department.objects.get_or_create(
            code='HR',
            defaults={
                'company': company, 'name': 'منابع انسانی',
                'description': 'واحد منابع انسانی و استخدام', 'order': 2
            }
        )
        finance_dept, _ = Department.objects.get_or_create(
            code='FIN',
            defaults={
                'company': company, 'name': 'مالی و حسابداری',
                'description': 'واحد مالی، حسابداری و بودجه', 'order': 3
            }
        )
        self.stdout.write('  واحدها ایجاد شدند.')

        # Positions
        pos_it_mgr, _ = Position.objects.get_or_create(
            code='POS-IT-MGR',
            defaults={
                'department': it_dept, 'title': 'مدیر فناوری اطلاعات',
                'description': 'مسئولیت کلی واحد IT', 'order': 1
            }
        )
        pos_dev_sup, _ = Position.objects.get_or_create(
            code='POS-DEV-SUP',
            defaults={
                'department': dev_dept, 'parent': pos_it_mgr,
                'title': 'سرپرست توسعه', 'order': 1
            }
        )
        pos_infra_sup, _ = Position.objects.get_or_create(
            code='POS-INFRA-SUP',
            defaults={
                'department': infra_dept, 'parent': pos_it_mgr,
                'title': 'سرپرست زیرساخت', 'order': 2
            }
        )
        pos_senior_dev, _ = Position.objects.get_or_create(
            code='POS-SR-DEV',
            defaults={
                'department': dev_dept, 'parent': pos_dev_sup,
                'title': 'توسعه‌دهنده ارشد', 'order': 1
            }
        )
        pos_dev, _ = Position.objects.get_or_create(
            code='POS-DEV',
            defaults={
                'department': dev_dept, 'parent': pos_dev_sup,
                'title': 'توسعه‌دهنده', 'order': 2
            }
        )
        pos_dev2, _ = Position.objects.get_or_create(
            code='POS-DEV-2',
            defaults={
                'department': dev_dept, 'parent': pos_dev_sup,
                'title': 'توسعه‌دهنده جونیور', 'order': 3
            }
        )
        pos_net, _ = Position.objects.get_or_create(
            code='POS-NET',
            defaults={
                'department': infra_dept, 'parent': pos_infra_sup,
                'title': 'کارشناس شبکه', 'order': 1
            }
        )
        pos_srv, _ = Position.objects.get_or_create(
            code='POS-SRV',
            defaults={
                'department': infra_dept, 'parent': pos_infra_sup,
                'title': 'کارشناس سرور', 'order': 2
            }
        )
        pos_hr_mgr, _ = Position.objects.get_or_create(
            code='POS-HR-MGR',
            defaults={
                'department': hr_dept, 'title': 'مدیر منابع انسانی', 'order': 1
            }
        )
        pos_hr_exp, _ = Position.objects.get_or_create(
            code='POS-HR-EXP',
            defaults={
                'department': hr_dept, 'parent': pos_hr_mgr,
                'title': 'کارشناس منابع انسانی', 'order': 2
            }
        )
        pos_fin_mgr, _ = Position.objects.get_or_create(
            code='POS-FIN-MGR',
            defaults={
                'department': finance_dept, 'title': 'مدیر مالی', 'order': 1
            }
        )
        self.stdout.write('  پست‌ها ایجاد شدند.')

        # Assign roles to positions
        PositionRole.objects.get_or_create(position=pos_it_mgr, role=roles['IT_MANAGER'])
        PositionRole.objects.get_or_create(position=pos_dev_sup, role=roles['SUPERVISOR'])
        PositionRole.objects.get_or_create(position=pos_infra_sup, role=roles['SUPERVISOR'])
        PositionRole.objects.get_or_create(position=pos_senior_dev, role=roles['SENIOR_EXPERT'])
        PositionRole.objects.get_or_create(position=pos_dev, role=roles['EXPERT'])
        PositionRole.objects.get_or_create(position=pos_dev2, role=roles['EXPERT'])
        PositionRole.objects.get_or_create(position=pos_net, role=roles['NETWORK_EXPERT'])
        PositionRole.objects.get_or_create(position=pos_srv, role=roles['NETWORK_EXPERT'])
        PositionRole.objects.get_or_create(position=pos_hr_mgr, role=roles['MANAGER'])
        PositionRole.objects.get_or_create(position=pos_hr_exp, role=roles['EXPERT'])
        PositionRole.objects.get_or_create(position=pos_fin_mgr, role=roles['MANAGER'])

        # Employees
        employees_data = [
            ('علی', 'احمدی', 'EMP001', 'ali.ahmadi@itic.ir', '09121000001', pos_it_mgr),
            ('رضا', 'محمدی', 'EMP002', 'reza.mohammadi@itic.ir', '09121000002', pos_dev_sup),
            ('مریم', 'حسینی', 'EMP003', 'maryam.hosseini@itic.ir', '09121000003', pos_infra_sup),
            ('سارا', 'کریمی', 'EMP004', 'sara.karimi@itic.ir', '09121000004', pos_senior_dev),
            ('محمد', 'رضایی', 'EMP005', 'mohammad.rezaei@itic.ir', '09121000005', pos_dev),
            ('فاطمه', 'موسوی', 'EMP006', 'fatemeh.mousavi@itic.ir', '09121000006', pos_net),
            ('حسین', 'نجفی', 'EMP007', 'hossein.najafi@itic.ir', '09121000007', pos_srv),
            ('زهرا', 'صادقی', 'EMP008', 'zahra.sadeghi@itic.ir', '09121000008', pos_hr_mgr),
            ('امیر', 'تهرانی', 'EMP009', 'amir.tehrani@itic.ir', '09121000009', pos_hr_exp),
            ('نیلوفر', 'بهرامی', 'EMP010', 'nilufar.bahrami@itic.ir', '09121000010', pos_fin_mgr),
        ]
        for first, last, pnum, email, phone, position in employees_data:
            emp, created = Employee.objects.get_or_create(
                personnel_number=pnum,
                defaults={
                    'first_name': first, 'last_name': last,
                    'email': email, 'phone': phone,
                    'is_active': True,
                    'hire_date': datetime.date(2020, 1, 1),
                }
            )
            UserPosition.objects.get_or_create(
                employee=emp, position=position, is_active=True,
                defaults={
                    'is_primary': True,
                    'start_date': datetime.date(2020, 1, 1),
                }
            )
        self.stdout.write('  پرسنل ایجاد شدند.')

        self.stdout.write(self.style.SUCCESS(
            '\nداده‌های نمونه با موفقیت بارگذاری شدند!'
        ))
        self.stdout.write(f'  شرکت: {company.name}')
        self.stdout.write(f'  واحدها: {Department.objects.count()}')
        self.stdout.write(f'  پست‌ها: {Position.objects.count()}')
        self.stdout.write(f'  پرسنل: {Employee.objects.count()}')
        self.stdout.write(f'  نقش‌ها: {Role.objects.count()}')
        self.stdout.write('\nبرای اجرا: python manage.py runserver')
        self.stdout.write('آدرس: http://127.0.0.1:8000/org/')
