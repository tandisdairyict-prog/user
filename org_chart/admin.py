from django.contrib import admin
from .models import (
    Company, Department, Role, AppPermission, Position, PositionRole,
    Employee, UserPosition, RolePermission, UserPermissionOverride, AuditLog
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'registration_number', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'name_en', 'registration_number']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'parent', 'is_active', 'order']
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'code']
    raw_id_fields = ['parent']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'permission_count', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']

    @admin.display(description='تعداد دسترسی')
    def permission_count(self, obj):
        return obj.permission_count


@admin.register(AppPermission)
class AppPermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'codename', 'category']
    list_filter = ['category']
    search_fields = ['name', 'codename']


class PositionRoleInline(admin.TabularInline):
    model = PositionRole
    extra = 1


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'department', 'parent', 'is_active', 'subordinate_count']
    list_filter = ['department__company', 'is_active']
    search_fields = ['title', 'code']
    raw_id_fields = ['parent']
    inlines = [PositionRoleInline]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'personnel_number', 'email', 'phone', 'is_active', 'hire_date']
    list_filter = ['is_active']
    search_fields = ['first_name', 'last_name', 'personnel_number', 'email']


@admin.register(UserPosition)
class UserPositionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'position', 'is_primary', 'is_active', 'start_date', 'end_date']
    list_filter = ['is_active', 'is_primary']
    search_fields = ['employee__first_name', 'employee__last_name', 'position__title']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission']
    list_filter = ['role']


@admin.register(UserPermissionOverride)
class UserPermissionOverrideAdmin(admin.ModelAdmin):
    list_display = ['employee', 'permission', 'override_type', 'created_at']
    list_filter = ['override_type']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'entity_type', 'entity_name', 'performed_by', 'created_at']
    list_filter = ['action', 'entity_type']
    readonly_fields = ['action', 'entity_type', 'entity_id', 'entity_name',
                       'description', 'performed_by', 'created_at']
