# Supabase e PostgreSQL

Esta aplicacao usa PostgreSQL/Supabase como banco oficial. O arquivo `avaliacoes.db` nao e mais fallback de execucao normal; ele fica apenas como origem de migracao ou apoio em testes locais.

## Variaveis aceitas

A connection string pode vir do ambiente ou dos secrets do Streamlit. A ordem de busca e:

- `APP_DATABASE_URL`;
- `DATABASE_URL`;
- `SUPABASE_DB_URL`;
- `[database].url`;
- `[connections.supabase].url`;
- `[connections.postgres].url`.

Exemplo em `.streamlit/secrets.toml`:

```toml
APP_DATABASE_URL = "postgresql://postgres.PROJECT:SENHA@HOST:5432/postgres?sslmode=require"
```

Use `.streamlit/secrets.toml.example` como modelo. Nao commite o arquivo real de secrets.

## Execucao local

```powershell
python -m pip install -r requirements.txt
$env:APP_DATABASE_URL = "postgresql://..."
python -m streamlit run app.py
```

Se `APP_DATABASE_URL` ou equivalente nao estiver configurado, a app para na inicializacao com uma mensagem de erro. Isso evita gravar acidentalmente em um banco local efemero.

## Streamlit Community Cloud

No Streamlit Cloud:

1. Abra **App settings > Secrets**.
2. Cadastre `APP_DATABASE_URL` com a connection string do Supabase.
3. Prefira a URL do pooler em modo session quando estiver disponivel.
4. Garanta `sslmode=require`.

## Schema

O schema oficial esta em:

```text
supabase/migrations/20260522203641_init_avaliacoes_schema.sql
```

`db.init_postgres_db()` tambem garante as tabelas e colunas necessarias durante a inicializacao da app. A migracao SQL e util para ambientes controlados via Supabase CLI.

Tabelas principais:

- `login_users`;
- `employees`;
- `weekly_evaluations`;
- `weekly_errors`;
- `monitor_monthly_evaluations`.

O schema habilita Row Level Security nas tabelas e revoga acesso direto de `anon` e `authenticated`. A app acessa o banco pela connection string PostgreSQL do servidor.

## Migracao do SQLite

Para importar dados do `avaliacoes.db` para o Supabase:

```powershell
python scripts/migrate_sqlite_to_supabase.py --database-url "postgresql://..."
```

Para substituir dados existentes antes de importar:

```powershell
python scripts/migrate_sqlite_to_supabase.py --database-url "postgresql://..." --replace
```

Use `--replace` somente com backup confirmado, porque ele limpa as tabelas de destino antes da importacao.

O script:

- le as tabelas do SQLite por `id`;
- faz upsert no PostgreSQL com conflito por `id`;
- ressincroniza as sequencias de identity;
- respeita a ordem de delecao quando `--replace` e usado.

## Testes com SQLite

Os testes usam SQLite somente quando `AVALIACAO_ALLOW_SQLITE=1`. O arquivo `tests/conftest.py` define essa variavel por padrao para a suite.

Essa compatibilidade existe para testes rapidos de regra de negocio, sem exigir um Supabase real em cada execucao.

