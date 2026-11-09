# -*- coding: utf-8 -*-
"""Gera o banner do TrueCompass em PDF, no tamanho exato de impressão.

    90 cm de largura x 120 cm de altura, retrato.

Tipografia conforme a especificação da disciplina:
    título 80 pt · títulos de seção 36 a 40 pt · corpo e bullets 21 a 26 pt
    (o mínimo de 20 pt é respeitado em todo o banner, inclusive nas legendas).

Fontes: Montserrat, em `fontes/`; na falta dela, Liberation Sans, que é
metricamente compatível com a Arial — as duas são permitidas. Para baixar a
Montserrat sem navegador:

    npm pack @fontsource/montserrat && tar xzf fontsource-montserrat-*.tgz
    python3 -c "from fontTools.ttLib import TTFont; \\
        [TTFont(f'package/files/montserrat-latin-{p}-normal.woff').save(f'fontes/Montserrat-{p}.ttf') \\
         for p in ('400','600','700','800')]"

Uso:
    python3 docs/banner/gerar_banner.py              # gera banner_truecompass.pdf
    python3 docs/banner/gerar_banner.py --previa     # e exporta um PNG de prova

Os números impressos saem das medições do próprio repositório
(`matematica/algoritmos/demo.py` e `backend/infra/preparar_alt.py`). Se uma
medição mudar, atualize MEDIDAS, logo abaixo — e só ali.
"""
from __future__ import annotations

import math
import os
import sys

from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

AQUI = os.path.dirname(os.path.abspath(__file__))
CAPTURAS = os.path.join(AQUI, "capturas")
SAIDA = os.path.join(AQUI, "banner_truecompass.pdf")

LARGURA, ALTURA = 90 * cm, 120 * cm


# ----------------------------------------------------------------- tipografia
def _registrar_fontes() -> tuple[str, str, str, str]:
    pasta = os.path.join(AQUI, "fontes")
    pesos = {"400": "Banner", "600": "Banner-Semi", "700": "Banner-Bold", "800": "Banner-Black"}
    if all(os.path.exists(os.path.join(pasta, f"Montserrat-{p}.ttf")) for p in pesos):
        for peso, nome in pesos.items():
            pdfmetrics.registerFont(TTFont(nome, os.path.join(pasta, f"Montserrat-{peso}.ttf")))
        return "Banner", "Banner-Semi", "Banner-Bold", "Banner-Black"

    liberation = "/usr/share/fonts/truetype/liberation"
    if os.path.exists(os.path.join(liberation, "LiberationSans-Regular.ttf")):
        pdfmetrics.registerFont(TTFont("Banner", f"{liberation}/LiberationSans-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Banner-Bold", f"{liberation}/LiberationSans-Bold.ttf"))
        print("aviso: Montserrat ausente — usando Liberation Sans (métrica da Arial).")
        return "Banner", "Banner-Bold", "Banner-Bold", "Banner-Bold"

    print("aviso: nenhuma TTF encontrada — usando Helvetica (métrica da Arial).")
    return "Helvetica", "Helvetica-Bold", "Helvetica-Bold", "Helvetica-Bold"


REG, SEMI, BOLD, BLACK = _registrar_fontes()
MONO = "Courier-Bold"

# Caractere fora da fonte sai BRANCO no PDF, sem erro nenhum. Como a Montserrat
# do Google vem no subconjunto "latin", setas e símbolos matemáticos não estão
# lá — então todo texto desenhado passa por esta conferência.
def _glifos_da_fonte() -> set[int] | None:
    caminho = os.path.join(AQUI, "fontes", "Montserrat-400.ttf")
    if not os.path.exists(caminho):
        return None
    try:
        from fontTools.ttLib import TTFont as _TT
        return set(_TT(caminho).getBestCmap())
    except ImportError:
        return None


GLIFOS = _glifos_da_fonte()
SEM_GLIFO: set[str] = set()


def _conferir(txto: str) -> str:
    if GLIFOS is not None:
        SEM_GLIFO.update(ch for ch in txto if ord(ch) not in GLIFOS and ch != "\n")
    return txto


# --------------------------------------------------------------------- paleta
PAPEL = (0.961, 0.961, 0.945)
TINTA = (0.078, 0.086, 0.094)
SUAVE = (0.345, 0.376, 0.404)
ACO = (0.231, 0.251, 0.275)
VERDE = (0.180, 0.482, 0.310)
VERDE_CLARO = (0.361, 0.604, 0.420)
VERMELHO = (0.800, 0.231, 0.275)
LATAO = (0.620, 0.478, 0.263)
ESCURO = (0.067, 0.075, 0.082)
CARTAO = (1, 1, 1)
BORDA = (0.831, 0.831, 0.804)
TRILHO = (0.906, 0.906, 0.886)

