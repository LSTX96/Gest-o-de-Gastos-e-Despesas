"""Motor de análise: transforma os números em história, observações e sugestões."""
from .helpers import fmt_moeda

ORDEM_NIVEL = {"alerta": 0, "atencao": 1, "info": 2, "positivo": 3}


def _pct(parte: float, todo: float) -> float:
    return (parte / todo * 100) if todo else 0.0


# ---------------------------------------------------------------------------
# Storytelling: parágrafos que contam o que está acontecendo
# ---------------------------------------------------------------------------
def historia(c: dict) -> list[str]:
    """Recebe o contexto calculado e devolve parágrafos em linguagem natural."""
    paragrafos = []
    total = c["total_mes"]
    anterior = c["total_mes_ant"]

    # 1) O mês em relação ao anterior
    if anterior > 0:
        variacao = (total / anterior - 1) * 100
        direcao = "acima" if variacao >= 0 else "abaixo"
        comparacao = f"{abs(variacao):.0f}% {direcao} de {c['mes_ant_nome']} ({fmt_moeda(anterior)})"
    else:
        comparacao = f"sem lançamentos em {c['mes_ant_nome']} para comparar"
    paragrafos.append(
        f"Em {c['mes_nome']}, {c['escopo']} soma {fmt_moeda(total)} em compromissos, {comparacao}."
    )

    # 2) Composição do mês
    if total > 0:
        pf = _pct(c["fixas_mes"], total)
        pv = _pct(c["var_mes"], total)
        texto = (
            f"As contas fixas respondem por {pf:.0f}% ({fmt_moeda(c['fixas_mes'])}) "
            f"e os gastos variáveis por {pv:.0f}% ({fmt_moeda(c['var_mes'])})."
        )
        if c["por_tipo_mes"]:
            tipo, valor = max(c["por_tipo_mes"].items(), key=lambda x: x[1])
            texto += f" O maior peso do mês vem de {tipo}, com {fmt_moeda(valor)} ({_pct(valor, total):.0f}% do total)."
        paragrafos.append(texto)

    # 2b) Olhando para trás
    passado = [p for p in c.get("passado", []) if p[1] > 0]
    if passado:
        media_p = sum(v for _, v in passado) / len(passado)
        caro = max(passado, key=lambda x: x[1])
        variacao_p = _pct(total, media_p) - 100
        direcao_p = "acima" if variacao_p >= 0 else "abaixo"
        paragrafos.append(
            f"No retrovisor, {caro[0]} foi o mês mais caro dos últimos 12 meses ({fmt_moeda(caro[1])}). "
            f"A média dos meses com lançamentos é {fmt_moeda(media_p)}, e o mês atual está "
            f"{abs(variacao_p):.0f}% {direcao_p} dela."
        )

    # 3) Olhando para frente: só o que ainda está a pagar
    aberto = c.get("futuro_aberto", [])
    soma_aberto = sum(v for _, v in aberto)
    if soma_aberto > 0:
        com_aberto = [p for p in aberto if p[1] > 0]
        pico = max(com_aberto, key=lambda x: x[1])
        paragrafos.append(
            f"Olhando para frente, os próximos 12 meses têm {fmt_moeda(soma_aberto)} a pagar, "
            f"distribuídos em {len(com_aberto)} mês(es). {pico[0]} é o mês com mais contas em aberto "
            f"({fmt_moeda(pico[1])})."
        )
    else:
        paragrafos.append(
            "Olhando para frente, não há contas a pagar lançadas para os próximos 12 meses."
        )

    # 4) Limites
    com_limite = [l for l in c["lojas"] if l["limite"] > 0]
    acima = [l for l in com_limite if l["gasto"] > l["limite"]]
    if acima:
        nomes = ", ".join(l["nome"] for l in acima)
        excesso = sum(l["gasto"] - l["limite"] for l in acima)
        paragrafos.append(
            f"{len(acima)} loja(s) passaram do limite mensal ({nomes}), "
            f"somando {fmt_moeda(excesso)} acima do teto."
        )
    elif com_limite:
        paragrafos.append("Todas as lojas com limite cadastrado estão dentro do teto neste mês.")

    return paragrafos


