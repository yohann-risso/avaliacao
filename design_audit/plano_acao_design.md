# Plano de ação de design - Avaliação & Bonificação

Data da auditoria: 22/05/2026  
Escopo percorrido: login, funcionários, avaliação semanal individual, avaliação em massa, monitoria mensal, relatório mensal, relatório por setor e detalhado por funcionário.

## Diagnóstico executivo

A app já tem uma boa direção: ferramenta operacional, fluxo mensal claro e CSS centralizado em `theme.py`. O maior ganho agora não vem de trocar framework imediatamente; vem de redesenhar a hierarquia das telas para reduzir esforço de conferência, destacar pendências e transformar tabelas/formulários em superfícies de trabalho mais guiadas.

Recomendação: manter Streamlit no curto prazo, criar uma camada de design system mais explícita e reorganizar as telas críticas. Considerar troca para React/Next.js apenas se a operação exigir edição concorrente, perfis de acesso mais granulares, uso remoto contínuo, notificações, auditoria multiusuário ou integração com ERP/WMS/folha.

## O que aproveitar dos outros apps Kaisan

Foram usados como referência local os projetos `picking-kaisan`, `estoque-kaisan`, `picking-by-box-kaisan` e `rma-kaisan`. Eles já resolvem problemas parecidos de operação, conferência, exceção e painel administrativo, então a melhor estratégia é reaproveitar a linguagem visual e os componentes, não copiar telas inteiras.

| App de referência | O que vale aproveitar | Onde aplicar em Avaliação | Ajuste necessário |
| --- | --- | --- | --- |
| `picking-kaisan` | Cockpit compacto de operador, cartões de item, barra de progresso com percentual forte, badge de sincronização, dropdown de filtros com contador ativo e painel de fila/offline. | Avaliação em massa, checklist mensal, filtros de funcionário/setor/função, status de "último salvamento" e pendências por linha. | Trocar linguagem de picking/endereço por competência, semana, avaliador, justificativa e pagamento estimado. |
| `estoque-kaisan` | Admin cockpit com cards semânticos, stage tiles, foco operacional, listas de exceções e mapas/grades de densidade. | Relatório mensal, relatório por setor, sidebar de processo e tela de monitoria mensal. | Reduzir a ênfase em mapa físico e adaptar para mapa de risco por setor, cobertura e elegibilidade. |
| `picking-by-box-kaisan` | Melhor base de design system: tokens Kaisan, status pills, dark-mode-ready, grids administrativos, action cards e padrões de modal/tabela. | `theme.py` e componentes reutilizáveis: `summary_grid`, `status_chip`, `stage_grid`, `focus_strip`, `action_grid`, tabelas densas. | Usar como fonte de tokens e estados, mas manter a interface mais administrativa e menos scanner-first. |
| `rma-kaisan` | Mobile-first, header fixo, scanbar/searchbar, focus visible, safe areas, skeleton loading, toasts, modais e tabelas que viram cards em mobile. | Funcionários, consulta/edição rápida, carregamento do relatório, feedback pós-salvar, acessibilidade geral e uso em telas estreitas. | Em Avaliação, o uso principal continua desktop; mobile deve priorizar consulta, correção pontual e conferência. |

### Padrões reaproveitáveis por prioridade

1. **Tokens e estados do ByBox**: padronizar `ink`, `brand`, `success`, `warning`, `danger`, `page-bg`, `surface`, `status-pill-*` no `theme.py`.
2. **Cockpit do Estoque/ByBox**: transformar o relatório mensal em painel de decisão com métricas, etapas, exceções e foco do dia.
3. **Filtros e progresso do Picking**: usar dropdown/toolbar com contador ativo, barra de progresso do fechamento e painel de pendências sempre visível.
4. **Feedback do RMA**: criar toast de salvamento, skeleton para relatórios pesados, foco visível e tabelas responsivas com leitura em cards.
5. **Action grids Kaisan**: agrupar ações por intenção e risco, em vez de espalhar botões soltos pelas páginas.

## Principais problemas encontrados

1. A navegação atual mostra as etapas, mas não mostra estado do processo. O usuário não vê de cara se a competência está incompleta, pronta para fechamento ou bloqueada.
2. Os headers ocupam muito espaço vertical em telas operacionais. Eles são bonitos, mas competem com os controles que o usuário realmente usa todo dia.
3. As abas funcionam como etapas, porém não indicam conclusão, pendência ou próximo passo. Em avaliação semanal e monitoria, a validação só aparece tarde demais.
4. As tabelas são o coração da app, mas ainda parecem tabelas genéricas. Falta status por linha, priorização visual, colunas fixas por intenção e leitura rápida de risco.
5. A avaliação em massa tem muito potencial, mas a barra de ações rápidas fica solta. Falta uma área fixa de resumo/validação que acompanhe a edição.
6. O relatório mensal mistura checklist, filtros, métricas, tabelas, ranking e exportação em uma tela longa. O fechamento deveria se comportar como um cockpit de decisão.
7. Funcionários combina cadastro, listagem, edição e ativação em uma sequência vertical. Para manutenção diária, um layout lista + painel de detalhe reduz bastante rolagem e erro.
8. A sidebar não ajuda a responder "onde estou no mês?". Ela deveria exibir progresso por etapa, pendências e atalho para o fechamento.
9. A linguagem visual depende bastante de azul/navy. A paleta é boa, mas precisa de uso semântico mais forte para sucesso, atenção, risco, dinheiro e auditoria.
10. A troca de framework não resolveria sozinha esses pontos. Se a arquitetura visual continuar igual, React apenas entregaria a mesma experiência com mais custo.

