# Avaliação & Bonificação

App interno para cadastro de colaboradores, avaliação semanal, monitoria mensal e fechamento de bonificação da operação de estoque e expedição.

## Stack escolhida

- **Python 3.13**: linguagem principal do app.
- **Streamlit**: interface rápida para uso administrativo interno, com menor custo de manutenção que um frontend separado.
- **SQLite**: banco local simples e suficiente para operação controlada em uma máquina ou rede pequena.
- **Pandas**: leitura, cálculo e montagem de tabelas para revisão e fechamento.
- **ReportLab**: geração dos PDFs de fechamento, assinatura e anexos.
- **CSS customizado em `theme.py`**: identidade visual própria sem adicionar complexidade de frontend.

Essa stack é a melhor escolha para o estágio atual do app porque prioriza velocidade de uso, baixa fricção de instalação e manutenção simples. Se o app virar multiusuário com acesso simultâneo, login e uso remoto, o próximo passo recomendado é manter a lógica em Python e migrar o banco para PostgreSQL/Supabase antes de considerar um frontend separado.

## Rodando localmente

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Direção de UI/UX

O app deve parecer uma ferramenta operacional: claro, confiável, direto e fácil de revisar. A navegação segue o fluxo real do trabalho:

1. Funcionários
2. Avaliação Semanal
3. Monitoria Mensal
4. Relatório Mensal

As decisões visuais e de interação estão documentadas em [STYLE_GUIDE.md](STYLE_GUIDE.md).