# ------------------------------------------------------------------- medições
MEDIDAS = {
    "nos": "118.267", "arestas": "180.424", "semaforos": "3.542",
    "dijkstra_nos": 1_703_955, "haversine_nos": 1_329_866, "alt_nos": 119_398,
    "haversine_ms": 172, "alt_ms": 14,
    "testes": 183, "e2e": 20,
}
REPO = "https://github.com/Cm-Kauan/Prototipo-TrueCompass"

# ------------------------------------------------------------------ utilidades
c = pdfcanvas.Canvas(SAIDA, pagesize=(LARGURA, ALTURA))
c.setTitle("TrueCompass — banner do projeto")
c.setAuthor("Squad TrueCompass — Universidade São Judas Tadeu")


def larg(txto: str, fonte: str, tam: float) -> float:
    return pdfmetrics.stringWidth(txto, fonte, tam)


def quebrar(txto: str, fonte: str, tam: float, largura: float) -> list[str]:
    linhas: list[str] = []
    for bloco in txto.split("\n"):
        atual = ""
        for palavra in bloco.split(" "):
            teste = palavra if not atual else f"{atual} {palavra}"
            if larg(teste, fonte, tam) <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas


def texto(x, y, txto, fonte=REG, tam=24, cor=TINTA, alinhar="esq"):
    c.setFont(fonte, tam)
    c.setFillColorRGB(*cor)
    {"centro": c.drawCentredString, "dir": c.drawRightString}.get(alinhar, c.drawString)(x, y, _conferir(txto))


def paragrafo(x, y, txto, largura, fonte=REG, tam=24, cor=TINTA, entrelinha=1.40) -> float:
    """Escreve de cima para baixo a partir da linha de base `y`. Devolve o y da última linha."""
    c.setFont(fonte, tam)
    c.setFillColorRGB(*cor)
    for linha in quebrar(_conferir(txto), fonte, tam, largura):
        c.drawString(x, y, linha)
        y -= tam * entrelinha
    return y + tam * entrelinha


def alt_paragrafo(txto, largura, fonte=REG, tam=24, entrelinha=1.40) -> float:
    return len(quebrar(txto, fonte, tam, largura)) * tam * entrelinha


def caixa(x, y, l, a, preenche=CARTAO, borda=BORDA, raio=0.4 * cm, espessura=2.2):
    if preenche:
        c.setFillColorRGB(*preenche)
    if borda:
        c.setStrokeColorRGB(*borda)
        c.setLineWidth(espessura)
    c.roundRect(x, y - a, l, a, raio, stroke=1 if borda else 0, fill=1 if preenche else 0)


def titulo_secao(x, y, txto, largura, cor=VERDE, tam=40) -> float:
    c.setFillColorRGB(*cor)
    c.rect(x, y, largura, 0.34 * cm, stroke=0, fill=1)
    texto(x, y - 1.52 * cm, txto.upper(), BLACK, tam, TINTA)
    return y - 2.45 * cm


def seta(x1, y1, x2, y2, cor=ACO, espessura=3.4, cabeca=0.4 * cm):
    c.setStrokeColorRGB(*cor)
    c.setLineWidth(espessura)
    c.setLineCap(1)
    c.line(x1, y1, x2, y2)
    ang = math.atan2(y2 - y1, x2 - x1)
    c.setFillColorRGB(*cor)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - cabeca * math.cos(ang - 0.42), y2 - cabeca * math.sin(ang - 0.42))
    p.lineTo(x2 - cabeca * math.cos(ang + 0.42), y2 - cabeca * math.sin(ang + 0.42))
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def bussola(cx, cy, r, aro=(1, 1, 1), norte=VERMELHO, sul=(0.78, 0.78, 0.76)):
    c.setStrokeColorRGB(*aro)
    c.setLineWidth(r * 0.085)
    c.circle(cx, cy, r, stroke=1, fill=0)
    c.setLineWidth(r * 0.05)
    for i in range(12):
        a = math.pi / 6 * i
        c.line(cx + r * 0.82 * math.sin(a), cy + r * 0.82 * math.cos(a),
               cx + r * 0.95 * math.sin(a), cy + r * 0.95 * math.cos(a))
    for alvo, cor in (((0, r * 0.74), norte), ((0, -r * 0.74), sul)):
        p = c.beginPath()
        p.moveTo(cx + alvo[0], cy + alvo[1])
        p.lineTo(cx + r * 0.2, cy)
        p.lineTo(cx - r * 0.2, cy)
        p.close()
        c.setFillColorRGB(*cor)
        c.drawPath(p, stroke=0, fill=1)


