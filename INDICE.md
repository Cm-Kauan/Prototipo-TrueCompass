# TrueCompass — índice do projeto

Mapa de onde está cada coisa. Projeto acadêmico de Matemática Computacional
Aplicada (USJT).

## Comece por aqui

| Arquivo | Para quê |
|---|---|
| `COMO_RODAR.md` | instalar, rodar os testes, subir o servidor, importar a malha |
| `README.md` | visão do produto — o que o app faz, para quem usa |
| `CLAUDE.md` | decisões de projeto que valem manter (e as armadilhas) |

## Aprendizado do squad

| Arquivo | Assunto |
|---|---|
| `algoritmos/EXPLICACAO.md` | os **algoritmos** em linguagem simples (A\*, busca reversa) |
| `algoritmos/MATEMATICA.md` | as **fórmulas**: de onde vieram e o que quebra se mexer |

## Documentação formal

| Arquivo | Conteúdo |
|---|---|
| `Documentacao_App/TrueCompass_Documentacao_Tecnica.pdf` | doc original — seções 1 a 7 |
| `Documentacao_App/TrueCompass_Secao_C_Fundamentacao_Matematica.pdf` | 9 definições, 14 proposições, 5 corolários, com demonstrações |
| `Documentacao_App/TrueCompass_1a_Parcial_Relatorio_Executivo.pdf` | entrega da 1ª parcial, 8 seções |
| `Documentacao_Aula/` | material da disciplina |

> A Seção C **retifica** a §6 da doc original: a consulta por raio na quadtree
> é O(log n + k), e não O(log n). Ver Proposição C.14.

## Código — backend

As setas de dependência apontam sempre para dentro: `algoritmos/` não conhece
ninguém, e é por isso que seus testes rodam sem banco e sem servidor.

### `algoritmos/` — matemática pura

| Arquivo | O que faz |
|---|---|
| `grafo.py` | malha como grafo ponderado direcionado, grafo reverso, haversine |
| `busca.py` | Dijkstra e A\* na **mesma** rotina (Dijkstra ≡ A\* com h ≡ 0) |
| `matching.py` | pareamento reverso many-to-one — 1 busca em vez de k |
| `quadtree.py` | índice espacial com poda por retângulo |
| `indice_espacial.py` | varredura linear, mantida como **oráculo** dos testes |
| `topologica.py` | algoritmo de Kahn |
| `matriz_mapa.py` | mapa como matriz de células → grafo |
| `semaforo.py` | atraso esperado em cruzamento semaforizado |
| `cidade_exemplo.py` | cidade sintética (mão única, avenidas, rio com 2 pontes) |
| `demo.py` | comparativo medido — `python3 -m algoritmos.demo` |

### `dominio/` — regras de negócio

| Arquivo | O que faz |
|---|---|
| `estados.py` | DAG do ciclo da corrida; Kahn valida no boot |
| `registro.py` | posições dos motoristas em memória (não no banco) |
| `servicos/corrida.py` | orquestra quadtree → busca reversa → A\* |

### `api/` — camada HTTP (FastAPI)

| Arquivo | O que faz |
|---|---|
| `main.py` | app e `lifespan`: valida DAG, carrega malha, constrói reverso |
| `rotas/auth.py` | registro e login (JWT) |
| `rotas/motoristas.py` | ping de GPS, disponibilidade |
| `rotas/corridas.py` | ciclo da corrida |
| `rotas/ws.py` | acompanhamento em tempo real |
| `conexoes.py` | gerenciador de WebSocket |
| `eventos.py` | mensagens do WS e `comitar_e_publicar` |
| `esquemas.py` · `deps.py` | contratos Pydantic e injeção de dependências |

### `infra/` — banco, rede, segredos

| Arquivo | O que faz |
|---|---|
| `osm.py` | Overpass API, parser OSM, poda ao componente fortemente conexo |
| `importar_malha.py` | CLI: gera `dados/malha.json` uma vez, offline |
| `modelos.py` · `banco.py` | tabelas SQLAlchemy e sessão |
| `seguranca.py` | bcrypt e JWT |
| `config.py` | configuração via ambiente |

## Testes — 140 no backend, sem pytest

```bash
for t in algoritmos quadtree osm estados api ws; do python3 tests/test_$t.py; done
```

| Arquivo | Qtd | Cobre |
|---|---:|---|
| `tests/test_algoritmos.py` | 15 | Dijkstra, A\*, pareamento reverso |
| `tests/test_quadtree.py` | 20 | índice espacial, poda, casos degenerados |
| `tests/test_osm.py` | 18 | parser OSM, mão única, poda (sem rede) |
| `tests/test_matriz.py` | 29 | matriz do mapa, semáforos, mapa de produção |
| `tests/test_estados.py` | 18 | Kahn, DAG, transições proibidas |
| `tests/test_api.py` | 26 | ciclo completo via HTTP, auth, concorrência, malha |
| `tests/test_ws.py` | 14 | tempo real, isolamento entre corridas |

Mais 20 verificações de interface em `web/e2e/fluxo.py` (Playwright).

## Mapa — `mapas/centro.mapa`

Matriz 36×36 editável como texto. Um caractere por célula:

| | |
|---|---|
| `.` | rua local, mão dupla |
| `A` | avenida, mais rápida |
| `S` | cruzamento semaforizado |
| `> < ^ v` | mão única |
| `#` | intransponível (quarteirão, rio, parque) |

Edite o arquivo e reinicie o servidor — o grafo é derivado dele no boot.

## Front-end — `web/` (React + Vite)

| Arquivo | O que faz |
|---|---|
| `src/api.js` | cliente HTTP e URL do WebSocket |
| `src/App.jsx` | sessão, tema claro/escuro, carga da malha |
| `src/componentes/Mapa.jsx` | Leaflet: malha, rotas, marcadores |
| `src/componentes/PainelPassageiro.jsx` | pedir corrida e acompanhar |
| `src/componentes/PainelMotorista.jsx` | ficar online, receber, deslocar |
| `src/componentes/LinhaDeEstados.jsx` | o DAG da corrida, visualmente |
| `src/ganchos/usarCorridaAoVivo.js` | assina o WebSocket |
| `e2e/fluxo.py` | teste ponta a ponta (Playwright), 20 verificações |

```bash
cd web && npm install && npm run dev      # http://127.0.0.1:5173
```

Leia `web/README.md` para o roteiro de demonstração.

`Base_Front_End/Front_End.html` — protótipo visual original do squad, mantido
como referência (a paleta do app veio dele).

## Deploy

| Camada | Plataforma | Arquivos |
|---|---|---|
| Back-end | **Railway** | `Procfile`, `railway.json`, `requirements.txt` |
| Front-end | **Vercel** | — |

Serverless não serve para o backend: sem WebSocket e sem processo persistente
para manter o grafo em memória. Mantenha `--workers 1`.

## Resultados medidos

| Substituição | Ganho | Otimalidade |
|---|---|---|
| k Dijkstras → 1 busca reversa | **10,7×** | preservada |
| Dijkstra → A\* | **3,2×** | preservada |
| Varredura linear → quadtree | **154,8×** | preservada |

Em nenhum dos três houve perda de otimalidade: a resposta é a **mesma**,
obtida com menos busca. Reproduza com `python3 -m algoritmos.demo`.
