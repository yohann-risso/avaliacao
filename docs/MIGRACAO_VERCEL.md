# Migração para Vercel JavaScript

## Decisão

A aplicação passou a ter um frontend e backend web em Next.js/TypeScript, executado no runtime Node.js padrão da Vercel. O PostgreSQL/Supabase existente permanece como fonte oficial; portanto, a migração não duplica o banco nem exige copiar registros.

## Segurança

- A connection string existe somente no servidor.
- O cliente do PostgreSQL é criado no escopo do módulo, com `max: 1`, `prepare: false` e SSL obrigatório.
- Na Vercel, use o Transaction pooler do Supabase (porta 6543). A aplicação converte automaticamente a porta 5432 do host `*.pooler.supabase.com` para 6543 nesse runtime, preservando o projeto e as credenciais. Conexões diretas e execução fora da Vercel permanecem como configuradas.
- O cliente PostgreSQL é reutilizado no processo também em produção. O modo session pode esgotar o limite de clientes entre instâncias serverless (`EMAXCONNSESSION`), mesmo com `max: 1` por instância.
- O timeout ocioso do cliente é de cinco segundos. Nas requisições da Vercel, uma tarefa `after` mantém o processo ativo por mais 5,5 segundos após a resposta, permitindo que o postgres.js feche conexões ociosas antes da suspensão da função. Isso evita reutilizar sockets antigos e deixar o carregamento preso após um período sem acessos.
- O pipelining do postgres.js fica desativado com `max_pipeline: 0`: o Supavisor em modo transação não suporta múltiplas consultas enviadas antecipadamente na mesma conexão. Consultas simultâneas da aplicação aguardam a vez no cliente, sem alterar as transações de gravação.
- As Server Actions e rotas de exportação revalidam autenticação e autorização.
- A sessão é um JWT `HS256` em cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção, com validade de oito horas.
- A função de verificação aceita o formato legado `pbkdf2_sha256$600000$salt$digest`, evitando redefinição de senhas na virada.
- Usuários desativados deixam de passar na validação da sessão imediatamente.
- As tabelas continuam com RLS habilitada e acesso de `anon`/`authenticated` revogado. A aplicação usa a conexão PostgreSQL privada no servidor.

## Mapeamento das telas

| Streamlit | Next.js |
| --- | --- |
| `ui_auth.py` | `/login` + `src/app/actions/auth.ts` |
| `ui_employees.py` | `/funcionarios` |
| `ui_users.py` | `/usuarios` |
| `ui_weekly.py` | `/avaliacoes` |
| `ui_monitor.py` | `/monitoria` |
| `ui_report.py` | `/relatorios` e `/api/export/*` |
| `rules.py` / `utils.py` | `src/lib/rules.ts`, `dates.ts` e `money.ts` |
| `db.py` | `src/lib/db.ts`, `data.ts` e Server Actions |

## Compatibilidade e corte

Os arquivos Python foram preservados para comparação e rollback durante a homologação. O Next.js é o entrypoint oficial da Vercel. Depois da conferência funcional em produção, o código Streamlit pode ser removido em uma alteração separada e explícita.

As RPCs antigas de produtividade de Picking e Packing/By-Box foram removidas. Os mapeamentos de operador também não são usados pelo Next.js. Itens e produtividade são informados diretamente na avaliação ou no lote XLSX. A planilha pode ser exportada, revisada e reimportada; a importação valida o arquivo inteiro antes da transação e gera justificativas auditáveis para descontos.

A competência possui sempre quatro semanas. A nota de cada quesito primeiro passa pela tabela de proporcionalidade (0%, 25%, 50%, 75% ou 100% da verba); em seguida, as ocorrências corporativas aplicam os pontos de desconto, limitados ao valor disponível e aos quesitos indicados pela diretriz. A01 e A06 também produzem efeitos mensais de assiduidade. A reincidência A01 bloqueia o bônus-base mensal.

A monitoria deixou de ter formulário de avaliação. Todo monitor ativo e elegível recebe automaticamente o adicional fixo de R$ 300,00 no fechamento da competência.

## Homologação recomendada

1. Entrar com um usuário existente.
2. Conferir a contagem e os dados de funcionários.
3. Salvar uma avaliação em uma semana de teste e reabrir a mesma semana.
4. Registrar e remover ocorrências por código; conferir pontos e desconto recalculados.
5. Conferir a lista de monitores elegíveis e o adicional fixo de R$ 300,00.
6. Comparar o fechamento de uma competência concluída com o PDF/CSV da versão Streamlit.
7. Validar os dois perfis de acesso.
8. Só então trocar o domínio principal para o deploy da Vercel.