## Direção proposta

Transformar a app em um painel operacional de fechamento mensal:

- Sidebar como trilha de processo, com status por etapa.
- Topo compacto com competência ativa, cobertura e pendências.
- Cada tela com uma ação primária inequívoca.
- Tabelas com chips de status, colunas fixas, densidade controlada e realce de exceções.
- Formulários guiados por blocos menores, com validação antecipada.
- Resumos financeiros sempre próximos da ação de salvar/exportar.
- Exportações em área própria, separadas da conferência.

## Mockups visuais

Arquivo: `design_audit/mockups/index.html`

O mockup contém quatro telas conceituais:

1. Fechamento mensal como cockpit: cobertura, pendências, total do mês, stage tiles, checklist e exportações.
2. Avaliação semanal em massa: barra de filtros estilo Picking, ações em lote, tabela priorizada e painel fixo de validação.
3. Funcionários: lista filtrável com painel de detalhe, busca persistente inspirada no RMA e status por linha.
4. Avaliação individual/monitoria: fluxo guiado por etapas, critérios em cards e prévia financeira lateral.

## Plano de implementação

### Fase 1 - Fundamentos visuais

Prioridade: alta  
Esforço: médio  
Arquivos prováveis: `theme.py`, `STYLE_GUIDE.md`

- Adotar a base de tokens do `picking-by-box-kaisan` como referência para cores, raios, sombras, status e contraste.
- Criar componentes reutilizáveis para `process_stepper`, `toolbar`, `summary_strip`, `status_chip`, `validation_panel`, `money_card`, `stage_grid`, `focus_strip` e `empty_state`.
- Reduzir altura do `render_page_header` em telas internas.
- Manter logo e identidade, mas mover metadados para uma faixa compacta.
- Adotar estados semânticos consistentes: pronto, atenção, bloqueado, novo, salvo, pendente.
- Definir densidade: cards de resumo compactos, formulários com blocos e tabelas com altura previsível.
- Criar padrões de feedback inspirados no `rma-kaisan`: toast, skeleton, foco visível e mensagens `aria-live` quando possível dentro do Streamlit.

Critério de aceite:
- Todas as telas principais usam o mesmo padrão de topo e status.
- Nenhum alerta crítico fica escondido dentro de expander por padrão.

### Fase 2 - Sidebar de processo

Prioridade: alta  
Esforço: baixo/médio  
Arquivos prováveis: `app.py`, `theme.py`, consultas auxiliares em `db.py` ou `ui_report.py`

- Trocar a sidebar puramente navegacional por uma trilha com status.
- Exibir competência atual, cobertura semanal, monitorias pendentes e estado do relatório.
- Manter os quatro passos atuais, mas com indicadores:
  - Funcionários: total ativo e cadastros incompletos.
  - Avaliação semanal: avaliações esperadas x encontradas.
  - Monitoria mensal: monitores elegíveis x avaliados.
  - Relatório mensal: pronto, pendente ou bloqueado.
- Adicionar ação secundária "Ir para fechamento" quando houver pendências críticas.

Critério de aceite:
- Ao abrir a app, o usuário entende o estado do mês sem entrar no relatório.

### Fase 3 - Relatório mensal como cockpit

Prioridade: alta  
Esforço: médio/alto  
Arquivos prováveis: `ui_report.py`, `theme.py`

- Mover checklist para o topo como painel sempre visível, inspirado nos cockpits administrativos de `estoque-kaisan` e `picking-by-box-kaisan`.
- Separar a tela em três zonas:
  - Decisão: cobertura, pendências, total, monitores, setores.
  - Conferência: tabelas filtráveis e ranking.
  - Saída: PDF executivo, PDF setor, CSV e anexos.
- Colocar pendências em lista priorizada com ação sugerida.
- Adicionar stage tiles para "Base conferida", "Semanais", "Monitoria", "Exportação" e "Assinatura".
- Adicionar focus strip com as 3 exceções que realmente precisam de decisão antes do fechamento.
- Transformar o expander "Semanas consideradas" em informação contextual menor, não o primeiro item da tela.
- Melhorar filtros com toolbar horizontal e chips ativos.

Critério de aceite:
- O usuário consegue responder em 10 segundos: "posso fechar o mês?".

### Fase 4 - Avaliação semanal em massa

Prioridade: alta  
Esforço: alto  
Arquivos prováveis: `ui_weekly.py`, `theme.py`

- Reorganizar o modo em massa em layout de trabalho:
  - Header compacto com semana e competência.
  - Toolbar de filtros com contador ativo, no padrão de `picking-kaisan`.
  - Barra de ações em lote com botões agrupados por intenção.
  - Tabela com status e prioridade fixos à esquerda.
  - Painel lateral ou faixa fixa com seleção, pendências, score médio e valor estimado.
