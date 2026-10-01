# -*- coding: utf-8 -*-
"""Regras de negocio da corrida.

Orquestra as tres pecas algoritmicas sem conhecer HTTP:
  indice espacial (filtro)  ->  busca reversa (ETA real)  ->  A* (rota)
e submete toda mudanca de estado ao DAG.
"""

import time

from sqlalchemy import update

from algoritmos.busca import busca_caminho_minimo, reconstruir_caminho
from algoritmos.grafo import haversine, heuristica_haversine
from algoritmos.matching import motoristas_mais_proximos
from dominio import estados as E
from infra.modelos import Corrida, CorridaTransicao, Motorista, Pagamento

TARIFA_BASE = 5.00
POR_MINUTO = 0.80
POR_KM = 1.90


class SemMotoristaDisponivel(Exception):
    pass


class DestinoInalcancavel(Exception):
    pass


# --------------------------------------------------------------- transicoes

def transitar(sessao, corrida, novo_estado):
    """Ponto UNICO de mudanca de estado. Valida pelo DAG e audita.

    Nenhuma rota da API altera `corrida.estado` diretamente -- se alterasse,
    a garantia estrutural do DAG viraria apenas convencao.
    """
    anterior = corrida.estado
    E.exigir_transicao(anterior, novo_estado)     # levanta TransicaoInvalida
    corrida.estado = novo_estado
    sessao.add(CorridaTransicao(corrida_id=corrida.id, de_estado=anterior,
                                para_estado=novo_estado))
    return corrida


# ------------------------------------------------------------------- rota

def calcular_rota(grafo, no_origem, no_destino, alt=None):
    """A* ate o destino. Devolve (segundos, caminho).

    Com `alt`, usa a heuristica de marcos (ALT), muito mais apertada; sem ela,
    cai na haversine. As duas sao admissiveis, logo a rota devolvida e a mesma
    -- muda so quanto do grafo precisa ser explorado para encontra-la.

    O divisor da haversine e a velocidade maxima MEDIDA no proprio grafo, e
    nao um teto fixo: a malha real de Sao Paulo tem trecho a 110 km/h, e um
    teto de 100 faria h superestimar ali.
    """
    if no_origem == no_destino:
        return 0.0, [no_origem]
    heuristica = (alt.heuristica(no_destino, origem=no_origem) if alt
                  else heuristica_haversine(grafo, no_destino))
    resultado = busca_caminho_minimo(grafo, no_origem, {no_destino}, h=heuristica)
    if no_destino not in resultado.custos:
        raise DestinoInalcancavel(f"sem rota de {no_origem} ate {no_destino}")
    return (resultado.custos[no_destino],
            reconstruir_caminho(resultado.anterior, no_origem, no_destino))


def comprimento_metros(grafo, caminho):
    return sum(
        haversine(*grafo.coordenadas(a), *grafo.coordenadas(b))
        for a, b in zip(caminho, caminho[1:])
    )


def estimar_custo(segundos, metros):
    return round(TARIFA_BASE + POR_MINUTO * (segundos / 60) + POR_KM * (metros / 1000), 2)


