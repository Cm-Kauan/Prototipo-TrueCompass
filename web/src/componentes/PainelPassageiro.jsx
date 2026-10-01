import { useEffect, useState } from 'react'
import { api } from '../api'
import { usarCorridaAoVivo } from '../ganchos/usarCorridaAoVivo'
import { CartaoBussola } from './Bussola'
import { LinhaDeEstados } from './LinhaDeEstados'
import { Mapa } from './Mapa'

const paraPontos = (rota) => (rota?.pontos ?? []).map(([lat, lon]) => [lat, lon])
const minutos = (s) => (s == null ? '—' : `${(s / 60).toFixed(1)}`)
const reais = (v) => (v == null ? '—' : v.toFixed(2).replace('.', ','))

export function PainelPassageiro({ sessao, malha }) {
  const [origem, definirOrigem] = useState(null)
  const [destino, definirDestino] = useState(null)
  const [corrida, definirCorrida] = useState(null)
  const [rota, definirRota] = useState([])
  const [rotaMotorista, definirRotaMotorista] = useState([])
  const [erro, definirErro] = useState(null)
  const [ocupado, definirOcupado] = useState(false)

  const aoVivo = usarCorridaAoVivo(corrida?.id, sessao.token)
  const estado = aoVivo.estado?.estado ?? corrida?.estado ?? null
  const encerrada = estado === 'paga' || estado === 'cancelada'

  // O backend é a fonte da verdade do estado; o WebSocket apenas empurra a
  // mudança. Ao receber um evento, recarregamos a corrida para ter ETA e custo.
  useEffect(() => {
    if (!aoVivo.estado || !corrida) return
    api.consultarCorrida(sessao.token, corrida.id)
      .then(definirCorrida)
      .catch(() => {})
  }, [aoVivo.estado?.estado])

  // Traçado do motorista até você: recalculado a cada ping de GPS dele.
  useEffect(() => {
    if (!corrida || !['alocacao', 'rota'].includes(estado)) {
      definirRotaMotorista([])
      return
    }
    api.rotaDoMotorista(sessao.token, corrida.id)
      .then((r) => definirRotaMotorista(paraPontos(r)))
      .catch(() => definirRotaMotorista([]))
  }, [corrida?.id, estado, aoVivo.posicaoMotorista?.lat, aoVivo.posicaoMotorista?.lon])

  function aoClicarNoMapa(lat, lon) {
    if (corrida && !encerrada) return          // corrida em andamento: mapa travado
    if (!origem || (origem && destino)) {
      definirOrigem({ lat, lon })
      definirDestino(null)
      definirCorrida(null)
      definirRota([])
    } else {
      definirDestino({ lat, lon })
    }
  }

  async function agir(acao, chamada) {
    definirErro(null)
    definirOcupado(true)
    try {
      definirCorrida(await chamada())
    } catch (falha) {
      definirErro(falha.message)
    } finally {
      definirOcupado(false)
    }
  }

  async function pedir() {
    definirErro(null)
    definirOcupado(true)
    try {
      const nova = await api.pedirCorrida(sessao.token, {
        origem_lat: origem.lat, origem_lon: origem.lon,
        destino_lat: destino.lat, destino_lon: destino.lon,
      })
      definirCorrida(nova)
      definirRota(paraPontos(await api.rotaDaCorrida(sessao.token, nova.id)))
    } catch (falha) {
      definirErro(falha.message)
    } finally {
      definirOcupado(false)
    }
  }

  function novaCorrida() {
    definirCorrida(null); definirOrigem(null); definirDestino(null)
    definirRota([]); definirRotaMotorista([]); definirErro(null)
  }

  const dica = corrida && !encerrada ? null
    : !origem ? 'Clique no mapa para marcar a ORIGEM'
    : !destino ? 'Agora clique no DESTINO'
    : 'Pronto — peça a corrida no painel'

  const procurando = ocupado && !corrida

  return (
    <div className="corpo">
      <aside className="lateral">
        <CartaoBussola origem={origem} destino={destino} />

        <div className="cartao entra entra-2">
          <div className="cartao-titulo">Sua corrida</div>
          {!corrida || encerrada ? (
            <>
              <div className="tenue" style={{ marginBottom: 11 }}>
                Marque origem e destino clicando no mapa. As ruas desenhadas são a
                malha que o algoritmo realmente percorre.
              </div>
              <div className="metricas" style={{ marginBottom: 11 }}>
                <div className="metrica">
                  <div className="metrica-rotulo">Origem</div>
                  <div className="metrica-valor" style={{ fontSize: 13 }}>
                    {origem ? `${origem.lat.toFixed(4)}, ${origem.lon.toFixed(4)}` : '—'}
                  </div>
                </div>
                <div className="metrica">
                  <div className="metrica-rotulo">Destino</div>
                  <div className="metrica-valor" style={{ fontSize: 13 }}>
                    {destino ? `${destino.lat.toFixed(4)}, ${destino.lon.toFixed(4)}` : '—'}
                  </div>
                </div>
              </div>
              <button className={`botao ${procurando ? 'aguardando' : ''}`}
                      onClick={pedir}
                      disabled={!origem || !destino || ocupado}>
                {ocupado ? 'Procurando motorista…' : 'Pedir corrida'}
              </button>
              {encerrada && (
                <button className="botao secundario" style={{ marginTop: 8 }}
                        onClick={novaCorrida}>
                  Começar outra corrida
                </button>
              )}
            </>
          ) : (
            <>
              <div className="metricas">
                <div className="metrica">
                  <div className="metrica-rotulo">Motorista chega em</div>
                  <div className="metrica-valor">
                    {minutos(corrida.eta_segundos)} <small>min</small>
                  </div>
                </div>
                <div className="metrica">
                  <div className="metrica-rotulo">Valor estimado</div>
                  <div className="metrica-valor">
                    <small>R$ </small>{reais(corrida.custo_estimado)}
                  </div>
                </div>
              </div>
              <div className="linha-botoes" style={{ marginTop: 11 }}>
                {estado === 'rota' && (
                  <button className="botao pequeno"
                          onClick={() => agir('iniciar', () => api.iniciar(sessao.token, corrida.id))}
                          disabled={ocupado}>Embarquei</button>
                )}
                {estado === 'em_curso' && (
                  <button className="botao pequeno"
                          onClick={() => agir('finalizar', () => api.finalizar(sessao.token, corrida.id))}
                          disabled={ocupado}>Cheguei ao destino</button>
                )}
                {estado === 'concluida' && (
                  <button className="botao pequeno"
                          onClick={() => agir('pagar', () => api.pagar(sessao.token, corrida.id))}
                          disabled={ocupado}>
                    Pagar R$ {reais(corrida.custo_estimado)}
                  </button>
                )}
                {['alocacao', 'rota'].includes(estado) && (
                  <button className="botao pequeno perigo"
                          onClick={() => agir('cancelar', () => api.cancelar(sessao.token, corrida.id))}
                          disabled={ocupado}>Cancelar</button>
                )}
              </div>
            </>
          )}
          {erro && <div className="aviso erro" style={{ marginTop: 10 }} role="alert">{erro}</div>}
        </div>

        {corrida && <LinhaDeEstados estadoAtual={estado} />}

        {corrida && (
          <div className="cartao entra entra-3">
            <div className="cartao-titulo">
              Tempo real{' '}
              <span className={`selo ${aoVivo.conectado ? 'ativo' : ''}`}>
                <span className={`ponto ${aoVivo.conectado ? 'pulsando' : ''}`} />
                {aoVivo.conectado ? 'conectado' : 'offline'}
              </span>
            </div>
            <div className="mono registro-eventos"
                 style={{ color: 'var(--text-dim)', lineHeight: 1.7 }}>
              {aoVivo.eventos.length === 0 && <div>aguardando eventos…</div>}
              {aoVivo.eventos.slice(-6).reverse().map((e, i) => (
                <div key={i}>
                  {e.evento === 'estado'
                    ? `→ ${e.estado}`
                    : `· gps ${e.lat.toFixed(4)}, ${e.lon.toFixed(4)}`}
                </div>
              ))}
            </div>
          </div>
        )}

        {rota.length > 1 && (
          <div className="cartao entra entra-4">
            <div className="cartao-titulo">Rota calculada</div>
            <div className="tenue">
              {rota.length} cruzamentos no trajeto, escolhidos por <strong>A*</strong> com
              heurística haversine. O custo é idêntico ao do Dijkstra — a mesma
              rota ótima, com menos busca.
            </div>
          </div>
        )}
      </aside>

      <Mapa centro={malha?.centro} trechos={malha?.trechos ?? []}
            semaforos={malha?.semaforos ?? []}
            origem={origem} destino={destino}
            motorista={aoVivo.posicaoMotorista}
            rota={rota} rotaMotorista={rotaMotorista}
            aoClicar={aoClicarNoMapa} dica={dica} buscando={procurando} />
    </div>
  )
}