- Exibir progresso da semana e estado de salvamento como mini painel, reaproveitando o padrão de progresso/sync do Picking.
- Agrupar botões de ação por risco:
  - Seleção: marcar/desmarcar.
  - Nota: aplicar 100%, aplicar 80%.
  - Base: última base, justificativas.
  - Banco: recarregar/salvar.
- Realçar linhas com pendência, score baixo, origem nova e monitor.
- Fazer a aba "Detalhes & KPIs" virar painel persistente resumido, deixando a aba apenas para auditoria profunda.

Critério de aceite:
- Antes de salvar, pendências dos selecionados aparecem sem trocar de aba.

### Fase 5 - Avaliação individual e monitoria

Prioridade: média/alta  
Esforço: médio  
Arquivos prováveis: `ui_weekly.py`, `ui_monitor.py`, `theme.py`

- Substituir abas simples por stepper com estados: Entrada, Erros, Justificativas, Revisão.
- Exibir "prévia financeira" como painel lateral contextual dentro da página, não somente na sidebar.
- Transformar critérios em cards compactos com resultado, faixa paga e valor.
- Validar justificativas por critério já na etapa de justificativas, com contador por item.
- Reaproveitar o mesmo padrão visual na monitoria mensal.

Critério de aceite:
- O usuário sabe exatamente o que falta preencher sem ir até a última aba.

### Fase 6 - Funcionários

Prioridade: média  
Esforço: médio  
Arquivos prováveis: `ui_employees.py`, `theme.py`

- Separar melhor "Cadastrar" de "Gerenciar".
- Na gestão, usar layout lista + detalhe:
  - Lista filtrável e densa à esquerda/centro.
  - Painel de detalhe/edição à direita ou abaixo em desktop estreito.
- Usar barra de busca persistente no padrão de consulta do `rma-kaisan`: campo evidente, feedback imediato, loading/empty state e resultado em card quando a viewport for estreita.
- Trocar labels longas no select de edição por uma tabela selecionável ou cards compactos.
- Condicionar campos "Monitor desde" e "Coord./Sup. desde" à ativação dos toggles.
- Unificar desativar/reativar no painel do funcionário selecionado.

Critério de aceite:
- Editar status de um funcionário não exige procurar o mesmo nome em múltiplos selects.

### Fase 7 - Acessibilidade e responsividade

Prioridade: média  
Esforço: médio  
Arquivos prováveis: `theme.py`, todas as telas

- Garantir foco visível em todos os controles.
- Revisar contraste dos captions e avisos suaves.
- Reduzir textos dentro de botões longos; usar ícones apenas quando houver biblioteca ou símbolo claro.
- Em mobile, priorizar consulta e pequenas correções; fechamento completo continua desktop-first.
- Evitar overflow em placeholders e labels longas.

Critério de aceite:
- Nenhum texto fica truncado em 1366px desktop ou viewport mobile comum.

## Decisão sobre framework

### Manter Streamlit agora

Motivo: a app é interna, tem forte lógica em Python, PDF em ReportLab, SQLite local e fluxos administrativos. Streamlit ainda oferece melhor custo/benefício para evoluir rapidamente.

O que fazer para Streamlit render bem:
- Centralizar componentes HTML/CSS seguros em `theme.py`.
- Criar helpers de layout para reduzir repetição.
- Usar `st.data_editor` com configuração mais intencional.
- Preparar consultas agregadas para status da sidebar e cockpit.
- Portar os melhores padrões dos apps Vite como CSS/componentes Streamlit antes de decidir uma migração total.

### Migrar depois, se necessário

Stack sugerida se houver migração:
- Next.js/React para frontend.
- FastAPI ou serviço Python para regras de cálculo e PDF.
- PostgreSQL/Supabase para persistência.
- Autenticação externa e auditoria por usuário.

Os apps `picking-kaisan`, `estoque-kaisan`, `picking-by-box-kaisan` e `rma-kaisan` provam que a família Vite/JS funciona bem para operação scanner-first, mobile e uso remoto. Para Avaliação, eles devem ser referência de design system e interação. Uma migração completa só fica atraente quando a app precisar de edição simultânea, permissões, auditoria por usuário, backend compartilhado ou experiência mobile plena.

Gatilhos reais para migrar:
- múltiplos usuários editando ao mesmo tempo;
- necessidade de permissões por setor;
- acesso remoto com dados críticos;
- histórico/auditoria avançada;
- dashboards interativos que extrapolam Streamlit;
- integrações com sistemas externos.

## Sequência recomendada

1. Implementar fundamentos visuais e sidebar de processo.
2. Redesenhar relatório mensal como cockpit.
3. Redesenhar avaliação em massa.
4. Redesenhar avaliação individual e monitoria com o mesmo stepper.
5. Redesenhar funcionários.
6. Só então reavaliar framework com base em uso real.

Essa ordem ataca primeiro as telas com maior risco operacional: fechamento e lote. O cadastro melhora depois, porque é importante, mas não é onde o erro mensal mais caro acontece.
