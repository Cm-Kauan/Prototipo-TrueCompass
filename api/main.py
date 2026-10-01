# -*- coding: utf-8 -*-
"""Aplicacao FastAPI do TrueCompass."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from algoritmos.indice_espacial import indice_dos_nos
from api.conexoes import GerenciadorConexoes
from api.rotas import auth, corridas, malha, motoristas, ws
from dominio.estados import validar_dag
from dominio.registro import RegistroMotoristas
from infra.banco import criar_tabelas
from infra.config import obter_config

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
registrador = logging.getLogger("truecompass")


def carregar_malha(config):
    """Decide a fonte do mapa, nesta ordem de preferencia.

    1. MATRIZ (`mapas/*.mapa`) -- editavel a mao, versionavel em diff, carrega
       semaforos. E a fonte de autoria do projeto.
    2. Artefato do OpenStreetMap (`dados/malha.json`), gerado offline pelo CLI.
    3. Cidade sintetica, apenas para nao travar o desenvolvimento.

    O servidor NUNCA consulta a Overpass no boot: seria lento, fragil e abuso
    de um servico publico.

    Devolve (grafo, matriz_ou_None). A matriz e guardada porque o grafo nao
    carrega os semaforos -- eles ja foram absorvidos pelos pesos das arestas,
    e a matriz e quem sabe onde cada um esta, para o front desenhar.
    """
    if os.path.exists(config.arquivo_matriz):
        from algoritmos.matriz_mapa import MatrizMapa
        with open(config.arquivo_matriz, encoding="utf-8") as arquivo:
            matriz = MatrizMapa.de_texto(arquivo.read())
        grafo = matriz.para_grafo(considerar_semaforos=config.considerar_semaforos)
        dados = matriz.estatisticas()
        registrador.info(
            "mapa em matriz: %s (%dx%d, %d nos, %d arestas, %d semaforos%s)",
            config.arquivo_matriz, dados["altura"], dados["largura"],
            len(grafo.nos), grafo.total_arestas(), dados["semaforos"],
            "" if config.considerar_semaforos else " IGNORADOS",
        )
        return grafo, matriz

    if os.path.exists(config.arquivo_malha):
        from infra.osm import carregar_grafo
        grafo = carregar_grafo(config.arquivo_malha)
        registrador.info("malha do OpenStreetMap: %s (%d nos, %d arestas)",
                         config.arquivo_malha, len(grafo.nos), grafo.total_arestas())
        return grafo, None

    from algoritmos.cidade_exemplo import construir_cidade
    registrador.warning(
        "nem %s nem %s encontrados: subindo com a CIDADE SINTETICA.",
        config.arquivo_matriz, config.arquivo_malha,
    )
    return construir_cidade(lado=40), None


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    config = obter_config()

    # 1. O DAG do fluxo e validado por Kahn ANTES de qualquer requisicao.
    #    Havendo ciclo, o servidor nao sobe -- a prova da secao 5.2 da
    #    documentacao vira garantia de execucao.
    ordem = validar_dag()
    registrador.info("fluxo da corrida validado: %s", " -> ".join(ordem))

    # 2. A malha e o grafo reverso sao construidos UMA vez e ficam em memoria
    #    pelo tempo de vida do processo. Reconstruir por requisicao seria
    #    inviavel -- e e por isso que este backend precisa de processo
    #    persistente (Railway), e nao de funcoes serverless.
    app.state.grafo, app.state.matriz = carregar_malha(config)
    app.state.grafo.reverso()
    app.state.indice_nos = indice_dos_nos(app.state.grafo)
    registrador.info("grafo reverso e indice espacial prontos")

    app.state.registro = RegistroMotoristas()
    app.state.conexoes = GerenciadorConexoes()
    app.state.conexoes.registrar_loop(asyncio.get_running_loop())

    criar_tabelas()
    registrador.info("TrueCompass pronto (ambiente: %s)", config.ambiente)
    yield
    registrador.info("encerrando")


def criar_app():
    config = obter_config()
    app = FastAPI(
        title="TrueCompass API",
        description="Mobilidade urbana com roteamento por A* e pareamento "
                    "reverso many-to-one sobre malha do OpenStreetMap.",
        version="0.1.0",
        lifespan=ciclo_de_vida,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origens_cors,      # o dominio do front no Vercel
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for modulo in (auth, motoristas, corridas, malha, ws):
        app.include_router(modulo.rotas)

    @app.get("/saude", tags=["infra"])
    def saude():
        """Health check do Railway."""
        return {
            "status": "ok",
            "nos_na_malha": len(app.state.grafo.nos),
            "motoristas_online": len(app.state.registro),
            "websockets_abertos": app.state.conexoes.total(),
        }

    return app


app = criar_app()
