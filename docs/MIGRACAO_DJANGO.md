# Migração Streamlit → Django

## Estado atual

`django_app/` é a substituição web do Streamlit. Ela usa os mesmos dados no Supabase/PostgreSQL e mantém as tabelas legadas como modelos Django não gerenciados. Assim, nenhuma tabela é recriada e o Streamlit pode permanecer em operação durante a validação.

Fluxos já disponíveis no Django:

- login usando os hashes PBKDF2 já gravados em `login_users`;
- gestão de usuários e funcionários;
- avaliação semanal e log de erros;
- consulta sob demanda às métricas de picking e by-box;
- monitoria mensal;
- fechamento mensal e exportação CSV/PDF;
- paginação de listagens e health check em `/healthz/`.

## Execução local

Instale as dependências e forneça segredos apenas pelo ambiente:

```powershell
python -m pip install -r requirements.txt
$env:APP_DATABASE_URL = "postgresql://..."
$env:DJANGO_SECRET_KEY = "uma-chave-longa-e-aleatoria"
$env:DJANGO_DEBUG = "1"
python django_app\manage.py check
python django_app\manage.py test evaluations
python django_app\manage.py runserver
```

Use a string de conexão direta quando o servidor suportar IPv6. Em servidor persistente com rede IPv4, use a string do Supavisor em modo session, na porta `5432`. Não use pooler transaction (`6543`) para este servidor persistente.

## Segurança e Supabase

- O backend Django conecta-se ao PostgreSQL; nenhuma `service_role` ou senha é enviada ao navegador.
- A sessão usa cookie assinado e guarda apenas o identificador do usuário; a conta continua sendo validada no banco a cada requisição.
- O RLS atual e as revogações de `anon`/`authenticated` permanecem inalterados.
- A mudança de exposição automática da Data API não afeta essa arquitetura, pois o app usa PostgreSQL diretamente.
- Guarde `APP_DATABASE_URL` e `DJANGO_SECRET_KEY` no gerenciador de segredos da hospedagem.
- O endpoint `/healthz/` verifica apenas `SELECT 1` e não revela detalhes de conexão.

## Corte de produção

1. Configure uma instância de homologação com cópia anonimizada do banco.
2. Compare três competências reais: totais de pagamento, elegibilidade, checklist e CSV devem coincidir.
3. Mantenha um único escritor por fluxo: quando um módulo Django for liberado, bloqueie sua escrita no Streamlit.
4. Faça backup do Supabase e ensaie a restauração antes da primeira escrita em produção.
5. Liberte inicialmente usuários internos por feature flag ou URL de homologação.
6. Após dois fechamentos confirmados, deixe o Streamlit somente leitura por 7 a 14 dias e então o desative.

## Próximas otimizações sem aumentar a complexidade inicial

- índices e `EXPLAIN ANALYZE` nas consultas reais;
- Redis e fila apenas para PDFs/importações quando os tempos medidos exigirem;
- extração gradual dos builders de relatório para remover a dependência residual de módulos do Streamlit.
