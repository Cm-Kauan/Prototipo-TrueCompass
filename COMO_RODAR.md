# TrueCompass — como rodar

O repositório tem três partes (ver `INDICE.md`):

```
frontend/     app (React + TypeScript) e web (versão anterior)
backend/      servidor FastAPI
matematica/   algoritmos puros e o mapa em matriz
```

Todos os comandos abaixo partem da **raiz** do repositório, salvo indicação.

## Requisitos

- Python 3.11 ou superior (backend e matemática)
- Node.js 20 ou superior (front-end)

## Instalação do backend

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # a raiz aponta para backend/requirements.txt
```

## Rodar os testes

Não precisa de pytest, banco nem rede — cada arquivo roda sozinho:

```bash
python3 matematica/tests/test_algoritmos.py   # 19 — Dijkstra, A*, pareamento reverso
python3 matematica/tests/test_quadtree.py     # 20 — índice espacial
python3 matematica/tests/test_matriz.py       # 29 — matriz do mapa e semáforos
python3 backend/tests/test_osm.py             # 23 — parser OpenStreetMap
python3 backend/tests/test_estados.py         # 18 — Kahn e DAG da corrida
python3 backend/tests/test_api.py             # 37 — ciclo completo via HTTP
python3 backend/tests/test_ws.py              # 14 — tempo real
```

Todos de uma vez:

```bash
for t in algoritmos quadtree matriz; do python3 matematica/tests/test_$t.py; done
for t in osm estados api ws;        do python3 backend/tests/test_$t.py; done
```

## Ver os algoritmos comparados

```bash
cd matematica && python3 -m algoritmos.demo
```

Mede Dijkstra × A\*, pareamento ingênuo × reverso, e varredura linear × quadtree.

## Subir o servidor

```bash
export JWT_SECRET="qualquer-coisa-em-desenvolvimento"     # Windows: $env:JWT_SECRET="..."
uvicorn --app-dir backend api.main:app --reload
```

(ou, de dentro de `backend/`: `uvicorn api.main:app --reload`)

- API: http://127.0.0.1:8000
- **Documentação interativa: http://127.0.0.1:8000/docs** — dá para testar todos
  os endpoints pelo navegador, sem Postman
- Saúde: http://127.0.0.1:8000/saude

O servidor carrega, nesta ordem: a malha real (`backend/dados/malha.json`), o
mapa em matriz (`matematica/mapas/centro.mapa`) ou, sem nenhum dos dois, a
cidade sintética. Os caminhos funcionam de qualquer pasta de onde ele for
iniciado. Para usar a matriz com a malha presente: `MALHA_ARQUIVO=` (vazio).

## Subir o app

Com o backend no ar:

```bash
cd frontend/app
npm install
npm run dev            # http://localhost:5180
```

O front anterior continua em `frontend/web` (`npm run dev`, porta 5173).

## Importar a malha real do OpenStreetMap

```bash
cd backend
python3 -m infra.importar_malha --sul -23.615 --oeste -46.705 \
                                --norte -23.505 --leste -46.545
```

Roda **uma vez**, offline, e gera `backend/dados/malha.json` (versionado). O
servidor lê esse arquivo no boot — nunca consulta a Overpass em produção.
Caixas grandes demoram e a Overpass pode recusar; comece por um bairro.

## Variáveis de ambiente

Copie `backend/.env.exemplo` para `backend/.env`. Só `JWT_SECRET` é realmente
obrigatória em desenvolvimento; o resto tem padrão razoável. Caminhos
relativos (como `MALHA_ARQUIVO`) partem de `backend/`.

## Organização das pastas

```
matematica/algoritmos/   matemática pura — não importa FastAPI nem SQL
backend/dominio/         regras de negócio — não importa HTTP
backend/api/             camada HTTP (FastAPI)
backend/infra/           banco, rede, segredos
frontend/app/            interface (React + TypeScript)
```

A regra: **as setas de dependência apontam sempre para dentro**.
`matematica/` não conhece ninguém, e é por isso que seus testes rodam sem banco
e sem servidor. O backend encontra a pasta `matematica/` sozinho, por
`backend/matematica_no_caminho.py`.

Leia `matematica/algoritmos/EXPLICACAO.md` para entender os algoritmos em
linguagem simples, e `CLAUDE.md` para as decisões de projeto que valem manter.

## Deploy

- **Back-end → Railway**, com a **raiz** do repositório (o backend importa
  `matematica/`). `Procfile`, `railway.json` e `requirements.txt` da raiz já
  apontam para `backend/`. Health check em `/saude`. Adicione o plugin MySQL e
  defina `JWT_SECRET` e `CORS_ORIGENS`.
- **Front-end → Vercel**, diretório raiz `frontend/app`, com `VITE_API_URL`
  apontando para o backend.

Mantenha `--workers 1`: cada worker carrega sua própria cópia do grafo em
memória, e o GIL não paraleliza a busca mesmo.
