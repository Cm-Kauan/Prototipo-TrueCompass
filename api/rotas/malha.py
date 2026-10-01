# -*- coding: utf-8 -*-
"""Geometria da malha viaria, para o front-end desenhar.

Sem este endpoint o mapa dependeria de tiles externos (tile.openstreetmap.org)
e nao mostraria nada do grafo que realmente usamos. Servindo os trechos daqui,
o front desenha a MALHA DE VERDADE -- da para ver mao unica, o rio e as pontes,
e a rota calculada sobre as ruas que o algoritmo enxerga.

Nao exige autenticacao: e geometria derivada de dado publico do OpenStreetMap,
sem qualquer informacao de usuario.
"""

from fastapi import APIRouter, Depends, Query

from api.deps import obter_grafo, obter_matriz

rotas = APIRouter(prefix="/malha", tags=["malha"])

LIMITE_MAXIMO = 20_000


@rotas.get("/info")
def info(grafo=Depends(obter_grafo)):
    """Caixa envolvente e tamanho da malha: o front centraliza o mapa com isso."""
    latitudes, longitudes = [], []
    for no in grafo.nos:
        lat, lon = grafo.coordenadas(no)
        latitudes.append(lat)
        longitudes.append(lon)
    if not latitudes:
        return {"nos": 0, "arestas": 0, "caixa": None}
    return {
        "nos": len(latitudes),
        "arestas": grafo.total_arestas(),
        "caixa": {"sul": min(latitudes), "norte": max(latitudes),
                  "oeste": min(longitudes), "leste": max(longitudes)},
        "centro": {"lat": (min(latitudes) + max(latitudes)) / 2,
                   "lon": (min(longitudes) + max(longitudes)) / 2},
    }


@rotas.get("/semaforos")
def semaforos(matriz=Depends(obter_matriz)):
    """Cruzamentos semaforizados, para o front desenhar.

    Vem da matriz, e nao do grafo: o atraso ja foi absorvido pelos pesos das
    arestas e nao e mais recuperavel a partir deles. Quem sabe onde cada sinal
    esta e a matriz.

    Lista vazia quando a malha veio do OpenStreetMap, que nao traz temporizacao
    semaforica utilizavel.
    """
    if matriz is None:
        return {"semaforos": [], "total": 0, "fonte": "openstreetmap"}

    saida = []
    for i in range(matriz.altura):
        for j in range(matriz.largura):
            sinal = matriz.semaforo_de(i, j)
            if sinal is None:
                continue
            lat, lon = matriz.coordenadas(i, j)
            saida.append({
                "lat": round(lat, 6), "lon": round(lon, 6),
                "vermelho": sinal.vermelho, "ciclo": sinal.ciclo,
                "atraso_medio": round(sinal.atraso, 2),
            })
    return {"semaforos": saida, "total": len(saida), "fonte": "matriz"}


@rotas.get("/trechos")
def trechos(sul: float = Query(-90), oeste: float = Query(-180),
            norte: float = Query(90), leste: float = Query(180),
            limite: int = Query(6000, ge=1, le=LIMITE_MAXIMO),
            grafo=Depends(obter_grafo)):
    """Trechos de rua dentro da caixa, em formato compacto.

    Cada trecho e [lat1, lon1, lat2, lon2, mao_unica], com mao_unica em 0 ou 1.
    Lista, e nao objeto, para reduzir o tamanho da resposta -- numa malha real
    sao milhares de segmentos, e nome de campo repetido dominaria o payload.

    Trechos de mao dupla sao emitidos UMA vez (apenas quando origem < destino),
    evitando desenhar a mesma rua duas vezes sobrepostas.
    """
    dentro = {}
    for no in grafo.nos:
        lat, lon = grafo.coordenadas(no)
        if sul <= lat <= norte and oeste <= lon <= leste:
            dentro[no] = (lat, lon)

    saida = []
    truncado = False
    for origem, (lat1, lon1) in dentro.items():
        for destino, _peso in grafo.vizinhos(origem):
            if destino not in dentro:
                continue
            volta_existe = origem in dict(grafo.vizinhos(destino))
            # Mao dupla: emite so um sentido, para nao sobrepor a linha.
            if volta_existe and not (origem < destino):
                continue
            if len(saida) >= limite:
                truncado = True
                break
            lat2, lon2 = dentro[destino]
            saida.append([round(lat1, 6), round(lon1, 6),
                          round(lat2, 6), round(lon2, 6),
                          0 if volta_existe else 1])
        if truncado:
            break

    return {"trechos": saida, "total": len(saida), "truncado": truncado}
