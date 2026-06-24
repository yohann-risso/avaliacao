import pandas as pd

from ui_users import (
    _edit_evaluator_options,
    _evaluator_options,
    _label_for_evaluator_id,
)


def test_evaluator_options_keep_duplicate_labels_addressable():
    evaluators = pd.DataFrame([
        {"id": 1, "name": "Yohann Risso", "sector": "", "role": ""},
        {"id": 2, "name": "Yohann Risso", "sector": "", "role": ""},
    ])

    options, mapping = _evaluator_options(evaluators)

    assert "Yohann Risso" in options
    assert "Yohann Risso · ID 2" in options
    assert mapping["Yohann Risso"] == 1
    assert mapping["Yohann Risso · ID 2"] == 2
    assert _label_for_evaluator_id(mapping, 1) == "Yohann Risso"
    assert _label_for_evaluator_id(mapping, 2) == "Yohann Risso · ID 2"


def test_edit_evaluator_options_include_current_link_missing_from_active_list():
    evaluator_options, evaluator_map = _evaluator_options(pd.DataFrame([
        {"id": 1, "name": "Outro Avaliador", "sector": "CD", "role": "Supervisor"},
    ]))
    selected_row = pd.Series({
        "evaluator_employee_id": 99,
        "evaluator_name": "Yohann Risso",
        "evaluator_sector": "",
        "evaluator_role": "",
        "evaluator_active": 1,
        "evaluator_is_leadership": 0,
    })

    edit_options, edit_map, current_label, needs_fix = _edit_evaluator_options(
        evaluator_options,
        evaluator_map,
        selected_row,
    )

    assert needs_fix is True
    assert current_label == "Yohann Risso · vínculo atual"
    assert current_label in edit_options
    assert edit_map[current_label] == 99
