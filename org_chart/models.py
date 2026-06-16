from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    name = models.CharField(max_length=200, verbose_name='نام شرکت')
    name_en = models.CharField(max_length=200, blank=True, verbose_name='نام انگلیسی')
    logo = models.ImageField(upload_to='logos/', null=True, blank=True, verbose_name='لوگو')
    registration_number = models.CharField(max_length=100, blank=True, verbose_name='شماره ثبت')
    website = models.URLField(blank=True, verbose_name='وب‌سایت')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ویرایش')

    class Meta:
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        related_name='departments', verbose_name='شرکت'
    )
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='children',
        verbose_name='واحد والد'
    )
    name = models.CharField(max_length=200, verbose_name='نام واحد')
    code = models.CharField(max_length=50, unique=True, verbose_name='کد واحد')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    manager_name = models.CharField(max_length=200, blank=True, verbose_name='نام مدیر')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    order = models.IntegerField(default=0, verbose_name='ترتیب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ویرایش')

    class Meta:
        verbose_name = 'واحد سازمانی'
        verbose_name_plural = 'واحدهای سازمانی'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.company.name} / {self.name}"

    @property
    def employee_count(self):
        return UserPosition.objects.filter(
            position__department=self, is_active=True
        ).count()

    @property
    def all_employee_count(self):
        total = self.employee_count
        for child in self.children.filter(is_active=True):
            total += child.all_employee_count
        return total


class Role(models.Model):
    name = models.CharField(max_length=200, verbose_name='نام نقش')
    code = models.CharField(max_length=100, unique=True, verbose_name='کد نقش')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    class Meta:
        verbose_name = 'نقش'
        verbose_name_plural = 'نقش‌ها'

    def __str__(self):
        return self.name

    @property
    def permission_count(self):
        return self.role_permissions.count()


class AppPermission(models.Model):
    CATEGORY_CHOICES = [
        ('hr', 'منابع انسانی'),
        ('finance', 'مالی'),
        ('it', 'فناوری اطلاعات'),
        ('admin', 'مدیریتی'),
        ('report', 'گزارش'),
        ('other', 'سایر'),
    ]
    name = models.CharField(max_length=200, verbose_name='نام دسترسی')
    codename = models.CharField(max_length=200, unique=True, verbose_name='کد دسترسی')
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES,
        default='other', verbose_name='دسته‌بندی'
    )
    description = models.TextField(blank=True, verbose_name='توضیحات')

    class Meta:
        verbose_name = 'دسترسی'
        verbose_name_plural = 'دسترسی‌ها'

    def __str__(self):
        return f"{self.name} ({self.codename})"


class Position(models.Model):
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE,
        related_name='positions', verbose_name='واحد'
    )
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='children',
        verbose_name='پست والد'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان پست')
    code = models.CharField(max_length=50, unique=True, verbose_name='کد پست')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    order = models.IntegerField(default=0, verbose_name='ترتیب')
    roles = models.ManyToManyField(
        Role, through='PositionRole',
        blank=True, verbose_name='نقش‌ها'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ویرایش')

    class Meta:
        verbose_name = 'پست سازمانی'
        verbose_name_plural = 'پست‌های سازمانی'
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.department.name} / {self.title}"

    @property
    def assigned_employee(self):
        up = self.user_positions.filter(is_active=True, is_primary=True).first()
        return up.employee if up else None

    @property
    def subordinate_count(self):
        return self.children.filter(is_active=True).count()

    @property
    def primary_role(self):
        pr = self.position_roles.select_related('role').first()
        return pr.role if pr else None

    @property
    def permission_count(self):
        total = 0
        for pr in self.position_roles.select_related('role'):
            total += pr.role.permission_count
        return total

    @property
    def user_override_count(self):
        emp = self.assigned_employee
        if emp:
            return emp.permission_overrides.count()
        return 0


class PositionRole(models.Model):
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='position_roles'
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('position', 'role')
        verbose_name = 'نقش پست'
        verbose_name_plural = 'نقش‌های پست'

    def __str__(self):
        return f"{self.position.title} - {self.role.name}"


class Employee(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employee',
        verbose_name='کاربر سیستم'
    )
    personnel_number = models.CharField(
        max_length=50, unique=True, verbose_name='شماره پرسنلی'
    )
    first_name = models.CharField(max_length=100, verbose_name='نام')
    last_name = models.CharField(max_length=100, verbose_name='نام خانوادگی')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    phone = models.CharField(max_length=20, blank=True, verbose_name='تلفن')
    national_id = models.CharField(max_length=20, blank=True, verbose_name='کد ملی')
    avatar = models.ImageField(
        upload_to='avatars/', null=True, blank=True, verbose_name='تصویر'
    )
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    hire_date = models.DateField(null=True, blank=True, verbose_name='تاریخ استخدام')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ویرایش')

    class Meta:
        verbose_name = 'پرسنل'
        verbose_name_plural = 'پرسنل'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        initials = (self.first_name[0] if self.first_name else '') + \
                   (self.last_name[0] if self.last_name else '')
        return None


class UserPosition(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE,
        related_name='user_positions', verbose_name='پرسنل'
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE,
        related_name='user_positions', verbose_name='پست'
    )
    is_primary = models.BooleanField(default=True, verbose_name='پست اصلی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    start_date = models.DateField(verbose_name='تاریخ شروع')
    end_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پایان')
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_positions', verbose_name='تخصیص‌دهنده'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تخصیص پرسنل'
        verbose_name_plural = 'تخصیص‌های پرسنل'

    def __str__(self):
        return f"{self.employee.full_name} - {self.position.title}"


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name='role_permissions'
    )
    permission = models.ForeignKey(AppPermission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('role', 'permission')
        verbose_name = 'دسترسی نقش'
        verbose_name_plural = 'دسترسی‌های نقش'

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class UserPermissionOverride(models.Model):
    OVERRIDE_CHOICES = [
        ('grant', 'اعطای دسترسی'),
        ('deny', 'سلب دسترسی'),
    ]
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE,
        related_name='permission_overrides', verbose_name='پرسنل'
    )
    permission = models.ForeignKey(
        AppPermission, on_delete=models.CASCADE, verbose_name='دسترسی'
    )
    override_type = models.CharField(
        max_length=10, choices=OVERRIDE_CHOICES, verbose_name='نوع'
    )
    reason = models.TextField(blank=True, verbose_name='دلیل')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='ایجادکننده'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'permission')
        verbose_name = 'استثنای دسترسی'
        verbose_name_plural = 'استثناهای دسترسی'

    def __str__(self):
        return f"{self.employee.full_name} - {self.permission.name} ({self.override_type})"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'ایجاد'),
        ('update', 'ویرایش'),
        ('delete', 'حذف'),
        ('assign', 'تخصیص'),
        ('move', 'جابجایی'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='عملیات')
    entity_type = models.CharField(max_length=50, verbose_name='نوع موجودیت')
    entity_id = models.IntegerField(verbose_name='شناسه موجودیت')
    entity_name = models.CharField(max_length=200, verbose_name='نام موجودیت')
    description = models.TextField(verbose_name='توضیحات')
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name='انجام‌دهنده'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ')

    class Meta:
        verbose_name = 'لاگ عملیات'
        verbose_name_plural = 'لاگ‌های عملیات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.entity_type} #{self.entity_id}"
