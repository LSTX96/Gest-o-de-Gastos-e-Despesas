# Passivo Cumani

Aplicação web (Reflex/Python puro) para controle do passivo semanal e mensal
das 7 lojas da rede **Drogarias Cumani**, com contas fixas, boletos de
distribuidoras, semáforo de vencimento, 3 níveis de acesso e relatórios.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

reflex init                    # se ainda não inicializado
reflex db init
reflex db migrate

python -m rps_passivo.seed     # popula lojas, contas fixas, distribuidoras,
                                # tipos de despesa e os 3 usuários padrão

reflex run
```

Acesse em `http://localhost:3000`.

## Usuários padrão (criados pelo seed)

| Usuário       | Senha        | Papel          |
|---------------|--------------|----------------|
| admin         | admin123     | Administrador  |
| operador      | operador123  | Operador       |
| visualizador  | visual123    | Visualizador   |

**Troque essas senhas antes de usar em produção.**

## O que já está implementado

- Login com 3 papéis (admin / operator / viewer) e logo Cumani centralizada
- Modelo de dados completo (SQLModel): usuários, lojas, contas fixas,
  distribuidoras, tipos de despesa, boletos, log de auditoria
- Componentes reutilizáveis `StoreAvatar` (logo ou iniciais) e
  `SemaforoBadge` (verde/amarelo/laranja/vermelho conforme dias até o
  vencimento)
- Dashboard com KPIs, alerta de contas próximas e gráficos (Plotly:
  barras por loja, pizza por tipo de despesa)
- Página de **Lançamentos** (operador): seleção de loja, alternância
  Conta Fixa / Boleto de Distribuidora, modais rápidos de cadastro
  (nova loja com upload de logo, nova conta fixa, nova distribuidora,
  novo tipo de despesa) e lista dos últimos lançamentos
- Página **Contas a Pagar**: card de alerta com as contas que vencem em
  até 5 dias, tabela ordenada por proximidade de vencimento com filtros
  de loja/status, e modal de detalhe com opção "Marcar como Pago"
- **Contas Fixas** (consulta por loja) e **Lojas** (grade com avatar/logo,
  criação e edição)
- **Relatório Semanal** (limite x boletos x fixas x total, com status
  Dentro do limite / Excedido) e **Relatório Mensal** (versão simplificada
  do mês atual)
- Seed com os dados reais extraídos da planilha `Passivo_RPS.xlsx`: as
  7 lojas com seus limites semanais/mensais e as contas fixas de RP1,
  RP2, RP3, ITAUNA e MUZEMA (CURICICA e TRINDADE usam um conjunto padrão
  replicável, pois não tinham aba própria de contas fixas na planilha —
  ajuste pelo admin)
- Controle de permissão "operador só edita o que criou" (`pode_editar_item`
  em `auth.py`), com flag `created_by_operator` salva em todos os cadastros
  feitos pelo operador

## Próximos passos sugeridos (não incluídos nesta primeira entrega)

Para manter esta entrega revisável, os itens abaixo ficaram como próxima
iteração — a arquitetura (models, auth, state) já foi pensada para
suportá-los sem retrabalho:

- Páginas dedicadas de administração de **Usuários**, **Distribuidoras**
  e **Tipos de Despesa** (hoje gerenciáveis via modais rápidos na tela
  de Lançamentos)
- **Folha de Rosto** para impressão (layout A4) e botão "Exportar PDF"
- **Exportação/Importação de Excel** no formato exato da planilha
  original (estrutura de `openpyxl` pronta em `requirements.txt`)
- Tela de **log de auditoria** para o admin (o registro já é gravado em
  `AuditLog` a cada criação/edição/pagamento)
- Upload de logo da loja gravando de fato o `base64` no banco (o campo
  `upload_logo_loja` no `LancamentosState` está com um placeholder —
  falta ligar ao `rx.upload_files` do Reflex)
- Agrupamento por tipo de despesa (accordion) na tela Contas a Pagar
- Cálculo de contas a vencer no card do Dashboard (`contas_a_vencer`
  hoje é ilustrativo — precisa aplicar `dias_restantes` da mesma forma
  que a tela Contas a Pagar já faz)

## Estrutura de arquivos

```
rps_passivo/
├── rxconfig.py
├── requirements.txt
├── assets/
│   └── logo_cumani.png
└── rps_passivo/
    ├── rps_passivo.py       # entry point / rotas
    ├── models.py            # SQLModel
    ├── auth.py               # hashing + permissões por papel
    ├── state.py              # estados Reflex (auth, dashboard, lançamentos...)
    ├── seed_data.py          # dados reais extraídos da planilha
    ├── seed.py                # script de popular o banco
    ├── utils/
    │   ├── semaforo.py
    │   ├── avatar.py
    │   └── helpers.py
    ├── components/
    │   ├── navbar.py          # navbar + sidebar + bottom nav + page_shell
    │   ├── store_avatar.py
    │   ├── semaforo_badge.py
    │   └── cards.py
    └── pages/
        ├── login.py
        ├── dashboard.py
        ├── lancamentos.py
        ├── contas_pagar.py
        ├── contas_fixas.py
        ├── lojas.py
        ├── relatorio_semanal.py
        └── relatorio_mensal.py
```
