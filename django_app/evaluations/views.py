from __future__ import annotations

from datetime import datetime
from io import BytesIO

from django.contrib import messages
from django.db import IntegrityError, connection, transaction
from django.http import Http404, HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
import pandas as pd

from constants import MONITOR_MONTHLY_TOTAL

from .auth import admin_required, login_required, request_user, verify_legacy_password
from .forms import (
    EmployeeForm,
    LegacyUserForm,
    LoginForm,
    MonitorEvaluationForm,
    WeeklyErrorForm,
    WeeklyEvaluationForm,
    SpreadsheetImportForm,
)
from .models import Employee, LegacyLoginUser, MonitorMonthlyEvaluation, WeeklyError, WeeklyEvaluation
from .services import default_month, now_text, today_week_start, weekly_preview


def _password_hash(password: str) -> str:
    import hashlib
    import secrets

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


def _auditor(request):
    user = request_user(request)
    return (user.id if user else None, user.username if user else "")


def login_view(request):
    if request_user(request):
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].strip()
        user = LegacyLoginUser.objects.filter(username__iexact=username, active=True).first()
        if user and verify_legacy_password(form.cleaned_data["password"], user.password_hash):
            request.session.cycle_key()
            request.session["legacy_user_id"] = user.id
            request.session["legacy_username"] = user.username
            LegacyLoginUser.objects.filter(pk=user.pk).update(last_login_at=now_text(), updated_at=now_text())
            return redirect("dashboard")
        form.add_error(None, "Usuário ou senha inválidos.")
    return render(request, "evaluations/login.html", {"form": form})


@require_POST
def logout_view(request):
    request.session.flush()
    return redirect("login")


@login_required
def dashboard(request):
    month = request.GET.get("month", default_month())
    stats = {
        "employees": Employee.objects.filter(active=True).count(),
        "monitors": Employee.objects.filter(active=True, is_monitor=True, is_leadership=False).count(),
        "leadership": Employee.objects.filter(active=True, is_leadership=True).count(),
        "weekly": WeeklyEvaluation.objects.filter(week_start=request.GET.get("week", today_week_start())).count(),
    }
    return render(request, "evaluations/dashboard.html", {"stats": stats, "month": month})


@admin_required
def employee_list(request):
    queryset = Employee.objects.all() if request.GET.get("inactive") == "1" else Employee.objects.filter(active=True)
    search = request.GET.get("q", "").strip()
    if search:
        from django.db.models import Q
        queryset = queryset.filter(Q(name__icontains=search) | Q(sector__icontains=search) | Q(role__icontains=search))
    page = Paginator(queryset, 50).get_page(request.GET.get("page"))
    return render(request, "evaluations/employee_list.html", {"employees": page, "page_obj": page, "query": search})


@admin_required
def employee_form(request, employee_id: int | None = None):
    employee = get_object_or_404(Employee, pk=employee_id) if employee_id else Employee(created_at=now_text())
    form = EmployeeForm(request.POST or None, instance=employee)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        user_id, username = _auditor(request)
        if employee_id is None:
            record.created_at = now_text()
            record.created_by_user_id = user_id
            record.created_by_username = username
        record.updated_at = now_text()
        record.updated_by_user_id = user_id
        record.updated_by_username = username
        if not record.active and not record.deactivated_at:
            record.deactivated_at = now_text()
        if record.active:
            record.deactivated_at = ""
        record.save()
        messages.success(request, "Funcionário salvo.")
        return redirect("employee_list")
    return render(request, "evaluations/employee_form.html", {"form": form, "employee": employee})


@admin_required
def user_list(request):
    users = LegacyLoginUser.objects.all()
    return render(request, "evaluations/user_list.html", {"users": users})


@admin_required
def user_form(request, user_id: int | None = None):
    legacy = get_object_or_404(LegacyLoginUser, pk=user_id) if user_id else None
    initial = None
    if legacy:
        initial = {"username": legacy.username, "role": legacy.role, "active": legacy.active, "evaluator_employee": legacy.evaluator_employee_id}
    form = LegacyUserForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].strip()
        duplicate = LegacyLoginUser.objects.filter(username__iexact=username).exclude(pk=user_id).exists()
        if duplicate:
            form.add_error("username", "Já existe um usuário com esse nome.")
        elif not legacy and not form.cleaned_data["password"]:
            form.add_error("password", "A senha é obrigatória para um novo usuário.")
        else:
            evaluator = form.cleaned_data["evaluator_employee"]
            if legacy is None:
                legacy = LegacyLoginUser(
                    username=username,
                    password_hash=_password_hash(form.cleaned_data["password"]),
                    role=form.cleaned_data["role"],
                    evaluator_employee_id=evaluator.id if evaluator else None,
                    active=form.cleaned_data["active"],
                    created_at=now_text(),
                    updated_at=now_text(),
                )
            else:
                legacy.username = username
                legacy.role = form.cleaned_data["role"]
                legacy.evaluator_employee_id = evaluator.id if evaluator else None
                legacy.active = form.cleaned_data["active"]
                legacy.updated_at = now_text()
                if form.cleaned_data["password"]:
                    legacy.password_hash = _password_hash(form.cleaned_data["password"])
            legacy.save()
            messages.success(request, "Usuário salvo.")
            return redirect("user_list")
    return render(request, "evaluations/user_form.html", {"form": form, "legacy": legacy})


