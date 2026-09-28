# Avaliação & Bonificação

Aplicação interna para cadastro de colaboradores, avaliação semanal, adicional fixo de monitoria e fechamento de bonificação da operação de estoque e expedição.

## Stack atual

- **Next.js 16 + React 19 + TypeScript** com App Router;
- **Node.js 24** no runtime padrão da Vercel (Fluid Compute);
- **PostgreSQL/Supabase** já existente, acessado somente no servidor;
- **Postgres.js** com uma conexão por instância e prepared statements desativados para o Transaction pooler;
- **Server Components** para leituras e **Server Actions** para mutações;
- **ExcelJS** e **pdf-lib** para exportações.

A versão Streamlit foi mantida nos arquivos Python como referência temporária da migração. O deploy da Vercel usa `package.json`, `src/app` e `vercel.ts`; nenhum processo Python é necessário em produção.

## Funcionalidades migradas

- login compatível com os hashes PBKDF2 já gravados em `login_users`;
- criação do primeiro administrador;
- perfis `admin` e `avaliador`, com vínculo ao avaliador operacional;
- cadastro, edição, ativação e desativação de funcionários;
- avaliação semanal em quatro semanas fixas, com faixas de pagamento e justificativas;
- catálogo corporativo A01–A08, Q01–Q04, P01–P04 e C01–C04, com desconto automático por pontos;
- adicional fixo de monitoria de R$ 300,00, sem avaliação mensal;
- fechamento mensal com cobertura, pendências, valores e adicional por tempo de empresa;
- exportação do fechamento em CSV e PDF;
- exportação da semana em XLSX.
- importação transacional do lote semanal em XLSX.

As RPCs antigas de produtividade de Picking e Packing/By-Box não fazem parte da aplicação Vercel. Itens e produtividade são preenchidos diretamente ou importados pelo XLSX.

## Configuração local

Requisitos: Node.js 24 e acesso ao banco Supabase atual.

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Preencha `.env.local`:

```dotenv
DATABASE_URL="postgresql://postgres.PROJECT_REF:SENHA@POOLER_HOST:6543/postgres?sslmode=require"
SESSION_SECRET="um-segredo-longo-com-pelo-menos-32-caracteres"
```

Use a URL do **Transaction pooler** do Supabase, normalmente na porta `6543`. O código usa `max: 1`, `prepare: false` e SSL obrigatório para o ambiente serverless.

O schema continua versionado em `supabase/migrations/`. Se o banco já era usado pela versão Streamlit, não há migração de dados: as mesmas tabelas são reutilizadas.

## Verificação

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

## Deploy na Vercel

1. Importe o repositório na Vercel.
2. Cadastre `DATABASE_URL` e `SESSION_SECRET` nos ambientes desejados.
3. Confirme Node.js 24 nas configurações do projeto.
4. Publique; o framework e o build são declarados em `vercel.ts`.

Também é possível usar a CLI:

```powershell
npx vercel link
npx vercel env add DATABASE_URL
npx vercel env add SESSION_SECRET
npx vercel deploy
```

Não coloque a senha do banco ou `SESSION_SECRET` em variáveis `NEXT_PUBLIC_*`.

## Estrutura principal

```text
src/app/                 rotas, páginas, Server Actions e exportações
src/components/          componentes da interface
src/lib/                 autenticação, banco, regras, datas e relatórios
supabase/migrations/     schema PostgreSQL existente
vercel.ts                configuração do projeto Vercel
```

Detalhes da decisão técnica e do corte de migração estão em [docs/MIGRACAO_VERCEL.md](docs/MIGRACAO_VERCEL.md).
As regras implementadas e a ordem do cálculo estão documentadas em [docs/REGRAS_CALCULO.md](docs/REGRAS_CALCULO.md).
