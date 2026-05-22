# Avaliação & Bonificação

App interno para cadastro de colaboradores, avaliação semanal, monitoria mensal e fechamento de bonificação da operação de estoque e expedição.

## Stack escolhida

- **Python 3.13**: linguagem principal do app.
- **Streamlit**: interface rápida para uso administrativo interno, com menor custo de manutenção que um frontend separado.
- **PostgreSQL/Supabase**: banco oficial da aplicação, com persistência e uso multiusuário.
- **Pandas**: leitura, cálculo e montagem de tabelas para revisão e fechamento.
- **ReportLab**: geração dos PDFs de fechamento, assinatura e anexos.
- **CSS customizado em `theme.py`**: identidade visual própria sem adicionar complexidade de frontend.

Essa stack prioriza velocidade de uso, baixa fricção de manutenção e operação multiusuário. O banco da aplicação é o Supabase; bancos SQLite locais são ignorados pelo repositório e só devem ser usados como origem temporária de migração ou apoio de testes.

## Rodando localmente

```powershell
python -m pip install -r requirements.txt
# configure APP_DATABASE_URL antes de iniciar
python -m streamlit run app.py
```

Um modelo de secrets esta em `.streamlit/secrets.toml.example`.

## Login

O app cria automaticamente a tabela `login_users` no banco configurado. No primeiro acesso, quando ainda não houver usuários cadastrados, a tela inicial permite criar o primeiro administrador. Depois disso, o menu do sistema só aparece após login.

A senha é gravada com hash PBKDF2, não em texto puro.

## Banco Supabase/PostgreSQL

O app exige uma connection string PostgreSQL/Supabase em uma destas chaves:

```toml
APP_DATABASE_URL = "postgresql://postgres.pqpvuivefzlkgszwzyzs:SUA_SENHA@aws-1-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require"
```

Também são aceitas `DATABASE_URL`, `SUPABASE_DB_URL`, `[database].url`, `[connections.supabase].url` e `[connections.postgres].url`.

No Streamlit Community Cloud, coloque essa chave em **App settings > Secrets**. Se for necessário repetir a migração de um SQLite local para o Supabase:

```powershell
python scripts/migrate_sqlite_to_supabase.py --sqlite-path ".\avaliacoes.db" --database-url "postgresql://..." --replace
```

Use `--replace` apenas quando houver backup confirmado, porque ele limpa as tabelas antes da importação.

## Publicando no Streamlit Community Cloud

O projeto já está organizado para deploy no Streamlit Cloud:

- Repositório: `yohann-risso/avaliacao`
- Branch: `main`
- Arquivo principal: `app.py`
- Dependências: `requirements.txt`
- Tema: `.streamlit/config.toml`

No painel do [Streamlit Community Cloud](https://share.streamlit.io/), clique em **Create app**, selecione o repositório acima e informe `app.py` como entrypoint. Em **Advanced settings**, escolha Python 3.13 para manter a mesma versão usada no desenvolvimento local.

Observação importante: sem `APP_DATABASE_URL` ou equivalente, o app para na tela inicial com erro de configuração. Ele não usa mais SQLite local como fallback.

## Direção de UI/UX

O app deve parecer uma ferramenta operacional: claro, confiável, direto e fácil de revisar. A navegação segue o fluxo real do trabalho:

1. Funcionários
2. Avaliação Semanal
3. Monitoria Mensal
4. Relatório Mensal

As decisões visuais e de interação estão documentadas em [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md).

## Documentação completa

A documentação da aplicação está em [docs/](docs/):

- [Guia operacional](docs/GUIA_OPERACIONAL.md): uso da app no ciclo mensal.
- [Guia resumido para colaboradores](docs/GUIA_COLABORADORES.md): explicação simples das regras de avaliação e bonificação.
- [Referência técnica](docs/REFERENCIA_TECNICA.md): arquitetura, banco, regras, testes e deploy.
- [Supabase e PostgreSQL](docs/SUPABASE.md): configuração do banco remoto e migração do SQLite.
