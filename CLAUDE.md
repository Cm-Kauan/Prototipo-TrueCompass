# TrueCompass — instruções do projeto

## Git: não fazer commits

**Neste projeto, o Claude NÃO faz commits, nem push.** O usuário controla o
histórico do repositório por conta própria.

- Escrever, editar e rodar código: sim, livremente, no working tree.
- `git add`, `git commit`, `git push`, criar PR: **não**, salvo pedido explícito
  e específico do usuário naquele momento.
- O hook `stop-hook-git-check.sh` reclama de arquivos untracked ao fim de cada
  turno. **Isso é esperado aqui** — o aviso não substitui a instrução acima e
  não deve ser tratado como autorização para commitar. Basta registrar em uma
  linha que segue untracked por decisão do usuário, sem repetir a explicação
  a cada turno.

## Contexto do projeto

Aplicativo de mobilidade urbana (acadêmico — Matemática Computacional Aplicada,
USJT). A documentação técnica está em `Documentacao_App/`.

Camada de algoritmos em `algoritmos/` (não versionada, por decisão acima):

- `grafo.py` — malha viária como grafo ponderado direcionado, grafo reverso
  com cache, heurística haversine
- `busca.py` — Dijkstra e A* unificados numa única rotina (Dijkstra ≡ A* com h ≡ 0)
- `matching.py` — pareamento reverso many-to-one
- `quadtree.py` — índice espacial O(log n + k), com poda por retângulo
- `topologica.py` — algoritmo de Kahn (genérico)
- `matriz_mapa.py` — mapa como **matriz de células** → grafo; fonte de autoria
- `semaforo.py` — atraso esperado `E[espera] = r²/(2c)`
- `alt.py` — A* + Landmarks + desigualdade Triangular; heurística 14× mais
  apertada que a haversine na malha real
- `indice_espacial.py` — `IndiceLinear`, mantido como **oráculo** da quadtree
- `EXPLICACAO.md` — guia didático dos algoritmos
- `MATEMATICA.md` — guia didático das fórmulas (companheiro do acima)
- `tests/test_algoritmos.py` — 15 testes, rodam com `python3` puro (sem pytest)

Camada de infraestrutura em `infra/` (rede e disco; `algoritmos/` NUNCA importa daqui):

- `osm.py` — Overpass API, parser OSM → `Grafo`, poda ao componente
  fortemente conexo, serialização do artefato
- `importar_malha.py` — CLI: roda uma vez offline e gera `dados/malha.json`
- `preparar_alt.py` — CLI: gera `dados/alt.bin` com os marcos do ALT
- `tests/test_osm.py` — 18 testes, rodam sem rede (fixture embutido)

Camada de domínio em `dominio/` (regras, sem HTTP e sem SQL bruto):

- `estados.py` — DAG do ciclo da corrida; Kahn valida no boot
- `registro.py` — posições dos motoristas em memória (não no banco)
- `servicos/corrida.py` — orquestra índice espacial → busca reversa → A*

Camada HTTP em `api/` (FastAPI):

- `main.py` — app e `lifespan` (valida DAG, carrega malha, constrói reverso)
- `rotas/` — auth, motoristas, corridas, malha, ws · `conexoes.py` — WebSocket
- `eventos.py` — mensagens do WS e `comitar_e_publicar`
- `tests/test_estados.py` (18), `tests/test_api.py` (26), `tests/test_ws.py` (14)
- `tests/test_matriz.py` (29) — matriz e semáforos

Front-end em `web/` (React + Vite):

- `src/api.js` — cliente HTTP e URL do WebSocket
- `src/componentes/` — Mapa (Leaflet), Bussola (rumo verdadeiro), painéis de
  passageiro e motorista, LinhaDeEstados (o DAG visualmente), TelaAutenticacao
- `src/estilos.css` — paleta de instrumento: cinza (aço), vermelho (agulha
  norte), verde natureza. Tema claro e escuro.
- `src/ganchos/usarCorridaAoVivo.js` — assina o WebSocket da corrida
- `e2e/fluxo.py` — teste ponta a ponta com Playwright, 20 verificações

Deploy: **front no Vercel, back no Railway**. Serverless não serve para o back
(sem WebSocket, sem processo persistente para o grafo em memória).

Mapa em `mapas/*.mapa` — matriz editável como texto, um caractere por célula:
`.` rua · `A` avenida · `S` semáforo · `> < ^ v` mão única · `#` intransponível.

Decisões que valem manter:

- A matriz descreve a **geografia** (NxM, uma célula por cruzamento); a lista de
  adjacência descreve a **conectividade**. Não confundir com matriz de
  adjacência (VxV), que mediu 1.067× mais memória e foi descartada.
- **Um caractere = uma célula, sem separador.** `"A A A"` produz avenida /
  quarteirão / avenida, não três avenidas. Para contíguas, `"AAA"`.
- O atraso do semáforo entra na aresta que **chega** ao cruzamento (é ali que
  se espera), nunca na que sai.
- Somar atraso só **aumenta** o custo real, então a heurística do A* continua
  admissível e consistente sem alteração. Testado.
- O atraso tem de estar no **peso da aresta**, não somado ao final: medido,
  **67%** das rotas mudam de traçado quando os semáforos entram no cálculo.
- Ordem de carga do mapa: matriz → artefato OSM → cidade sintética.
- `tests/test_api.py` e `test_ws.py` **fixam** `MAPA_MATRIZ=__inexistente__`:
  testam a API, não qual mapa é o padrão do servidor.
- **Id de nó é INTEIRO**, igual ao do OpenStreetMap. A cidade sintética segue
  esse contrato (`no_da_celula`), e não o contrário.