def estimar_viagem(grafo, indice_nos, origem, destino, *, registro=None,
                   config=None, semaforos=frozenset(), comparar=False):
    """Previa da viagem, ANTES de pedir: rota, tempo, distancia e preco.

    `origem`/`destino` sao (lat, lon) do endereco escolhido. Cada um e
    ancorado ao cruzamento mais proximo pela quadtree, e o A* roda entre os
    dois -- exatamente o calculo que o pedido de corrida fara depois.

    Com `registro`, mede tambem o ETA REAL do motorista mais proximo (busca
    reversa, a mesma do pareamento). Com `comparar`, roda o Dijkstra sobre o
    mesmo par e devolve os dois contadores de nos expandidos: o custo tem de
    ser identico (o Dijkstra e o oraculo), so o esforco muda.
    """
    no_origem = indice_nos.mais_proximo(*origem)
    no_destino = indice_nos.mais_proximo(*destino)
    if no_origem is None or no_destino is None:
        raise DestinoInalcancavel("coordenadas fora da area coberta pela malha")

    inicio = time.perf_counter()
    if no_origem == no_destino:
        segundos, caminho, expandidos = 0.0, [no_origem], 0
    else:
        resultado = busca_caminho_minimo(grafo, no_origem, {no_destino},
                                         h=heuristica_haversine(grafo, no_destino))
        if no_destino not in resultado.custos:
            raise DestinoInalcancavel(f"sem rota de {no_origem} ate {no_destino}")
        segundos = resultado.custos[no_destino]
        caminho = reconstruir_caminho(resultado.anterior, no_origem, no_destino)
        expandidos = resultado.nos_expandidos
    ms_a_estrela = (time.perf_counter() - inicio) * 1000

    metros = comprimento_metros(grafo, caminho)
    pontos = [grafo.coordenadas(no) for no in caminho]
    saida = {
        "segundos": segundos,
        "metros": metros,
        "custo_estimado": estimar_custo(segundos, metros),
        "pontos": pontos,
        "semaforos_no_caminho": sum(1 for no in caminho if no in semaforos),
        # Quanto o endereco esta do cruzamento onde a rota comeca/termina:
        # o front desenha esse trecho a pe, tracejado.
        "ancoragem_m": {
            "origem": haversine(*origem, *pontos[0]),
            "destino": haversine(*destino, *pontos[-1]),
        },
        "algoritmo": {
            "a_estrela": {"nos_expandidos": expandidos, "ms": round(ms_a_estrela, 1)},
            "velocidade_max_kmh": round(grafo.velocidade_maxima_kmh(), 1),
            "nos_na_malha": len(grafo.nos),
        },
        "motoristas": None,
    }

    if comparar and no_origem != no_destino:
        inicio = time.perf_counter()
        oraculo = busca_caminho_minimo(grafo, no_origem, {no_destino})
        saida["algoritmo"]["dijkstra"] = {
            "nos_expandidos": oraculo.nos_expandidos,
            "ms": round((time.perf_counter() - inicio) * 1000, 1),
            "mesmo_custo": abs(oraculo.custos[no_destino] - segundos) < 1e-6,
        }

    if registro is not None and config is not None:
        lat, lon = pontos[0]
        candidatos = registro.candidatos(lat, lon, config.raio_busca_m,
                                         config.max_candidatos)
        ranking = motoristas_mais_proximos(
            grafo, no_origem, candidatos, limite_segundos=config.limite_matching_s,
        ) if candidatos else []
        saida["motoristas"] = {
            "proximos": len(candidatos),
            "eta_mais_proximo_s": ranking[0].eta_segundos if ranking else None,
        }
    return saida


# --------------------------------------------------------------- alocacao

def alocar_motorista(sessao, grafo, registro, corrida, config):
    """Escolhe o motorista de menor ETA REAL e o reserva.

    1. Indice espacial corta de milhares para ~20 candidatos plausiveis.
    2. UMA busca reversa da o tempo real de todos eles de uma vez.
    3. A reserva e otimista: `UPDATE ... WHERE disponivel = 1`. Se afetou
       zero linhas, outro pedido ganhou a corrida pelo mesmo motorista --
       segue para o proximo do ranking, sem travar a tabela.
    """
    lat, lon = grafo.coordenadas(corrida.no_origem)
    candidatos = registro.candidatos(lat, lon, config.raio_busca_m,
                                     config.max_candidatos)
    if not candidatos:
        raise SemMotoristaDisponivel("nenhum motorista disponivel no raio")

    ranking = motoristas_mais_proximos(
        grafo, corrida.no_origem, candidatos,
        limite_segundos=config.limite_matching_s,
    )
    if not ranking:
        raise SemMotoristaDisponivel(
            "ha motoristas por perto, mas nenhum alcanca o passageiro a tempo"
        )

    for candidato in ranking:
        afetadas = sessao.execute(
            update(Motorista)
            .where(Motorista.id == candidato.motorista_id,
                   Motorista.disponivel.is_(True))
            .values(disponivel=False)
        ).rowcount
        if afetadas == 1:
            registro.definir_disponibilidade(candidato.motorista_id, False)
            corrida.motorista_id = candidato.motorista_id
            corrida.eta_segundos = candidato.eta_segundos
            transitar(sessao, corrida, E.ALOCACAO)
            return candidato

    raise SemMotoristaDisponivel(
        "todos os candidatos foram alocados a outros pedidos neste instante"
    )


def liberar_motorista(sessao, registro, motorista_id):
    if motorista_id is None:
        return
    sessao.execute(
        update(Motorista).where(Motorista.id == motorista_id).values(disponivel=True)
    )
    registro.definir_disponibilidade(motorista_id, True)


# ----------------------------------------------------------------- fluxo

def definir_rota(sessao, grafo, corrida, alt=None):
    """Calcula a rota da corrida e avanca o estado para `rota`."""
    segundos, caminho = calcular_rota(grafo, corrida.no_origem, corrida.no_destino,
                                      alt=alt)
    corrida.custo_estimado = estimar_custo(segundos, comprimento_metros(grafo, caminho))
    transitar(sessao, corrida, E.ROTA)
    return segundos, caminho


def registrar_pagamento(sessao, corrida):
    """So roda depois que `transitar` aceitou concluida -> paga."""
    transitar(sessao, corrida, E.PAGA)
    pagamento = Pagamento(corrida_id=corrida.id,
                          valor=corrida.custo_estimado or 0.0)
    sessao.add(pagamento)
    return pagamento