@login_required
def weekly_list(request):
    week_start = request.GET.get("week", today_week_start())
    evaluations = WeeklyEvaluation.objects.filter(week_start=week_start).select_related("employee")
    page = Paginator(evaluations, 50).get_page(request.GET.get("page"))
    return render(request, "evaluations/weekly_list.html", {"evaluations": page, "page_obj": page, "week_start": week_start})


@login_required
def weekly_form(request, evaluation_id: int | None = None):
    evaluation = get_object_or_404(WeeklyEvaluation, pk=evaluation_id) if evaluation_id else None
    initial = {"week_start": request.GET.get("week", today_week_start())}
    user = request_user(request)
    if user and user.evaluator_employee_id:
        evaluator = Employee.objects.filter(pk=user.evaluator_employee_id).values_list("name", flat=True).first()
        if evaluator:
            initial["evaluator"] = evaluator
    form = WeeklyEvaluationForm(request.POST or None, instance=evaluation, initial=initial if not evaluation else None)
    if request.method == "POST" and form.is_valid():
        candidate = form.save(commit=False)
        existing = WeeklyEvaluation.objects.filter(employee=candidate.employee, week_start=candidate.week_start).exclude(pk=candidate.pk).first()
        if existing:
            candidate.pk = existing.pk
            candidate.created_at = existing.created_at
        else:
            candidate.created_at = now_text()
        candidate.save()
        messages.success(request, "Avaliação semanal salva.")
        return redirect("weekly_errors", evaluation_id=candidate.pk)
    return render(request, "evaluations/weekly_form.html", {"form": form, "evaluation": evaluation})


@login_required
def weekly_errors(request, evaluation_id: int):
    evaluation = get_object_or_404(WeeklyEvaluation.objects.select_related("employee"), pk=evaluation_id)
    errors = WeeklyError.objects.filter(employee=evaluation.employee, week_start=evaluation.week_start)
    form = WeeklyErrorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        error = form.save(commit=False)
        error.employee = evaluation.employee
        error.week_start = evaluation.week_start
        error.role_snapshot = evaluation.employee.role
        error.created_at = now_text()
        error.save()
        messages.success(request, "Erro semanal registrado.")
        return redirect("weekly_errors", evaluation_id=evaluation.id)
    return render(request, "evaluations/weekly_errors.html", {
        "evaluation": evaluation, "errors": errors, "form": form, "preview": weekly_preview(evaluation),
    })


@login_required
def weekly_error_import(request):
    form = SpreadsheetImportForm(request.POST or None, request.FILES or None, initial={"week_start": today_week_start()})
    summary = None
    if request.method == "POST" and form.is_valid():
        try:
            from weekly_error_import import load_weekly_error_import_file, prepare_weekly_error_import

            employees_df = pd.DataFrame.from_records(Employee.objects.filter(active=True).values("id", "name", "sector", "role"))
            prepared = prepare_weekly_error_import(
                load_weekly_error_import_file(form.cleaned_data["file"]),
                employees_df,
                form.cleaned_data["week_start"].isoformat() if form.cleaned_data["week_start"] else "",
            )
            rows = [WeeklyError(
                employee_id=row["employee_id"], week_start=row["week_start_iso"], role_snapshot=row["role_snapshot"],
                error_type=row["error_type"], severity=row["severity"], qty=row["qty"], notes=row["notes"],
                created_at=row["created_at"] or now_text(),
            ) for row in prepared["valid_rows"]]
            with transaction.atomic():
                WeeklyError.objects.bulk_create(rows, batch_size=500)
            summary = prepared["summary"]
            messages.success(request, f"{len(rows)} erro(s) importado(s).")
        except Exception as exc:
            form.add_error(None, f"Não foi possível importar a planilha: {exc}")
    return render(request, "evaluations/spreadsheet_import.html", {"form": form, "summary": summary, "title": "Importar erros semanais", "back_url": "weekly_list"})