def imagem(arquivo, x, y, largura) -> float:
    img = ImageReader(os.path.join(CAPTURAS, arquivo))
    pw, ph = img.getSize()
    a = largura * ph / pw
    c.drawImage(img, x, y - a, largura, a, mask=None)
    c.setStrokeColorRGB(*BORDA)
    c.setLineWidth(1.6)
    c.rect(x, y - a, largura, a, stroke=1, fill=0)
    return y - a


# ======================================================================= fundo
c.setFillColorRGB(*PAPEL)
c.rect(0, 0, LARGURA, ALTURA, stroke=0, fill=1)

MARGEM = 4 * cm
UTIL = LARGURA - 2 * MARGEM          # 82 cm
COL_L = 26 * cm
COLS = [MARGEM, MARGEM + 28 * cm, MARGEM + 56 * cm]

BANDA_ALT = 22 * cm
BANDA_BASE = ALTURA - BANDA_ALT
Y_COL = BANDA_BASE - 2.7 * cm        # topo das colunas
RODAPE_TOPO = 24.2 * cm
RODAPE_BASE = 5.6 * cm

# =================================================================== cabeçalho
c.setFillColorRGB(*ESCURO)
c.rect(0, BANDA_BASE, LARGURA, BANDA_ALT, stroke=0, fill=1)
c.setFillColorRGB(*VERDE)
c.rect(0, BANDA_BASE, LARGURA, 0.42 * cm, stroke=0, fill=1)

for lx, rotulo in ((MARGEM, "LOGOTIPO DA UNIVERSIDADE"),
                   (LARGURA - MARGEM - 15.5 * cm, "LOGOTIPO DO CURSO")):
    c.setStrokeColorRGB(0.27, 0.29, 0.31)
    c.setLineWidth(2.0)
    c.setDash(7, 7)
    c.roundRect(lx, ALTURA - 6.5 * cm, 15.5 * cm, 4.0 * cm, 0.3 * cm, stroke=1, fill=0)
    c.setDash()
    texto(lx + 7.75 * cm, ALTURA - 4.75 * cm, rotulo, SEMI, 21, (0.40, 0.43, 0.45), "centro")

# a marca encostada no título: largura medida, não chutada
TITULO = "TrueCompass"
lt = larg(TITULO, BLACK, 80)
conjunto = 2.35 * cm * 2 + 1.5 * cm + lt
x0 = (LARGURA - conjunto) / 2
bussola(x0 + 2.35 * cm, ALTURA - 9.7 * cm, 2.35 * cm)
texto(x0 + 2.35 * cm * 2 + 1.5 * cm, ALTURA - 10.65 * cm, TITULO, BLACK, 80, (1, 1, 1))

SUB = ("Alocação ótima de motoristas e rota de menor tempo em malha viária real, "
       "com corretude demonstrada e ganho medido")
y = ALTURA - 13.6 * cm
for linha in quebrar(SUB, SEMI, 38, 74 * cm):
    texto(LARGURA / 2, y, linha, SEMI, 38, VERDE_CLARO, "centro")
    y -= 1.55 * cm

c.setStrokeColorRGB(0.21, 0.23, 0.25)
c.setLineWidth(2)
c.line(MARGEM, ALTURA - 15.9 * cm, LARGURA - MARGEM, ALTURA - 15.9 * cm)

y = ALTURA - 17.3 * cm
for linha in [
    "Bianca Murcela Mascamudo · RA 8261104797      Carolina Chaves · RA 826182449      "
    "Carolina Yukari Kague · RA 8261110898",
    "Gabryela Araujo · RA 826199094      Kauan Sousa · RA 8261113181      "
    "Wildiner Lopes · RA 8261102715",
]:
    texto(LARGURA / 2, y, linha, REG, 25, (0.87, 0.87, 0.85), "centro")
    y -= 1.45 * cm

texto(LARGURA / 2, ALTURA - 19.9 * cm, "Orientador:  Prof. Raulison Resende", SEMI, 27, (1, 1, 1), "centro")
texto(LARGURA / 2, ALTURA - 21.4 * cm,
      "Universidade São Judas Tadeu  ·  Matemática Computacional Aplicada (0064481)  ·  "
      "Campus ____________  ·  2026/2", SEMI, 25, (0.80, 0.66, 0.44), "centro")

# ================================================================== COLUNA 1
x, y = COLS[0], Y_COL
y = titulo_secao(x, y, "Contexto e problema", COL_L, VERMELHO)

