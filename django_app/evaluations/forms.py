from __future__ import annotations

from django import forms

from constants import DEFAULT_ERROR_TYPES, SEVERITIES

from .models import Employee, MonitorMonthlyEvaluation, WeeklyError, WeeklyEvaluation


class LoginForm(forms.Form):
    username = forms.CharField(label="Usuário", max_length=120)
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "name", "sector", "role", "hire_date", "monitor_start_date", "leadership_start_date",
            "termination_date", "picking_operator_name", "bybox_operator_name", "is_monitor", "is_leadership", "active",
        ]
        widgets = {
            "hire_date": forms.DateInput(attrs={"type": "date"}),
            "monitor_start_date": forms.DateInput(attrs={"type": "date"}),
            "leadership_start_date": forms.DateInput(attrs={"type": "date"}),
            "termination_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_leadership") and cleaned.get("is_monitor"):
            self.add_error("is_monitor", "Coordenação/supervisão não pode ser monitor.")
        if not cleaned.get("hire_date"):
            self.add_error("hire_date", "A data de contratação é obrigatória.")
        if cleaned.get("is_monitor") and not cleaned.get("monitor_start_date"):
            self.add_error("monitor_start_date", "Informe o início da monitoria.")
        if cleaned.get("is_leadership") and not cleaned.get("leadership_start_date"):
            self.add_error("leadership_start_date", "Informe o início na liderança.")
        return cleaned


class LegacyUserForm(forms.Form):
    username = forms.CharField(label="Usuário", max_length=120)
    password = forms.CharField(label="Senha", required=False, min_length=8, widget=forms.PasswordInput)
    role = forms.ChoiceField(label="Perfil", choices=(("avaliador", "Avaliador"), ("admin", "Administrador")))
    evaluator_employee = forms.ModelChoiceField(label="Avaliador vinculado", queryset=Employee.objects.none(), required=False)
    active = forms.BooleanField(label="Ativo", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evaluator_employee"].queryset = Employee.objects.filter(active=True, is_leadership=True).order_by("name")

    def clean_password(self):
        password = self.cleaned_data["password"]
        if password and (not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password)):
            raise forms.ValidationError("A senha deve combinar letras e números.")
        return password


class WeeklyEvaluationForm(forms.ModelForm):
    class Meta:
        model = WeeklyEvaluation
        fields = [
            "employee", "week_start", "evaluator", "items_count", "efficiency_pct", "assiduidade_pct", "qualidade_pct",
            "taxa_erros_pct", "produtividade_pct", "comportamento_pct", "notes", "assiduidade_just", "qualidade_just",
            "taxa_erros_just", "produtividade_just", "comportamento_just",
        ]
        widgets = {"week_start": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = Employee.objects.filter(active=True, is_leadership=False).order_by("sector", "role", "name")
        for field in ("efficiency_pct", "assiduidade_pct", "qualidade_pct", "taxa_erros_pct", "produtividade_pct", "comportamento_pct"):
            self.fields[field].min_value = 0
            self.fields[field].max_value = 100


class WeeklyErrorForm(forms.ModelForm):
    class Meta:
        model = WeeklyError
        fields = ["error_type", "severity", "qty", "notes"]

    error_type = forms.ChoiceField(choices=[(item, item) for item in DEFAULT_ERROR_TYPES])
    severity = forms.ChoiceField(choices=[(item, item.title()) for item in SEVERITIES])
    qty = forms.IntegerField(min_value=1, initial=1)


class SpreadsheetImportForm(forms.Form):
    file = forms.FileField(label="Planilha XLSX")
    week_start = forms.DateField(label="Semana", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    confirm = forms.BooleanField(label="Confirmo a gravação das linhas válidas", required=True)


class MonitorEvaluationForm(forms.ModelForm):
    class Meta:
        model = MonitorMonthlyEvaluation
        fields = [
            "employee", "month", "evaluator", "acomp_metas_pct", "org_fluxo_pct", "suporte_equipe_pct",
            "disciplina_oper_pct", "notes", "acomp_metas_just", "org_fluxo_just", "suporte_equipe_just", "disciplina_oper_just",
        ]
        widgets = {"month": forms.TextInput(attrs={"type": "month"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = Employee.objects.filter(active=True, is_monitor=True, is_leadership=False).order_by("name")
        for field in ("acomp_metas_pct", "org_fluxo_pct", "suporte_equipe_pct", "disciplina_oper_pct"):
            self.fields[field].min_value = 0
            self.fields[field].max_value = 100
