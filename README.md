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

## Login

O app cria automaticamente a tabela `login_users` no SQLite. No primeiro acesso, quando ainda não houver usuários cadastrados, a tela inicial permite criar o primeiro administrador. Depois disso, o menu do sistema só aparece após login.

A senha é gravada com hash PBKDF2, não em texto puro.

## Publicando no Streamlit Community Cloud

O projeto já está organizado para deploy no Streamlit Cloud:

- Repositório: `yohann-risso/avaliacao`
- Branch: `main`
- Arquivo principal: `app.py`
- Dependências: `requirements.txt`
- Tema: `.streamlit/config.toml`

No painel do [Streamlit Community Cloud](https://share.streamlit.io/), clique em **Create app**, selecione o repositório acima e informe `app.py` como entrypoint. Em **Advanced settings**, escolha Python 3.13 para manter a mesma versão usada no desenvolvimento local.

Observação importante: o app usa SQLite local (`avaliacoes.db`). No Streamlit Community Cloud, arquivos locais podem ser apagados em reinícios/redeploys da aplicação. Para uso real com vários usuários ou dados que não podem ser perdidos, migre o banco para PostgreSQL/Supabase antes de operar em produção.

## Direção de UI/UX

O app deve parecer uma ferramenta operacional: claro, confiável, direto e fácil de revisar. A navegação segue o fluxo real do trabalho:

1. Funcionários
2. Avaliação Semanal
3. Monitoria Mensal
4. Relatório Mensal

As decisões visuais e de interação estão documentadas em [STYLE_GUIDE.md](STYLE_GUIDE.md).
