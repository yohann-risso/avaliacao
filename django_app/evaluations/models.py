"""Mappings for the existing Supabase tables.

They are intentionally unmanaged: the Streamlit app and Django can coexist while
the migration happens, and the versioned Supabase SQL remains the schema source.
"""
from django.db import models


class LegacyLoginUser(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.TextField()
    password_hash = models.TextField()
    role = models.TextField(default="admin")
    evaluator_employee_id = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    last_login_at = models.TextField(blank=True, default="")
    created_at = models.TextField()
    updated_at = models.TextField(blank=True, default="")

    class Meta:
        managed = False
        db_table = "login_users"
        ordering = ["username"]

    @property
    def is_admin(self) -> bool:
        return self.active and self.role == "admin"


class Employee(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField()
    sector = models.TextField()
    role = models.TextField()
    hire_date = models.CharField(max_length=10, blank=True, default="")
    monitor_start_date = models.CharField(max_length=10, blank=True, default="")
    leadership_start_date = models.CharField(max_length=10, blank=True, default="")
    termination_date = models.CharField(max_length=10, blank=True, default="")
    picking_operator_name = models.TextField(blank=True, default="")
    bybox_operator_name = models.TextField(blank=True, default="")
    is_monitor = models.BooleanField(default=False)
    is_leadership = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    deactivated_at = models.TextField(blank=True, default="")
    created_at = models.TextField()
    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_by_username = models.TextField(blank=True, default="")
    updated_by_user_id = models.IntegerField(null=True, blank=True)
    updated_by_username = models.TextField(blank=True, default="")
    updated_at = models.TextField(blank=True, default="")

    class Meta:
        managed = False
        db_table = "employees"
        ordering = ["sector", "role", "name"]

    def __str__(self) -> str:
        return self.name


class WeeklyEvaluation(models.Model):
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, db_column="employee_id", on_delete=models.DO_NOTHING, related_name="weekly_evaluations")
    week_start = models.CharField(max_length=10)
    evaluator = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    assiduidade_pct = models.FloatField(default=100)
    qualidade_pct = models.FloatField(default=100)
    taxa_erros_pct = models.FloatField(default=100)
    produtividade_pct = models.FloatField(default=100)
    comportamento_pct = models.FloatField(default=100)
    efficiency_pct = models.FloatField(default=100)
    items_count = models.IntegerField(default=0)
    created_at = models.TextField()
    assiduidade_just = models.TextField(blank=True, default="")
    qualidade_just = models.TextField(blank=True, default="")
    taxa_erros_just = models.TextField(blank=True, default="")
    produtividade_just = models.TextField(blank=True, default="")
    comportamento_just = models.TextField(blank=True, default="")

    class Meta:
        managed = False
        db_table = "weekly_evaluations"
        unique_together = [("employee", "week_start")]
        ordering = ["-week_start", "employee__name"]


class WeeklyError(models.Model):
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, db_column="employee_id", on_delete=models.DO_NOTHING, related_name="weekly_errors")
    week_start = models.CharField(max_length=10)
    role_snapshot = models.TextField()
    error_type = models.TextField()
    severity = models.TextField()
    qty = models.IntegerField(default=1)
    notes = models.TextField(blank=True, default="")
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = "weekly_errors"
        ordering = ["-week_start", "employee__name", "id"]


class MonitorMonthlyEvaluation(models.Model):
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, db_column="employee_id", on_delete=models.DO_NOTHING, related_name="monthly_evaluations")
    month = models.CharField(max_length=7)
    evaluator = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    acomp_metas_pct = models.FloatField(default=100)
    org_fluxo_pct = models.FloatField(default=100)
    suporte_equipe_pct = models.FloatField(default=100)
    disciplina_oper_pct = models.FloatField(default=100)
    created_at = models.TextField()
    acomp_metas_just = models.TextField(blank=True, default="")
    org_fluxo_just = models.TextField(blank=True, default="")
    suporte_equipe_just = models.TextField(blank=True, default="")
    disciplina_oper_just = models.TextField(blank=True, default="")

    class Meta:
        managed = False
        db_table = "monitor_monthly_evaluations"
        unique_together = [("employee", "month")]
        ordering = ["-month", "employee__name"]