# ---------------------------------------------------------------------------
# Observações e sugestões
# ---------------------------------------------------------------------------
def observacoes(c: dict) -> list[dict[str, str]]:
    """Lista de observações ordenadas por importância (alerta, atenção, info, positivo)."""
    obs: list[dict[str, str]] = []

    def add(nivel: str, icone: str, titulo: str, texto: str) -> None:
        obs.append({"nivel": nivel, "icone": icone, "titulo": titulo, "texto": texto})

    # Contas vencidas
    if c["vencidas_qtd"]:
        add(
            "alerta", "triangle-alert",
            f"{c['vencidas_qtd']} conta(s) vencida(s)",
            f"Somam {fmt_moeda(c['vencidas_valor'])}. Regularize para evitar juros e multas; "
            "elas aparecem em vermelho na página Contas.",
        )

    # Limites das lojas
    com_limite = [l for l in c["lojas"] if l["limite"] > 0]
    for l in com_limite:
        p = _pct(l["gasto"], l["limite"])
        if p > 100:
            add(
                "alerta", "circle-alert",
                f"{l['nome']} passou do limite",
                f"Soma {fmt_moeda(l['gasto'])} no mês, {p - 100:.0f}% acima do teto de "
                f"{fmt_moeda(l['limite'])}. Avalie adiar compras não essenciais para o próximo mês.",
            )
        elif p >= 80:
            add(
                "atencao", "gauge",
                f"{l['nome']} perto do limite",
                f"Já usou {p:.0f}% do limite e faltam {c['dias_restantes']} dias para o mês fechar. "
                f"Restam {fmt_moeda(l['limite'] - l['gasto'])} para novos gastos.",
            )

    # Concentração de contas a pagar nos próximos meses (a partir do mês que vem)
    aberto = [p for p in c.get("futuro_aberto", []) if p[1] > 0]
    if len(aberto) >= 3:
        media = sum(v for _, v in aberto) / len(aberto)
        pico = max(aberto, key=lambda x: x[1])
        if pico[1] > media * 1.3:
            livres = sorted(c.get("futuro_aberto", []), key=lambda x: x[1])[:2]
            add(
                "atencao", "calendar-range",
                f"{pico[0]} concentra contas a pagar",
                f"O mês tem {fmt_moeda(pico[1])} em aberto, {_pct(pico[1], media) - 100:.0f}% acima "
                f"da média dos meses com contas ({fmt_moeda(media)}). Para novas compras a prazo, "
                f"prefira vencimentos em {livres[0][0]} ou {livres[1][0]}.",
            )

    # Semana com mais contas a pagar nas próximas 8 semanas
    semanas = [s for s in c["semanas"] if s[1] > 0]
    if semanas:
        media_s = sum(v for _, v in c["semanas"]) / len(c["semanas"])
        pico_s = max(semanas, key=lambda x: x[1])
        if len(semanas) == 1 or pico_s[1] > media_s * 1.5:
            add(
                "info", "calendar-days",
                "Semana mais pesada à frente",
                f"A semana de {pico_s[0]} tem {fmt_moeda(pico_s[1])} em contas a pagar. "
                "Vale conferir o caixa com antecedência.",
            )

    # Tipos de gasto fora do padrão
    for tipo, valor in sorted(c["por_tipo_mes"].items(), key=lambda x: -x[1])[:6]:
        media = c["media_tipo_3m"].get(tipo, 0.0)
        if media <= 0:
            continue
        if valor > media * 1.3 and valor - media > 200:
            add(
                "atencao", "trending-up",
                f"{tipo} acima do normal",
                f"{fmt_moeda(valor)} no mês, {_pct(valor, media) - 100:.0f}% acima da média "
                f"dos últimos 3 meses ({fmt_moeda(media)}).",
            )
        elif valor < media * 0.7:
            add(
                "positivo", "trending-down",
                f"{tipo} em queda",
                f"{fmt_moeda(valor)} no mês, {100 - _pct(valor, media):.0f}% abaixo da média "
                f"dos últimos 3 meses ({fmt_moeda(media)}).",
            )

    # Mês em relação ao anterior
    if c["total_mes_ant"] > 0:
        variacao = _pct(c["total_mes"], c["total_mes_ant"]) - 100
        if variacao <= -10:
            add(
                "positivo", "piggy-bank",
                "Mês mais leve que o anterior",
                f"{c['mes_nome'].capitalize()} está {abs(variacao):.0f}% abaixo de {c['mes_ant_nome']}.",
            )
        elif variacao >= 15:
            add(
                "atencao", "arrow-up-right",
                "Mês mais pesado que o anterior",
                f"{c['mes_nome'].capitalize()} está {variacao:.0f}% acima de {c['mes_ant_nome']}. "
                "Confira se há gastos pontuais que podem ser renegociados ou adiados.",
            )

    # Mês atual em relação à média histórica
    passado = [p for p in c.get("passado", []) if p[1] > 0]
    if len(passado) >= 2:
        media_hist = sum(v for _, v in passado) / len(passado)
        if media_hist > 0 and c["total_mes"] > media_hist * 1.3:
            add(
                "atencao", "history",
                "Mês acima da média histórica",
                f"{c['mes_nome'].capitalize()} soma {fmt_moeda(c['total_mes'])}, "
                f"{_pct(c['total_mes'], media_hist) - 100:.0f}% acima da média dos meses anteriores "
                f"({fmt_moeda(media_hist)}).",
            )

    # Qualidade dos dados
    if c["sem_tipo_qtd"] >= 3:
        add(
            "info", "tags",
            "Despesas sem tipo",
            f"{c['sem_tipo_qtd']} despesas dos últimos 12 meses somam {fmt_moeda(c['sem_tipo_valor'])} "
            "sem tipo de despesa. Classificá-las deixa os gráficos e as análises mais precisos.",
        )

    # Situação confortável
    if com_limite and all(l["gasto"] <= l["limite"] * 0.8 for l in com_limite):
        add(
            "positivo", "shield-check",
            "Lojas com folga no limite",
            "Todas as lojas com limite cadastrado estão abaixo de 80% do teto neste mês.",
        )

    if not obs:
        add(
            "info", "sparkles",
            "Sem pontos de atenção",
            "Os números do período estão dentro do padrão. Quanto mais despesas forem lançadas, "
            "mais precisa fica a análise.",
        )

    obs.sort(key=lambda o: ORDEM_NIVEL[o["nivel"]])
    return obs[:8]