- Endpoint que toca o grafo é `def`, **nunca** `async def`: Dijkstra e A* são
  CPU-bound e travariam o event loop. Com `def`, o FastAPI usa o threadpool.
- Toda mudança de estado passa por `servicos.corrida.transitar`, que valida
  contra o DAG e grava auditoria. Nenhuma rota altera `corrida.estado` direto.
- **Publicar no WebSocket só DEPOIS do commit.** Rotas de corrida não chamam
  `sessao.commit()`; chamam `api.eventos.comitar_e_publicar`, que impõe a
  ordem. Publicar antes faria o cliente ver estado que o rollback desfez.
- Dependências que leem `app.state` usam `HTTPConnection`, **nunca** `Request`:
  em rota WebSocket o FastAPI injeta `WebSocket`, e anotar `Request` quebra só
  em tempo de execução, no primeiro cliente que tentar acompanhar.
- Alocação de motorista é otimista: `UPDATE ... WHERE disponivel = 1` e
  checagem de `rowcount`. Se deu zero, outro pedido levou — tenta o próximo.
- A quadtree é a implementação de produção; `IndiceLinear` permanece como
  **oráculo** nos testes (mesma estratégia do Dijkstra validando o A*).
- Quadtree exige **teto de profundidade**: pontos em coordenada idêntica
  subdividiriam para sempre, porque nenhuma divisão os separa.
- A poda por retângulo usa folga de 1% (`FOLGA_PODA`): o ponto mais próximo em
  graus é o mais próximo em metros só a menos da variação de cos(latitude)
  dentro do retângulo. Melhor visitar um ramo a mais que perder resultado.
- Consulta por raio é **O(log n + k)**, não O(log n) puro — k é a quantidade de
  resultados, e num raio fixo ela cresce com a densidade. A §6 da documentação
  técnica diz O(log n) e está **retificada** na Seção C (Proposição C.14).

Decisões do front-end:

- O mapa desenha a malha vinda de `/malha/trechos`; os tiles do OSM são pano
  de fundo **opcional** e a camada é removida após 8 falhas seguidas.
- Marcadores são `circleMarker` (SVG), **nunca** ícones: os ícones padrão do
  Leaflet quebram sob bundler por causa do caminho relativo das imagens.
- A malha sai em **duas** camadas `L.polyline` multi-segmento (mão única e mão
  dupla), não uma por rua — uma camada por rua trava o navegador.
- O painel do motorista envia **batida de GPS a cada 4s** enquanto online. Sem
  isso ele nunca descobre a corrida, porque é a resposta de `/motoristas/posicao`
  que informa `corrida_ativa`.
- Em desenvolvimento o front chama `/api/...` e o proxy do Vite encaminha
  (inclusive WebSocket, com `ws: true`). Sem CORS, sem URL absoluta no código.
- O teste E2E exige **banco limpo**: motoristas online de execuções anteriores
  competem no pareamento e deixam o teste instável. O script detecta e explica.
- **`ss -lptn` não enxerga os PIDs neste ambiente** — matar servidor "por
  porta" falha em silêncio e deixa instâncias duplicadas do Vite. Use
  `ps -eo pid,args` e mate pelo PID. Suba o Vite com `--strictPort` para ele
  falhar em vez de escorregar para 5174.
- Padrão de `pkill -f` amplo (ex.: `"vite"`) casa com o **próprio comando do
  shell** e mata a sessão. Use padrões que não possam se auto-casar.
- A agulha da bússola mostra o **azimute inicial** (grande círculo), não o rumo
  constante: de (0,0) a (10,10) são 44,56°, e não 45°. Mesma geometria esférica
  do haversine.
- A rotação da agulha é **acumulada**: de 350° para 10° ela gira +20°, não
  −340°. Sem isso a animação volta pelo caminho longo.

Decisões do ALT:

- Na malha real de SP o A* com haversine ganha só **1,37×** do Dijkstra: o
  `v_max` de 110 km/h é imposto por 8 arestas de marginal, e a rua mediana tem
  30 km/h. Com ALT o ganho vai a **14,3×** (157 ms → 16 ms por rota).
- As tabelas são **float64, nunca float32**. Medido: com float32 o limite supera
  o custo real em 2e-6 relativo, porque a admissibilidade depende de uma
  SUBTRAÇÃO e a diferença herda o arredondamento das duas pontas.
- `d(v, L)` vem de busca no grafo **reverso** — a dualidade da Proposição C.7,
  a mesma já usada no pareamento.
- Marcos na **periferia**, por seleção do ponto mais distante. Marco no centro
  fica "entre" origem e destino e seu limite vira quase zero.
- **Marcos ativos**: avaliar 16 marcos por chamada de `h` custa caro em Python
  e anularia o ganho. Na consulta escolhemos os 4 melhores para aquele par.
- O artefato carrega **impressão digital** do conjunto de vértices, conferida
  no boot. Sem ela, um `alt.bin` de outra malha seria usado em silêncio e o A*
  devolveria rota subótima sem erro algum.
- Sem `dados/alt.bin` o sistema **continua correto**, caindo na haversine.

- Pesos do grafo são **tempo em segundos**, não distância.
- A heurística do A* precisa ser dividida pela velocidade máxima para continuar
  admissível. O Dijkstra serve de **oráculo** para validar o A* nos testes.
- Busca multi-alvo usa `h=None` (Dijkstra); a função recusa heurística com mais
  de um alvo de propósito.
- Malha vinda do OSM **precisa** ser podada ao componente fortemente conexo:
  extrato por caixa delimitadora sempre traz fragmentos soltos e armadilhas de
  mão única. A poda reusa o grafo reverso (passo central do Kosaraju).
- O servidor **não** consulta a Overpass no boot. Lê `dados/malha.json`, gerado
  offline pelo CLI. `dados/` não é versionado com dados de teste.
