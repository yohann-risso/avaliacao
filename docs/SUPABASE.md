# Supabase e PostgreSQL

Esta aplicacao usa PostgreSQL/Supabase como banco oficial. Arquivos SQLite locais, como `avaliacoes.db`, nao sao fallback de execucao normal e ficam ignorados pelo repositorio. Use-os apenas como origem temporaria de migracao ou apoio em testes locais.

## Variaveis aceitas

A connection string pode vir do ambiente ou dos secrets do Streamlit. A ordem de busca e:

- `APP_DATABASE_URL`;
- `DATABASE_URL`;
- `SUPABASE_DB_URL`;
- `[database].url`;
- `[connections.supabase].url`;
- `[connections.postgres].url`.

Para buscar automaticamente pecas e produtividade dos apps de picking, configure explicitamente a fonte externa do projeto `picking-kaisan` (`kinpwzuobsmfkjefnrdc`). Essas RPCs ficam em outro banco, entao a aplicacao nao usa `APP_DATABASE_URL` como fallback.

Opcao recomendada, usando a API do Supabase:

- `PICKING_SUPABASE_URL`;
- `PICKING_SUPABASE_KEY`.

Alternativamente, use uma connection string PostgreSQL somente leitura em uma destas chaves:

- `PICKING_DATABASE_URL`;
- `PICKING_SUPABASE_DB_URL`;
- `PICKING_POSTGRES_URL`;
- `[picking].url`;
- `[connections.picking].url`;
- `[connections.picking_supabase].url`.

Exemplo em `.streamlit/secrets.toml`:

```toml
APP_DATABASE_URL = "postgresql://postgres.PROJECT_REF:SENHA@POOLER_HOST:5432/postgres?sslmode=require"
PICKING_SUPABASE_URL = "https://kinpwzuobsmfkjefnrdc.supabase.co"
PICKING_SUPABASE_KEY = "SUA_SUPABASE_ANON_OU_SERVICE_ROLE_KEY"
```

Use `.streamlit/secrets.toml.example` como modelo. Nao commite o arquivo real de secrets.

As metricas externas usam funcoes RPC do projeto de picking. A chamada de picking espera `fn_eficiencia_por_operador_periodo(date, date, integer, integer)`. A chamada by-box usa preferencialmente a sobrecarga condensada `rpc_bybox_eficiencia_participantes_periodo(timestamptz, timestamptz, boolean)` com `p_condensar_operador = true`; se ela nao existir, cai para a RPC antiga `rpc_bybox_eficiencia_participantes_periodo(timestamptz, timestamptz)`. Se essas funcoes nao existirem no banco configurado, a avaliacao mostra um aviso e nao transforma a falha em itens `0`.

## Execucao local

```powershell
python -m pip install -r requirements.txt
python scripts/configure_supabase.py
python -m streamlit run app.py
```

O script pede a connection string de forma interativa, valida a conexao, garante o schema remoto e grava `.streamlit/secrets.toml`. Se `APP_DATABASE_URL` ou equivalente nao estiver configurado, a app para na inicializacao com uma mensagem de erro. Isso evita gravar acidentalmente em um banco local efemero.

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

`employees` tambem possui os campos opcionais `picking_operator_name` e `bybox_operator_name`. Quando vazios, o nome do funcionario e usado para cruzar com os operadores dos apps de picking.

O schema habilita Row Level Security nas tabelas e revoga acesso direto de `anon` e `authenticated`. A app acessa o banco pela connection string PostgreSQL do servidor.

## Migracao do SQLite

Para importar dados de um SQLite local para o Supabase:

```powershell
python scripts/migrate_sqlite_to_supabase.py --sqlite-path ".\avaliacoes.db" --database-url "postgresql://..."
```

Para substituir dados existentes antes de importar:

```powershell
python scripts/migrate_sqlite_to_supabase.py --sqlite-path ".\avaliacoes.db" --database-url "postgresql://..." --replace
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