for titulo, corpo in [
    ("A distância em linha reta mente.",
     "No cenário medido do projeto, um motorista a 275 m do passageiro leva 5,8 min para "
     "chegar; outro, a 548 m, leva 1,0 min — o primeiro está do outro lado do rio."),
    ("k candidatos, k varreduras do grafo.",
     "A alocação ingênua roda uma busca de rota completa para cada motorista candidato. "
     "É computação jogada fora em cada pedido, sob pressão de latência."),
    ("Semáforo não é detalhe de acabamento.",
     "Com a espera esperada dentro do peso da aresta, 67% das rotas mudam de traçado. "
     "Somado só no fim, o atraso devolve a rota errada."),
    ("Quem paga a conta.",
     "O passageiro espera mais do que precisaria, o motorista roda sem receber e a "
     "plataforma paga infraestrutura pelo desperdício."),
]:
    c.setFillColorRGB(*VERMELHO)
    c.circle(x + 0.3 * cm, y - 0.3 * cm, 0.25 * cm, stroke=0, fill=1)
    texto(x + 1.05 * cm, y - 0.58 * cm, titulo, BOLD, 25, TINTA)
    y = paragrafo(x + 1.05 * cm, y - 2.0 * cm, corpo, COL_L - 1.05 * cm, REG, 24, SUAVE)
    y -= 1.6 * cm

y -= 0.4 * cm
y = titulo_secao(x, y, "Objetivos", COL_L, VERDE)

GERAL = ("Formalizar a malha viária como grafo ponderado direcionado G = (V, E, w), com w em "
         "segundos, e implementar a camada algorítmica que devolve o motorista de menor tempo "
         "real de chegada e a rota ótima até o destino — com corretude demonstrada "
         "matematicamente e ganho medido experimentalmente.")
a_geral = alt_paragrafo(GERAL, COL_L - 2.2 * cm, REG, 24) + 3.2 * cm
caixa(x, y + 0.5 * cm, COL_L, a_geral, CARTAO, VERDE, espessura=3)
texto(x + 1.1 * cm, y - 0.65 * cm, "OBJETIVO GERAL", BLACK, 24, VERDE)
paragrafo(x + 1.1 * cm, y - 2.3 * cm, GERAL, COL_L - 2.2 * cm, REG, 24, TINTA)
y = y + 0.5 * cm - a_geral - 1.5 * cm

texto(x, y, "OBJETIVOS ESPECÍFICOS — ETAPAS CONCLUÍDAS", BLACK, 24, ACO)
y -= 1.45 * cm
for i, item in enumerate([
    "Modelar a malha como grafo direcionado em lista de adjacência, O(V + E), e o ciclo da corrida como DAG.",
    "Unificar Dijkstra e A* numa só rotina — o Dijkstra é o A* com h = 0 — e provar a heurística admissível e consistente.",
    "Parear k motoristas com UMA busca no grafo reverso: a distância de p até m no grafo invertido é a de m até p no original.",
    "Indexar as posições em quadtree e ordenar o fluxo de estados pelo algoritmo de Kahn.",
    "Apertar a heurística com ALT — marcos e desigualdade triangular — na malha real do OpenStreetMap.",
    "Validar por oráculo e expor tudo numa aplicação web: API FastAPI e app React com mapa e WebSocket.",
], 1):
    c.setFillColorRGB(*VERDE)
    c.circle(x + 0.5 * cm, y - 0.26 * cm, 0.5 * cm, stroke=0, fill=1)
    texto(x + 0.5 * cm, y - 0.55 * cm, str(i), BLACK, 23, (1, 1, 1), "centro")
    y = paragrafo(x + 1.55 * cm, y, item, COL_L - 1.55 * cm, REG, 24, TINTA)
    y -= 1.3 * cm

y -= 0.6 * cm
A_MALHA = 9.6 * cm
caixa(x, y, COL_L, A_MALHA, (0.937, 0.953, 0.941), VERDE_CLARO, espessura=2.6)
texto(x + 1.1 * cm, y - 1.5 * cm, "A MALHA QUE O SERVIDOR CARREGA", BLACK, 24, VERDE)
paragrafo(x + 1.1 * cm, y - 3.2 * cm,
          f"Centro expandido de São Paulo, extraído do OpenStreetMap pela Overpass e podado ao "
          f"maior componente fortemente conexo: {MEDIDAS['nos']} cruzamentos, "
          f"{MEDIDAS['arestas']} trechos de rua e {MEDIDAS['semaforos']} semáforos — "
          f"em memória, em 1,3 s de subida.", COL_L - 2.2 * cm, REG, 23, SUAVE)
y -= A_MALHA
FIM_C1 = y