# ---------------------------------------------------------------------------
# Análise das linhas do tempo (semanal e mensal)
# ---------------------------------------------------------------------------
def resumo_serie(rotulos, valores, inicio_futuro: int, unidade: str, abertura: str, abertos=None):
    """Resume uma linha do tempo.

    rotulos: nome de cada ponto (ex.: '16/11 a 22/11' ou 'MAR/27')
    valores: total de compromissos de cada ponto (pagos e a pagar)
    inicio_futuro: índice do primeiro ponto que ainda não passou
    unidade: 'semana' ou 'mês'
    abertura: começo da frase (ex.: 'Em 2026' ou 'Até dezembro')
    abertos: valor ainda a pagar de cada ponto (usado em tudo que é 'à frente')
    """
    semana = unidade == "semana"
    if abertos is None:
        abertos = valores
    pontos = list(zip(rotulos, valores))
    com_valor = [(r, v) for r, v in pontos if v > 0]
    if not com_valor:
        return f"{abertura}, ainda não há compromissos lançados.", []

    media = sum(v for _, v in com_valor) / len(com_valor)
    pico = max(com_valor, key=lambda x: x[1])
    acima = sum(1 for _, v in com_valor if v > media)
    plural = "semanas" if semana else "meses"

    destaques = [
        {
            "tipo": "pico",
            "rotulo": "Semana mais carregada" if semana else "Mês mais carregado",
            "valor": fmt_moeda(pico[1]),
            "detalhe": pico[0],
        },
        {
            "tipo": "media",
            "rotulo": f"Média por {unidade}",
            "valor": fmt_moeda(media),
            "detalhe": f"{acima} {plural} acima da média",
        },
    ]

    if semana:
        texto = f"{abertura}, a semana mais carregada é a de {pico[0]}, com {fmt_moeda(pico[1])}"
    else:
        texto = f"{abertura}, o mês mais carregado é {pico[0]}, com {fmt_moeda(pico[1])}"
    if len(com_valor) > 1 and media > 0:
        texto += f", {_pct(pico[1], media) - 100:.0f}% acima da média de {fmt_moeda(media)} por {unidade}."
    else:
        texto += "."

    futuro_total = pontos[inicio_futuro:]
    futuro_aberto = list(zip(rotulos, abertos))[inicio_futuro:]
    if not futuro_total:
        return texto + " Período encerrado.", destaques

    # O que ainda está a pagar daqui para frente
    a_pagar = sum(v for _, v in futuro_aberto)
    com_aberto = [(r, v) for r, v in futuro_aberto if v > 0]
    if a_pagar > 0:
        destaques.append({
            "tipo": "alerta",
            "rotulo": "A pagar à frente",
            "valor": fmt_moeda(a_pagar),
            "detalhe": f"{len(com_aberto)} {plural} com contas em aberto",
        })
        media_aberto = a_pagar / len(com_aberto)
        proxima = com_aberto[0] if len(com_aberto) == 1 else next(
            ((r, v) for r, v in com_aberto if v > media_aberto * 1.3), None
        )
        if proxima:
            destaques.append({
                "tipo": "alerta",
                "rotulo": "Próxima semana com mais a pagar" if semana else "Próximo mês com mais a pagar",
                "valor": fmt_moeda(proxima[1]),
                "detalhe": proxima[0],
            })
            if semana:
                texto += f" A próxima semana com mais contas a pagar é a de {proxima[0]} ({fmt_moeda(proxima[1])}): vale preparar o caixa."
            else:
                texto += f" O próximo mês com mais contas a pagar é {proxima[0]} ({fmt_moeda(proxima[1])}): vale preparar o caixa."
    else:
        texto += " Não há contas a pagar à frente neste período."

    # Pontos mais livres (pelo total de compromissos), para planejar compras novas
    livres = sorted(futuro_total, key=lambda x: x[1])[:2]
    destaques.append({
        "tipo": "leve",
        "rotulo": "Semana mais livre à frente" if semana else "Mês mais livre à frente",
        "valor": fmt_moeda(livres[0][1]),
        "detalhe": livres[0][0],
    })
    nomes = " e ".join(r for r, _ in livres)
    if semana:
        texto += f" Para novas compras a prazo, as semanas mais livres à frente são as de {nomes}."
    else:
        texto += f" Para novas compras a prazo, os meses mais livres à frente são {nomes}."

    return texto, destaques