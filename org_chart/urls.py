from django.urls import path
from . import views

app_name = 'org_chart'

urlpatterns = [
    path('', views.OrgChartView.as_view(), name='index'),
    path('api/tree/<int:company_id>/', views.TreeDataView.as_view(), name='tree_data'),
    path('api/node/<str:node_type>/<int:node_id>/', views.NodeDetailView.as_view(), name='node_detail'),
    path('api/search/', views.SearchView.as_view(), name='search'),
    path('api/move/', views.MoveNodeView.as_view(), name='move_node'),
    path('api/assign-user/', views.AssignUserView.as_view(), name='assign_user'),
    path('api/assign-role/', views.AssignRoleView.as_view(), name='assign_role'),
    path('api/add-node/', views.AddNodeView.as_view(), name='add_node'),
    path('api/delete-node/', views.DeleteNodeView.as_view(), name='delete_node'),
    path('api/rename-node/', views.RenameNodeView.as_view(), name='rename_node'),
    path('api/history/<str:node_type>/<int:node_id>/', views.NodeHistoryView.as_view(), name='node_history'),
    path('api/employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('api/roles/', views.RoleListView.as_view(), name='role_list'),
    path('api/permissions/<int:position_id>/', views.PositionPermissionsView.as_view(), name='position_permissions'),
]