# ================================================================== COLUNA 2
x, y = COLS[1], Y_COL
y = titulo_secao(x, y, "Metodologia e arquitetura", COL_L, ACO)
y = paragrafo(x, y, "Quatro camadas, com as setas de dependência sempre apontando para dentro. "
                    "A camada matemática não importa ninguém — por isso seus testes rodam sem "
                    "banco, sem servidor e sem rede.", COL_L, REG, 24, SUAVE)
y -= 1.5 * cm

CAMADAS = [
    ("frontend/ — app React + TypeScript", "mapa Leaflet, bússola, folha arrastável, WebSocket", VERDE_CLARO),
    ("backend/api/ — FastAPI", "rotas HTTP e WebSocket; publica só DEPOIS do commit", ACO),
    ("backend/dominio/ — regras do negócio", "DAG da corrida, alocação otimista, tarifa", LATAO),
    ("matematica/algoritmos/ — matemática pura", "grafo · A*/Dijkstra · ALT · quadtree · Kahn · matriz · semáforo", VERDE),
]
A_CAM, G_CAM = 3.5 * cm, 1.0 * cm
for i, (nome, nota, cor) in enumerate(CAMADAS):
    cy = y - i * (A_CAM + G_CAM)
    caixa(x, cy, COL_L, A_CAM, CARTAO, cor, espessura=3)
    c.setFillColorRGB(*cor)
    c.rect(x, cy - A_CAM, 0.5 * cm, A_CAM, stroke=0, fill=1)
    texto(x + 1.1 * cm, cy - 1.35 * cm, nome, BOLD, 24, TINTA)
    texto(x + 1.1 * cm, cy - 2.72 * cm, nota, REG, 21, SUAVE)
    if i < len(CAMADAS) - 1:
        seta(x + COL_L / 2, cy - A_CAM - 0.12 * cm, x + COL_L / 2, cy - A_CAM - G_CAM + 0.18 * cm, ACO, 3.6)
y -= len(CAMADAS) * A_CAM + (len(CAMADAS) - 1) * G_CAM
y -= 1.3 * cm
texto(x, y, "Matriz de adjacência V×V mediu 1.067× mais memória: descartada.", REG, 21, SUAVE)
y -= 2.0 * cm

texto(x, y, "O CAMINHO DE UM PEDIDO DE CORRIDA", BLACK, 25, TINTA)
y -= 1.7 * cm
PIPE = [
    ("1", "Pedido", "o passageiro marca origem e destino", VERDE),
    ("2", "Quadtree", "filtra os motoristas do entorno em O(log n + k)", LATAO),
    ("3", "Busca reversa", "UMA busca no grafo invertido mede o tempo real de todos", VERMELHO),
    ("4", "A* com ALT", "marcos + desigualdade triangular devolvem a rota ótima", VERDE),
    ("5", "DAG da corrida", "a transição de estado é validada antes de existir", ACO),
    ("6", "Commit, e só então WebSocket", "o cliente nunca vê estado que o rollback desfez", VERDE_CLARO),
]
A_PIPE, G_PIPE = 3.9 * cm, 0.8 * cm
for i, (num, nome, nota, cor) in enumerate(PIPE):
    caixa(x, y, COL_L, A_PIPE, CARTAO, BORDA, espessura=2)
    c.setFillColorRGB(*cor)
    c.circle(x + 1.3 * cm, y - 1.35 * cm, 0.75 * cm, stroke=0, fill=1)
    texto(x + 1.3 * cm, y - 1.68 * cm, num, BLACK, 29, (1, 1, 1), "centro")
    texto(x + 2.6 * cm, y - 1.6 * cm, nome, BOLD, 25, cor)
    paragrafo(x + 2.6 * cm, y - 3.0 * cm, nota, COL_L - 3.2 * cm, REG, 21, SUAVE, 1.25)
    y -= A_PIPE
    if i < len(PIPE) - 1:
        seta(x + 1.3 * cm, y - 0.1 * cm, x + 1.3 * cm, y - G_PIPE + 0.15 * cm, ACO, 3.2)
        y -= G_PIPE

y -= 1.5 * cm
texto(x, y, "DA MATRIZ DE CÉLULAS AO GRAFO PONDERADO", BLACK, 25, TINTA)
y -= 1.6 * cm
A_MAT = 10.9 * cm
caixa(x, y, COL_L, A_MAT, CARTAO, BORDA, espessura=2)

