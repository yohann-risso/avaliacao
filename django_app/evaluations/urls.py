from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("healthz/", views.healthz, name="healthz"),
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/new/", views.employee_form, name="employee_create"),
    path("employees/<int:employee_id>/", views.employee_form, name="employee_edit"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_form, name="user_create"),
    path("users/<int:user_id>/", views.user_form, name="user_edit"),
    path("weekly/", views.weekly_list, name="weekly_list"),
    path("weekly/new/", views.weekly_form, name="weekly_create"),
    path("weekly/errors/import/", views.weekly_error_import, name="weekly_error_import"),
    path("weekly/metrics/", views.weekly_metrics, name="weekly_metrics"),
    path("weekly/<int:evaluation_id>/", views.weekly_form, name="weekly_edit"),
    path("weekly/<int:evaluation_id>/errors/", views.weekly_errors, name="weekly_errors"),
    path("weekly/<int:evaluation_id>/errors/<int:error_id>/delete/", views.weekly_error_delete, name="weekly_error_delete"),
    path("monitoring/", views.monitor_list, name="monitor_list"),
    path("monitoring/new/", views.monitor_form, name="monitor_create"),
    path("monitoring/<int:evaluation_id>/", views.monitor_form, name="monitor_edit"),
    path("reports/", views.reports, name="reports"),
    path("reports/export.csv", views.report_csv, name="report_csv"),
    path("reports/export.pdf", views.report_pdf, name="report_pdf"),
]
