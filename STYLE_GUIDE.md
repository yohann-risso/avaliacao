# Guia de estilo, paleta e UX

## Direção visual

O estilo escolhido é **painel administrativo operacional**: limpo, sóbrio, denso na medida certa e orientado a conferência. O foco não é parecer uma landing page, e sim reduzir erro humano em cadastros, avaliações e fechamento mensal.

Princípios:

- Priorizar leitura, revisão e comparação.
- Usar cards apenas para métricas, avisos e blocos repetidos.
- Manter o fluxo em etapas fixas, sem navegação escondida.
- Dar destaque visual para pendências, status e valores de pagamento.
- Evitar decoração pesada; a interface deve passar confiança e velocidade.

## Paleta

| Papel | Cor | Hex | Uso |
| --- | --- | --- | --- |
| Texto principal | Azul petróleo escuro | `#12263A` | Títulos, valores e labels fortes |
| Navegação | Navy profundo | `#0B182A` | Sidebar e áreas de orientação |
| Primária | Azul operacional | `#347DA5` | Abas ativas, foco, ações principais e links |
| Sucesso | Verde controle | `#177864` | Operações concluídas, valores OK |
| Atenção | Âmbar | `#CB8A19` | Pendências, alertas leves e revisão |
| Erro | Vermelho fechado | `#B04557` | Falhas, exclusão e bloqueios |
| Fundo | Cinza azulado | `#EDF3F7` | Fundo geral da aplicação |
| Superfície | Branco frio | `#F9FCFF` | Inputs, cards e containers |
| Linha | Navy translúcido | `rgba(23, 52, 82, 0.12)` | Bordas e divisórias |

Essa paleta foi escolhida para combinar com o contexto de estoque/expedição: transmite controle e processo, mas usa verde, âmbar e vermelho como linguagem funcional para estados. O azul não deve ser usado sozinho para tudo; cada cor tem papel semântico.

## Tipografia

- Interface: `IBM Plex Sans`, `Segoe UI`, `sans-serif`.
- Títulos e números fortes: `Space Grotesk`, `Segoe UI`, `sans-serif`.
- Fallbacks do sistema são aceitos para manter o app leve e sem dependência externa de fonte.

Regras:

- Não usar letras muito condensadas ou decorativas.
- Não reduzir demais labels de formulário; o app depende de precisão.
- Valores monetários e totais devem ter peso visual maior que textos de apoio.

## Componentes

- **Sidebar**: sempre representa o fluxo de trabalho, não apenas páginas soltas.
- **Hero de página**: identifica etapa, função da tela e contexto rápido.
- **Status cards**: métricas de fechamento, pendências e valores relevantes.
- **Avisos**: sempre com cor semântica e texto objetivo.
- **Tabelas**: devem favorecer escaneamento e conferência, não estética decorativa.
- **Formulários**: campos obrigatórios marcados com `*`, com mensagens claras antes de salvar.

## UX dos fluxos

- O usuário deve conseguir seguir o mês inteiro pela ordem da sidebar.
- Cada tela deve deixar claro o que falta antes de fechar ou exportar.
- Campos críticos devem ter defaults seguros e justificativa quando houver desconto.
- O relatório mensal deve funcionar como checklist antes do PDF final.
- Mobile deve continuar usável para consulta e pequenos ajustes, mas o fechamento completo é pensado para desktop.

## Stack de UI

Manter **Streamlit + CSS customizado** é a decisão correta agora. Um frontend React separado só compensa se houver:

- múltiplos perfis de usuário com autenticação;
- concorrência real de edição;
- necessidade de uso externo/remoto;
- dashboards interativos mais complexos;
- integrações contínuas com ERP, WMS ou folha.

Enquanto o app for interno e focado no fechamento operacional, a stack atual entrega melhor relação entre qualidade de UX, velocidade de mudança e manutenção.