GRADE = [".A..", ".AS.", "#A..", ".A>."]
cel = 1.35 * cm
gx, gy = x + 1.2 * cm, y - 1.3 * cm
CORES_CEL = {".": (0.93, 0.93, 0.91), "A": (0.83, 0.88, 0.85), "S": (0.97, 0.87, 0.87),
             "#": (0.78, 0.78, 0.76), ">": (0.94, 0.91, 0.84)}
for i, linha in enumerate(GRADE):
    for j, ch in enumerate(linha):
        px, py = gx + j * cel, gy - i * cel
        c.setFillColorRGB(*CORES_CEL[ch])
        c.setStrokeColorRGB(*BORDA)
        c.setLineWidth(1.4)
        c.rect(px, py - cel, cel, cel, stroke=1, fill=1)
        texto(px + cel / 2, py - cel * 0.7, ch, MONO, 21, ACO, "centro")

seta(gx + 4 * cel + 0.6 * cm, gy - 2 * cel, gx + 4 * cel + 2.2 * cm, gy - 2 * cel, ACO, 4)
nx, ny = gx + 4 * cel + 3.3 * cm, gy - 0.8 * cm
PONTOS = [(0, 0), (1.8 * cm, 0.2 * cm), (0.3 * cm, -1.9 * cm), (2.2 * cm, -2.2 * cm), (1.1 * cm, -3.9 * cm)]
c.setStrokeColorRGB(*ACO)
c.setLineWidth(2.6)
for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4)]:
    c.line(nx + PONTOS[a][0], ny + PONTOS[a][1], nx + PONTOS[b][0], ny + PONTOS[b][1])
for k, (px, py) in enumerate(PONTOS):
    c.setFillColorRGB(*(VERMELHO if k == 3 else VERDE))
    c.circle(nx + px, ny + py, 0.4 * cm, stroke=0, fill=1)

texto(x + 1.2 * cm, y - 7.5 * cm,
      "Um caractere = uma célula.   .  rua     A  avenida     S  semáforo", REG, 21, SUAVE)
texto(x + 1.2 * cm, y - 8.7 * cm, ">  mão única     #  intransponível", REG, 21, SUAVE)
texto(x + 1.2 * cm, y - 9.7 * cm, "Espera esperada no semáforo:   E[espera] = r² / 2c", BOLD, 24, VERMELHO)
texto(x + 1.2 * cm, y - 10.7 * cm, "entra no peso da aresta que CHEGA ao cruzamento.", REG, 21, SUAVE)
y -= A_MAT
FIM_C2 = y

# ================================================================== COLUNA 3
x, y = COLS[2], Y_COL
y = titulo_secao(x, y, "Resultados e demonstração", COL_L, VERDE)
y = paragrafo(x, y, f"Medido na malha real: {MEDIDAS['nos']} cruzamentos de São Paulo. Em todos os "
                    "casos a rota devolvida é a mesma — o ganho é de busca, nunca de qualidade.",
              COL_L, REG, 24, SUAVE)
y -= 1.4 * cm

TILES = [("14,3×", "menos nós na rota\nde Dijkstra para A* com ALT", VERDE),
         ("10,7×", "menos nós no pareamento\nde k buscas para 1 reversa", VERMELHO),
         ("154,8×", "menos comparações\nda varredura linear à quadtree", LATAO),
         ("0", "rotas subótimas\nem toda a validação", ACO)]
