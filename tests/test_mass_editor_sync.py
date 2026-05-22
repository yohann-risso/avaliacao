import pandas as pd

from ui_weekly import apply_mass_editor_changes


def test_apply_mass_editor_changes_updates_checkbox_and_text():
    df = pd.DataFrame(
        [
            {
                "Selecionar": False,
                "Prioridade": 3,
                "Status": "",
                "Score": 100,
                "Itens": 0,
                "Assiduidade (%)": 100,
                "Qualidade (%)": 100,
                "Taxa Erros (%)": 100,
                "Prod/Efic (%)": 100,
                "Comportamento (%)": 100,
                "Avaliador": "",
                "Assiduidade Just.": "",
                "Qualidade Just.": "",
                "Taxa Erros Just.": "",
                "Produtividade Just.": "",
                "Comportamento Just.": "",
                "Notas": "",
            }
        ]
    )

    synced = apply_mass_editor_changes(
        df,
        {
            "edited_rows": {
                "0": {
                    "Selecionar": True,
                    "Avaliador": "Yohann",
                    "Qualidade (%)": 80,
                }
            }
        },
    )

    assert bool(synced.loc[0, "Selecionar"]) is True
    assert synced.loc[0, "Avaliador"] == "Yohann"
    assert synced.loc[0, "Qualidade (%)"] == 80
    assert synced.loc[0, "Score"] == 96.0
