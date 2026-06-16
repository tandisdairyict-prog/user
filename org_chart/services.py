from django.db.models import Q
from .models import (
    Company, Department, Position, Employee, UserPosition,
    Role, PositionRole, AuditLog, AppPermission, UserPermissionOverride
)
import datetime


class OrgChartService:

    @staticmethod
    def get_companies():
        return list(Company.objects.filter(is_active=True).values(
            'id', 'name', 'name_en', 'is_active'
        ))

    @staticmethod
    def get_tree_data(company_id):
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return None

        def build_position_node(position):
            employee = position.assigned_employee
            primary_role = position.primary_role
            child_positions = position.children.filter(is_active=True).order_by('order', 'title')
            return {
                'id': f'pos_{position.id}',
                'db_id': position.id,
                'type': 'position',
                'title': position.title,
                'code': position.code,
                'is_active': position.is_active,
                'subordinate_count': position.subordinate_count,
                'permission_count': position.permission_count,
                'user_override_count': position.user_override_count,
                'role_name': primary_role.name if primary_role else '',
                'roles': [{'id': pr.role.id, 'name': pr.role.name} for pr in
                           position.position_roles.select_related('role').all()],
                'employee': {
                    'id': employee.id,
                    'name': employee.full_name,
                    'personnel_number': employee.personnel_number,
                    'avatar_url': employee.avatar.url if employee.avatar else None,
                } if employee else None,
                'children': [build_position_node(cp) for cp in child_positions],
            }

        def build_department_node(dept):
            child_depts = dept.children.filter(is_active=True).order_by('order', 'name')
            root_positions = dept.positions.filter(
                is_active=True, parent__isnull=True
            ).order_by('order', 'title')
            return {
                'id': f'dept_{dept.id}',
                'db_id': dept.id,
                'type': 'department',
                'name': dept.name,
                'code': dept.code,
                'is_active': dept.is_active,
                'employee_count': dept.all_employee_count,
                'children': (
                    [build_department_node(d) for d in child_depts] +
                    [build_position_node(p) for p in root_positions]
                ),
            }

        root_depts = company.departments.filter(
            is_active=True, parent__isnull=True
        ).order_by('order', 'name')

        return {
            'id': f'company_{company.id}',
            'db_id': company.id,
            'type': 'company',
            'name': company.name,
            'name_en': company.name_en,
            'is_active': company.is_active,
            'logo_url': company.logo.url if company.logo else None,
            'children': [build_department_node(d) for d in root_depts],
        }

    @staticmethod
    def get_node_details(node_type, node_id):
        if node_type == 'company':
            obj = Company.objects.get(id=node_id)
            dept_count = obj.departments.filter(is_active=True).count()
            emp_count = UserPosition.objects.filter(
                position__department__company=obj, is_active=True
            ).count()
            return {
                'type': 'company',
                'id': obj.id,
                'name': obj.name,
                'name_en': obj.name_en,
                'registration_number': obj.registration_number,
                'website': obj.website,
                'description': obj.description,
                'is_active': obj.is_active,
                'department_count': dept_count,
                'employee_count': emp_count,
                'logo_url': obj.logo.url if obj.logo else None,
                'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': obj.updated_at.strftime('%Y-%m-%d %H:%M'),
            }

        elif node_type == 'department':
            obj = Department.objects.select_related('company', 'parent').get(id=node_id)
            pos_count = obj.positions.filter(is_active=True).count()
            return {
                'type': 'department',
                'id': obj.id,
                'name': obj.name,
                'code': obj.code,
                'description': obj.description,
                'company': obj.company.name,
                'company_id': obj.company_id,
                'parent': obj.parent.name if obj.parent else None,
                'parent_id': obj.parent_id,
                'employee_count': obj.all_employee_count,
                'position_count': pos_count,
                'manager_name': obj.manager_name,
                'is_active': obj.is_active,
                'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': obj.updated_at.strftime('%Y-%m-%d %H:%M'),
            }

        elif node_type == 'position':
            obj = Position.objects.select_related(
                'department', 'department__company', 'parent'
            ).prefetch_related('position_roles__role').get(id=node_id)
            employee = obj.assigned_employee
            roles = [{'id': pr.role.id, 'name': pr.role.name, 'code': pr.role.code}
                     for pr in obj.position_roles.select_related('role')]
            return {
                'type': 'position',
                'id': obj.id,
                'title': obj.title,
                'code': obj.code,
                'description': obj.description,
                'department': obj.department.name,
                'department_id': obj.department_id,
                'company': obj.department.company.name,
                'parent': obj.parent.title if obj.parent else None,
                'parent_id': obj.parent_id,
                'is_active': obj.is_active,
                'subordinate_count': obj.subordinate_count,
                'permission_count': obj.permission_count,
                'user_override_count': obj.user_override_count,
                'roles': roles,
                'employee': {
                    'id': employee.id,
                    'name': employee.full_name,
                    'personnel_number': employee.personnel_number,
                    'email': employee.email,
                    'phone': employee.phone,
                    'avatar_url': employee.avatar.url if employee.avatar else None,
                } if employee else None,
                'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': obj.updated_at.strftime('%Y-%m-%d %H:%M'),
            }

        elif node_type == 'employee':
            obj = Employee.objects.get(id=node_id)
            positions = obj.user_positions.filter(is_active=True).select_related(
                'position__department__company'
            )
            pos_list = [{
                'id': up.position.id,
                'title': up.position.title,
                'department': up.position.department.name,
                'company': up.position.department.company.name,
                'is_primary': up.is_primary,
                'start_date': up.start_date.strftime('%Y-%m-%d'),
            } for up in positions]
            return {
                'type': 'employee',
                'id': obj.id,
                'full_name': obj.full_name,
                'first_name': obj.first_name,
                'last_name': obj.last_name,
                'personnel_number': obj.personnel_number,
                'email': obj.email,
                'phone': obj.phone,
                'national_id': obj.national_id,
                'is_active': obj.is_active,
                'hire_date': obj.hire_date.strftime('%Y-%m-%d') if obj.hire_date else None,
                'avatar_url': obj.avatar.url if obj.avatar else None,
                'positions': pos_list,
                'permission_override_count': obj.permission_overrides.count(),
                'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M'),
            }
        return None

    @staticmethod
    def search_nodes(query, company_id=None):
        if not query or len(query.strip()) < 2:
            return []
        q = query.strip()
        results = []
        company_filter = {}
        if company_id:
            company_filter['company_id'] = company_id

        companies = Company.objects.filter(
            Q(name__icontains=q) | Q(name_en__icontains=q)
        )
        for c in companies:
            results.append({
                'id': f'company_{c.id}', 'db_id': c.id, 'type': 'company',
                'name': c.name, 'path': [f'company_{c.id}'],
            })

        dept_q = Q(name__icontains=q) | Q(code__icontains=q)
        if company_id:
            dept_q &= Q(company_id=company_id)
        departments = Department.objects.filter(dept_q, is_active=True).select_related('company')
        for d in departments:
            results.append({
                'id': f'dept_{d.id}', 'db_id': d.id, 'type': 'department',
                'name': d.name, 'path': OrgChartService._get_dept_path(d),
            })

        pos_q = Q(title__icontains=q) | Q(code__icontains=q)
        if company_id:
            pos_q &= Q(department__company_id=company_id)
        positions = Position.objects.filter(pos_q, is_active=True).select_related(
            'department__company'
        )
        for p in positions:
            results.append({
                'id': f'pos_{p.id}', 'db_id': p.id, 'type': 'position',
                'name': p.title, 'path': OrgChartService._get_pos_path(p),
            })

        emp_q = (
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(personnel_number__icontains=q)
        )
        employees = Employee.objects.filter(emp_q, is_active=True)
        for e in employees:
            results.append({
                'id': f'emp_{e.id}', 'db_id': e.id, 'type': 'employee',
                'name': e.full_name, 'path': [],
            })

        return results

    @staticmethod
    def _get_dept_path(dept):
        path = [f'dept_{dept.id}', f'company_{dept.company_id}']
        parent = dept.parent
        while parent:
            path.append(f'dept_{parent.id}')
            parent = parent.parent
        return list(reversed(path))

    @staticmethod
    def _get_pos_path(position):
        path = [f'pos_{position.id}']
        if position.parent:
            path = OrgChartService._get_pos_path(position.parent) + [f'pos_{position.id}']
        dept_path = OrgChartService._get_dept_path(position.department)
        return dept_path + path

    @staticmethod
    def assign_user_to_position(position_id, employee_id, user=None):
        position = Position.objects.get(id=position_id)
        employee = Employee.objects.get(id=employee_id)
        UserPosition.objects.filter(
            position=position, is_active=True, is_primary=True
        ).update(is_active=False)
        up = UserPosition.objects.create(
            employee=employee,
            position=position,
            is_primary=True,
            is_active=True,
            start_date=datetime.date.today(),
            assigned_by=user,
        )
        AuditLog.objects.create(
            action='assign',
            entity_type='position',
            entity_id=position.id,
            entity_name=position.title,
            description=f'پرسنل {employee.full_name} به پست {position.title} تخصیص یافت',
            performed_by=user,
        )
        return up

    @staticmethod
    def assign_role_to_position(position_id, role_id, user=None):
        position = Position.objects.get(id=position_id)
        role = Role.objects.get(id=role_id)
        pr, created = PositionRole.objects.get_or_create(position=position, role=role)
        AuditLog.objects.create(
            action='assign',
            entity_type='position',
            entity_id=position.id,
            entity_name=position.title,
            description=f'نقش {role.name} به پست {position.title} تخصیص یافت',
            performed_by=user,
        )
        return pr

    @staticmethod
    def remove_role_from_position(position_id, role_id, user=None):
        PositionRole.objects.filter(position_id=position_id, role_id=role_id).delete()

    @staticmethod
    def move_node(node_type, node_id, new_parent_id, new_parent_type, user=None):
        if node_type == 'department':
            dept = Department.objects.get(id=node_id)
            if new_parent_type == 'company':
                dept.parent = None
                dept.company_id = new_parent_id
            elif new_parent_type == 'department':
                new_parent = Department.objects.get(id=new_parent_id)
                if new_parent.company_id != dept.company_id:
                    return False, 'جابجایی بین شرکت‌های مختلف مجاز نیست'
                dept.parent = new_parent
            dept.save()
            AuditLog.objects.create(
                action='move',
                entity_type='department',
                entity_id=dept.id,
                entity_name=dept.name,
                description=f'واحد {dept.name} جابجا شد',
                performed_by=user,
            )
            return True, 'جابجایی انجام شد'

        elif node_type == 'position':
            pos = Position.objects.get(id=node_id)
            if new_parent_type == 'position':
                new_parent = Position.objects.get(id=new_parent_id)
                pos.parent = new_parent
                pos.department = new_parent.department
            elif new_parent_type == 'department':
                pos.parent = None
                pos.department_id = new_parent_id
            pos.save()
            AuditLog.objects.create(
                action='move',
                entity_type='position',
                entity_id=pos.id,
                entity_name=pos.title,
                description=f'پست {pos.title} جابجا شد',
                performed_by=user,
            )
            return True, 'جابجایی انجام شد'
        return False, 'نوع نود نامعتبر'

    @staticmethod
    def add_department(company_id, name, code, parent_id=None, user=None):
        dept = Department.objects.create(
            company_id=company_id,
            parent_id=parent_id,
            name=name,
            code=code,
        )
        AuditLog.objects.create(
            action='create',
            entity_type='department',
            entity_id=dept.id,
            entity_name=dept.name,
            description=f'واحد {dept.name} ایجاد شد',
            performed_by=user,
        )
        return dept

    @staticmethod
    def add_position(department_id, title, code, parent_id=None, user=None):
        pos = Position.objects.create(
            department_id=department_id,
            parent_id=parent_id,
            title=title,
            code=code,
        )
        AuditLog.objects.create(
            action='create',
            entity_type='position',
            entity_id=pos.id,
            entity_name=pos.title,
            description=f'پست {pos.title} ایجاد شد',
            performed_by=user,
        )
        return pos

    @staticmethod
    def delete_node(node_type, node_id, user=None):
        if node_type == 'department':
            obj = Department.objects.get(id=node_id)
            name = obj.name
            obj.is_active = False
            obj.save()
            AuditLog.objects.create(
                action='delete', entity_type='department',
                entity_id=node_id, entity_name=name,
                description=f'واحد {name} غیرفعال شد', performed_by=user,
            )
        elif node_type == 'position':
            obj = Position.objects.get(id=node_id)
            name = obj.title
            obj.is_active = False
            obj.save()
            AuditLog.objects.create(
                action='delete', entity_type='position',
                entity_id=node_id, entity_name=name,
                description=f'پست {name} غیرفعال شد', performed_by=user,
            )

    @staticmethod
    def rename_node(node_type, node_id, new_name, user=None):
        if node_type == 'department':
            obj = Department.objects.get(id=node_id)
            old_name = obj.name
            obj.name = new_name
            obj.save()
            AuditLog.objects.create(
                action='update', entity_type='department',
                entity_id=node_id, entity_name=new_name,
                description=f'نام واحد از {old_name} به {new_name} تغییر یافت',
                performed_by=user,
            )
        elif node_type == 'position':
            obj = Position.objects.get(id=node_id)
            old_name = obj.title
            obj.title = new_name
            obj.save()
            AuditLog.objects.create(
                action='update', entity_type='position',
                entity_id=node_id, entity_name=new_name,
                description=f'عنوان پست از {old_name} به {new_name} تغییر یافت',
                performed_by=user,
            )

    @staticmethod
    def get_audit_history(node_type, node_id):
        logs = AuditLog.objects.filter(
            entity_type=node_type, entity_id=node_id
        ).select_related('performed_by').order_by('-created_at')[:50]
        return [{
            'action': log.action,
            'action_display': log.get_action_display(),
            'entity_name': log.entity_name,
            'description': log.description,
            'performed_by': log.performed_by.get_full_name() or log.performed_by.username
            if log.performed_by else 'سیستم',
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M'),
        } for log in logs]

    @staticmethod
    def get_position_permissions(position_id):
        position = Position.objects.get(id=position_id)
        role_perms = {}
        for pr in position.position_roles.select_related('role').prefetch_related(
            'role__role_permissions__permission'
        ):
            role_perms[pr.role.name] = [{
                'id': rp.permission.id,
                'name': rp.permission.name,
                'codename': rp.permission.codename,
                'category': rp.permission.category,
            } for rp in pr.role.role_permissions.select_related('permission')]

        employee = position.assigned_employee
        overrides = []
        if employee:
            overrides = [{
                'id': uo.permission.id,
                'name': uo.permission.name,
                'codename': uo.permission.codename,
                'override_type': uo.override_type,
                'reason': uo.reason,
            } for uo in employee.permission_overrides.select_related('permission')]

        return {
            'position_id': position_id,
            'position_title': position.title,
            'role_permissions': role_perms,
            'user_overrides': overrides,
        }