tw, th = (COL_L - 1.0 * cm) / 2, 5.8 * cm
for i, (num, nota, cor) in enumerate(TILES):
    tx = x + (i % 2) * (tw + 1.0 * cm)
    ty = y - (i // 2) * (th + 1.0 * cm)
    caixa(tx, ty, tw, th, CARTAO, cor, espessura=3)
    texto(tx + tw / 2, ty - 2.55 * cm, num, BLACK, 56, cor, "centro")
    for k, linha in enumerate(nota.split("\n")):
        texto(tx + tw / 2, ty - 3.95 * cm - k * 1.1 * cm, linha, REG, 21, SUAVE, "centro")
y -= 2 * th + 1.0 * cm + 2.2 * cm

texto(x, y, "NÓS EXPANDIDOS EM 25 ROTAS ORIGEM–DESTINO", BLACK, 25, TINTA)
y -= 1.6 * cm
A_GRAF = 11.1 * cm
caixa(x, y, COL_L, A_GRAF, CARTAO, BORDA, espessura=2)
BARRAS = [("Dijkstra", MEDIDAS["dijkstra_nos"], ACO, ""),
          ("A* haversine", MEDIDAS["haversine_nos"], LATAO, f"{MEDIDAS['haversine_ms']} ms/rota"),
          ("A* com ALT", MEDIDAS["alt_nos"], VERDE, f"{MEDIDAS['alt_ms']} ms/rota")]
maior = max(v for _, v, _, _ in BARRAS)
bx, bw = x + 1.2 * cm, COL_L - 2.4 * cm
for i, (nome, valor, cor, nota) in enumerate(BARRAS):
    by = y - 1.8 * cm - i * 2.9 * cm
    texto(bx, by, nome, BOLD, 23, TINTA)
    texto(bx + bw, by, f"{valor:,}".replace(",", ".") + (f"   ·   {nota}" if nota else ""),
          SEMI, 22, cor, "dir")
    c.setFillColorRGB(*TRILHO)
    c.roundRect(bx, by - 1.7 * cm, bw, 1.1 * cm, 0.18 * cm, stroke=0, fill=1)
    c.setFillColorRGB(*cor)
    c.roundRect(bx, by - 1.7 * cm, bw * valor / maior, 1.1 * cm, 0.18 * cm, stroke=0, fill=1)
texto(bx, y - A_GRAF + 0.95 * cm,
      "Mesmo custo ótimo nas três — conferido rota a rota contra o Dijkstra.", REG, 21, SUAVE)
y -= A_GRAF + 2.0 * cm

texto(x, y, "O APLICATIVO FUNCIONANDO", BLACK, 25, TINTA)
y -= 1.5 * cm
lw = 8.1 * cm
base, fim = y, y
for i, (arq, legenda) in enumerate([("algoritmo.png", "A* × Dijkstra na rota"),
                                    ("alocada.png", "motorista alocado"),
                                    ("motorista-corrida.png", "lado do motorista")]):
    ix = x + 0.25 * cm + i * (lw + 0.6 * cm)
    fim = imagem(arq, ix, base, lw)
    texto(ix + lw / 2, fim - 1.1 * cm, legenda, REG, 21, SUAVE, "centro")
y = fim - 3.0 * cm

texto(x, y, "INDICADORES DE ENTREGA", BLACK, 25, TINTA)
y -= 1.5 * cm
INDS = [("Semáforos reais no peso das arestas", f"{MEDIDAS['semaforos']} · 67% das rotas mudam de traçado"),
        ("Pré-processamento do ALT", "16 marcos · 10,3 s · artefato de 29,8 MB"),
        ("Testes automatizados", f"{MEDIDAS['testes']} verdes + {MEDIDAS['e2e']} no navegador"),
        ("Estratégia de validação", "oráculo: Dijkstra confere o A*, varredura confere a quadtree")]
A_IND = len(INDS) * 2.35 * cm + 0.5 * cm
caixa(x, y + 0.45 * cm, COL_L, A_IND, CARTAO, BORDA, espessura=2)
for i, (chave, valor) in enumerate(INDS):
    iy = y - i * 2.35 * cm
    c.setFillColorRGB(*VERDE)
    c.circle(x + 1.05 * cm, iy - 0.22 * cm, 0.21 * cm, stroke=0, fill=1)
    texto(x + 1.7 * cm, iy - 0.5 * cm, chave, SEMI, 22, TINTA)
    texto(x + 1.7 * cm, iy - 1.65 * cm, valor, REG, 21, SUAVE)
y = y + 0.45 * cm - A_IND
FIM_C3 = y

# ====================================================================== rodapé
c.setFillColorRGB(0.925, 0.925, 0.906)
c.rect(MARGEM, RODAPE_BASE, UTIL, RODAPE_TOPO - RODAPE_BASE, stroke=0, fill=1)
c.setFillColorRGB(*VERDE)
c.rect(MARGEM, RODAPE_TOPO - 0.42 * cm, UTIL, 0.42 * cm, stroke=0, fill=1)

fx, fy = MARGEM + 2.0 * cm, RODAPE_TOPO - 1.4 * cm
L_CONC, L_REF, L_QR = 36 * cm, 26 * cm, 11.2 * cm

texto(fx, fy - 1.3 * cm, "CONSIDERAÇÕES FINAIS", BLACK, 36, TINTA)
yy = paragrafo(fx, fy - 3.6 * cm,
               "O ganho veio de trocar o algoritmo, não de comprar máquina: as mesmas rotas, com "
               "uma fração da busca. O que sustenta a troca é a demonstração — admissibilidade e "
               "consistência da heurística, dualidade do grafo reverso, aciclicidade do fluxo — e "
               "não a medição isolada. O protótipo roda ponta a ponta sobre ruas reais.",
               L_CONC, REG, 24, TINTA)
yy -= 1.5 * cm
texto(fx, yy, "TRABALHOS FUTUROS", BLACK, 24, ACO)
yy -= 1.4 * cm
for item in ["Semáforos dependentes do tempo (onda verde), provando antes a propriedade FIFO.",
             "Algoritmo húngaro para despacho em lote, com vários pedidos simultâneos.",
             "Publicação: front-end no Vercel, back-end no Railway com a malha em memória."]:
    c.setFillColorRGB(*LATAO)
    c.circle(fx + 0.28 * cm, yy + 0.24 * cm, 0.21 * cm, stroke=0, fill=1)
    yy = paragrafo(fx + 0.95 * cm, yy, item, L_CONC - 0.95 * cm, REG, 23, SUAVE)
    yy -= 1.2 * cm

yy -= 0.9 * cm
c.setStrokeColorRGB(*BORDA)
c.setLineWidth(2)
c.line(fx, yy + 0.4 * cm, fx + L_CONC, yy + 0.4 * cm)
paragrafo(fx, yy - 1.0 * cm,
          "Pilha: Python 3.11 · FastAPI · SQLAlchemy · React + TypeScript · Leaflet · WebSocket. "
          "Os algoritmos são de implementação própria — nenhuma biblioteca de grafos.",
          L_CONC, REG, 22, SUAVE)

rx = fx + L_CONC + 2.0 * cm
texto(rx, fy - 1.3 * cm, "REFERÊNCIAS", BLACK, 36, TINTA)
yy = fy - 3.5 * cm
for ref in [
    "CORMEN, T. H. et al. Algoritmos: teoria e prática. 4. ed. Rio de Janeiro: LTC, 2024.",
    "HART, P. E.; NILSSON, N. J.; RAPHAEL, B. A formal basis for the heuristic determination of "
    "minimum cost paths. IEEE Transactions on Systems Science and Cybernetics, v. 4, n. 2, "
    "p. 100-107, 1968.",
    "GOLDBERG, A. V.; HARRELSON, C. Computing the shortest path: A* search meets graph theory. "
    "In: SODA, 16., 2005, Vancouver. Proceedings. Philadelphia: SIAM, 2005. p. 156-165.",
]:
    yy = paragrafo(rx, yy, ref, L_REF, REG, 22, SUAVE, 1.3)
    yy -= 1.15 * cm
texto(rx, yy - 0.2 * cm, "Malha: OpenStreetMap contributors (ODbL),", REG, 21, SUAVE)
texto(rx, yy - 1.3 * cm, "extraída via Overpass API.", REG, 21, SUAVE)

qx = LARGURA - MARGEM - 2.0 * cm - L_QR
qy = RODAPE_BASE + 5.2 * cm
try:
    import qrcode

    qr = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(REPO)
    qr.make(fit=True)
    matriz = qr.get_matrix()
    c.setFillColorRGB(1, 1, 1)
    c.rect(qx - 0.55 * cm, qy - 0.55 * cm, L_QR + 1.1 * cm, L_QR + 1.1 * cm, stroke=0, fill=1)
    passo = L_QR / len(matriz)
    c.setFillColorRGB(*ESCURO)
    for i, linha in enumerate(matriz):
        for j, preto in enumerate(linha):
            if preto:
                c.rect(qx + j * passo, qy + L_QR - (i + 1) * passo, passo * 1.02, passo * 1.02,
                       stroke=0, fill=1)
except ImportError:
    print("aviso: módulo qrcode ausente — QR não desenhado (pip install qrcode).")

texto(qx + L_QR / 2, qy - 2.0 * cm, "Repositório, documentação e protótipo", SEMI, 23, TINTA, "centro")
texto(qx + L_QR / 2, qy - 3.2 * cm, "github.com/Cm-Kauan/Prototipo-TrueCompass", REG, 21, SUAVE, "centro")

c.showPage()
c.save()

if SEM_GLIFO:
    print("ATENÇÃO: a fonte não tem estes caracteres, que sairiam em branco: "
          + " ".join(sorted(SEM_GLIFO)))
print(f"banner: {SAIDA}  ({os.path.getsize(SAIDA) / 1e6:.1f} MB · 90 × 120 cm)")
for nome, fim in (("coluna 1", FIM_C1), ("coluna 2", FIM_C2), ("coluna 3", FIM_C3)):
    folga = (fim - RODAPE_TOPO) / cm
    print(f"  {nome}: termina em {fim / cm:5.1f} cm  ·  folga até o rodapé: {folga:5.1f} cm"
          f"{'   <<< ESTOUROU' if folga < 0 else ''}")

if "--previa" in sys.argv:
    destino = os.path.join(AQUI, "previa_banner")
    os.system(f'pdftoppm -png -r 50 -singlefile "{SAIDA}" "{destino}"')
    print(f"prévia: {destino}.png")