@login_required
def weekly_metrics(request):
    """Load picking and by-box data on demand, never during a generic page render."""
    week_start = request.GET.get("week", today_week_start())
    try:
        from picking_metrics import fetch_weekly_picking_metrics_for_employees

        source = pd.DataFrame.from_records(Employee.objects.filter(active=True, is_leadership=False).values(
            "id", "name", "sector", "role", "picking_operator_name", "bybox_operator_name"
        ))
        metrics, warnings = fetch_weekly_picking_metrics_for_employees(source, week_start)
        rows = []
        for employee in source.to_dict("records"):
            metric = metrics.get(employee["id"], {})
            rows.append({**employee, **metric})
    except Exception as exc:
        rows, warnings = [], [str(exc)]
    return render(request, "evaluations/weekly_metrics.html", {"week_start": week_start, "rows": rows, "warnings": warnings})


@login_required
@require_POST
def weekly_error_delete(request, evaluation_id: int, error_id: int):
    evaluation = get_object_or_404(WeeklyEvaluation, pk=evaluation_id)
    error = get_object_or_404(WeeklyError, pk=error_id, employee=evaluation.employee, week_start=evaluation.week_start)
    error.delete()
    messages.success(request, "Erro removido.")
    return redirect("weekly_errors", evaluation_id=evaluation_id)


@login_required
def monitor_list(request):
    month = request.GET.get("month", default_month())
    evaluations = MonitorMonthlyEvaluation.objects.filter(month=month).select_related("employee")
    page = Paginator(evaluations, 50).get_page(request.GET.get("page"))
    return render(request, "evaluations/monitor_list.html", {"evaluations": page, "page_obj": page, "month": month})


@login_required
def monitor_form(request, evaluation_id: int | None = None):
    evaluation = get_object_or_404(MonitorMonthlyEvaluation, pk=evaluation_id) if evaluation_id else None
    form = MonitorEvaluationForm(request.POST or None, instance=evaluation, initial={"month": request.GET.get("month", default_month())} if not evaluation else None)
    if request.method == "POST" and form.is_valid():
        candidate = form.save(commit=False)
        existing = MonitorMonthlyEvaluation.objects.filter(employee=candidate.employee, month=candidate.month).exclude(pk=candidate.pk).first()
        if existing:
            candidate.pk = existing.pk
            candidate.created_at = existing.created_at
        else:
            candidate.created_at = now_text()
        candidate.save()
        messages.success(request, "Monitoria salva.")
        return redirect("monitor_list")
    return render(request, "evaluations/monitor_form.html", {"form": form, "evaluation": evaluation, "total": MONITOR_MONTHLY_TOTAL})


@admin_required
def reports(request):
    month = request.GET.get("month", default_month())
    include_inactive = request.GET.get("inactive", "1") == "1"
    try:
        from ui_report import build_month_df
        report_df, weeks = build_month_df(month, include_inactive=include_inactive)
        rows = report_df.to_dict("records") if not report_df.empty else []
        columns = list(report_df.columns) if not report_df.empty else []
    except Exception as exc:
        messages.error(request, f"Não foi possível montar o relatório: {exc}")
        rows, columns, weeks = [], [], []
    return render(request, "evaluations/reports.html", {"month": month, "rows": rows, "columns": columns, "weeks": weeks, "include_inactive": include_inactive})


@admin_required
def report_csv(request):
    month = request.GET.get("month", default_month())
    from ui_report import build_month_df
    report_df, _ = build_month_df(month, include_inactive=True)
    response = HttpResponse(report_df.to_csv(index=False).encode("utf-8-sig"), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="fechamento-{month}.csv"'
    return response


@admin_required
def report_pdf(request):
    """Reuse the audited ReportLab builder while the UI migrates away from Streamlit."""
    month = request.GET.get("month", default_month())
    from ui_report import build_month_df, build_report_pdf_bytes_executivo, fetch_weekly_evaluations_for_weeks

    report_df, weeks = build_month_df(month, include_inactive=True)
    weekly_join = fetch_weekly_evaluations_for_weeks(weeks)
    pdf = build_report_pdf_bytes_executivo(
        df_pdf=report_df,
        month=month,
        coordinator_name=request_user(request).username,
        report_observation="",
        weeks_iso=weeks,
        weekly_join_df=weekly_join,
    )
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="fechamento-{month}.pdf"'
    return response


def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
