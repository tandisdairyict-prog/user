import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Company, Department, Position, Employee, Role, AppPermission
from .services import OrgChartService


class OrgChartView(View):
    def get(self, request):
        companies = Company.objects.filter(is_active=True)
        selected_company_id = request.GET.get('company', None)
        if not selected_company_id and companies.exists():
            selected_company_id = companies.first().id
        context = {
            'companies': companies,
            'selected_company_id': selected_company_id,
        }
        return render(request, 'org_chart/org_chart.html', context)


class TreeDataView(View):
    def get(self, request, company_id):
        data = OrgChartService.get_tree_data(company_id)
        if data is None:
            return JsonResponse({'error': 'شرکت یافت نشد'}, status=404)
        return JsonResponse({'data': data})


class NodeDetailView(View):
    def get(self, request, node_type, node_id):
        try:
            data = OrgChartService.get_node_details(node_type, node_id)
            if data is None:
                return JsonResponse({'error': 'یافت نشد'}, status=404)
            return JsonResponse({'data': data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class SearchView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        company_id = request.GET.get('company_id', None)
        if company_id:
            try:
                company_id = int(company_id)
            except (ValueError, TypeError):
                company_id = None
        results = OrgChartService.search_nodes(query, company_id)
        return JsonResponse({'results': results, 'count': len(results)})


@method_decorator(csrf_exempt, name='dispatch')
class MoveNodeView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            node_type = body.get('node_type')
            node_id = int(body.get('node_id'))
            new_parent_id = int(body.get('new_parent_id'))
            new_parent_type = body.get('new_parent_type')
            success, message = OrgChartService.move_node(
                node_type, node_id, new_parent_id, new_parent_type,
                user=request.user if request.user.is_authenticated else None
            )
            return JsonResponse({'success': success, 'message': message})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AssignUserView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            position_id = int(body.get('position_id'))
            employee_id = int(body.get('employee_id'))
            up = OrgChartService.assign_user_to_position(
                position_id, employee_id,
                user=request.user if request.user.is_authenticated else None
            )
            return JsonResponse({'success': True, 'message': 'پرسنل با موفقیت تخصیص یافت'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AssignRoleView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            position_id = int(body.get('position_id'))
            role_id = int(body.get('role_id'))
            action = body.get('action', 'assign')
            if action == 'remove':
                OrgChartService.remove_role_from_position(position_id, role_id)
                return JsonResponse({'success': True, 'message': 'نقش حذف شد'})
            else:
                OrgChartService.assign_role_to_position(
                    position_id, role_id,
                    user=request.user if request.user.is_authenticated else None
                )
                return JsonResponse({'success': True, 'message': 'نقش با موفقیت تخصیص یافت'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AddNodeView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            node_type = body.get('node_type')
            name = body.get('name', '').strip()
            code = body.get('code', '').strip()
            parent_id = body.get('parent_id')
            parent_type = body.get('parent_type')
            company_id = body.get('company_id')

            if not name or not code:
                return JsonResponse({'success': False, 'error': 'نام و کد الزامی است'}, status=400)

            user = request.user if request.user.is_authenticated else None

            if node_type == 'department':
                if parent_type == 'department':
                    dept = OrgChartService.add_department(
                        company_id=Department.objects.get(id=parent_id).company_id,
                        name=name, code=code, parent_id=parent_id, user=user
                    )
                else:
                    dept = OrgChartService.add_department(
                        company_id=company_id,
                        name=name, code=code, user=user
                    )
                return JsonResponse({
                    'success': True,
                    'message': 'واحد ایجاد شد',
                    'node_id': f'dept_{dept.id}',
                    'db_id': dept.id,
                })
            elif node_type == 'position':
                if parent_type == 'position':
                    parent_pos = Position.objects.get(id=parent_id)
                    pos = OrgChartService.add_position(
                        department_id=parent_pos.department_id,
                        title=name, code=code, parent_id=parent_id, user=user
                    )
                else:
                    pos = OrgChartService.add_position(
                        department_id=parent_id,
                        title=name, code=code, user=user
                    )
                return JsonResponse({
                    'success': True,
                    'message': 'پست ایجاد شد',
                    'node_id': f'pos_{pos.id}',
                    'db_id': pos.id,
                })
            return JsonResponse({'success': False, 'error': 'نوع نامعتبر'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class DeleteNodeView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            node_type = body.get('node_type')
            node_id = int(body.get('node_id'))
            user = request.user if request.user.is_authenticated else None
            OrgChartService.delete_node(node_type, node_id, user=user)
            return JsonResponse({'success': True, 'message': 'با موفقیت حذف شد'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class RenameNodeView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            node_type = body.get('node_type')
            node_id = int(body.get('node_id'))
            new_name = body.get('new_name', '').strip()
            if not new_name:
                return JsonResponse({'success': False, 'error': 'نام نمی‌تواند خالی باشد'}, status=400)
            user = request.user if request.user.is_authenticated else None
            OrgChartService.rename_node(node_type, node_id, new_name, user=user)
            return JsonResponse({'success': True, 'message': 'نام تغییر یافت'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class NodeHistoryView(View):
    def get(self, request, node_type, node_id):
        history = OrgChartService.get_audit_history(node_type, node_id)
        return JsonResponse({'history': history})


class EmployeeListView(View):
    def get(self, request):
        q = request.GET.get('q', '')
        qs = Employee.objects.filter(is_active=True)
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(personnel_number__icontains=q)
            )
        employees = [{
            'id': e.id,
            'name': e.full_name,
            'personnel_number': e.personnel_number,
            'email': e.email,
            'avatar_url': e.avatar.url if e.avatar else None,
        } for e in qs[:50]]
        return JsonResponse({'employees': employees})


class RoleListView(View):
    def get(self, request):
        roles = [{
            'id': r.id,
            'name': r.name,
            'code': r.code,
            'permission_count': r.permission_count,
        } for r in Role.objects.filter(is_active=True)]
        return JsonResponse({'roles': roles})


class PositionPermissionsView(View):
    def get(self, request, position_id):
        try:
            data = OrgChartService.get_position_permissions(position_id)
            return JsonResponse({'data': data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
