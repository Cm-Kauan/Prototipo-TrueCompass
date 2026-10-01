import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { usarCorridaAoVivo } from '../ganchos/usarCorridaAoVivo'
import { CartaoBussola } from './Bussola'
import { LinhaDeEstados } from './LinhaDeEstados'
import { Mapa } from './Mapa'

const paraPontos = (rota) => (rota?.pontos ?? []).map(([lat, lon]) => [lat, lon])

export function PainelMotorista({ sessao, malha }) {
  const [posicao, definirPosicao] = useState(null)
  const [online, definirOnline] = useState(false)
  const [corridaId, definirCorridaId] = useState(null)
  const [corrida, definirCorrida] = useState(null)
  const [trajeto, definirTrajeto] = useState([])
  const [erro, definirErro] = useState(null)
  const [simulando, definirSimulando] = useState(false)
  const cronometroRef = useRef(null)

  const aoVivo = usarCorridaAoVivo(corridaId, sessao.token)
  const estado = aoVivo.estado?.estado ?? corrida?.estado ?? null

  // Ao encerrar, para a simulação para não seguir pingando sem corrida.
  useEffect(() => {
    if (['paga', 'cancelada', 'concluida'].includes(estado)) pararSimulacao()
  }, [estado])

  useEffect(() => () => pararSimulacao(), [])

  /**
   * Batida de GPS periódica enquanto online.
   *
   * Sem isto o motorista só enviava posição ao clicar no mapa, e portanto
   * NUNCA descobria uma corrida atribuída a ele — a resposta de `/posicao` é
   * o que informa `corrida_ativa`. Aplicativos reais de motorista transmitem
   * GPS continuamente; a batida reproduz esse comportamento e ainda mantém o
   * registro em memória do backend atualizado.
   *
   * Pausada durante a simulação, que já envia a própria posição.
   */
  useEffect(() => {
    if (!online || !posicao || simulando) return
    const id = setInterval(() => { enviarPosicao(posicao.lat, posicao.lon) }, 4000)
    return () => clearInterval(id)
  }, [online, posicao?.lat, posicao?.lon, simulando])

  useEffect(() => {
    if (!corridaId) { definirCorrida(null); definirTrajeto([]); return }
    api.consultarCorrida(sessao.token, corridaId).then(definirCorrida).catch(() => {})
    api.rotaDoMotorista(sessao.token, corridaId)
      .then((r) => definirTrajeto(paraPontos(r)))
      .catch(() => definirTrajeto([]))
  }, [corridaId, aoVivo.estado?.estado])

  async function enviarPosicao(lat, lon) {
    definirErro(null)
    try {
      const resposta = await api.enviarPosicao(sessao.token, lat, lon)
      definirPosicao({ lat, lon })
      // O backend informa se este motorista está numa corrida ativa — é assim
      // que o painel descobre a corrida, sem endpoint extra.
      if (resposta.corrida_ativa !== corridaId) definirCorridaId(resposta.corrida_ativa)
      return resposta
    } catch (falha) {
      definirErro(falha.message)
      return null
    }
  }

  async function alternarDisponibilidade() {
    if (!posicao) {
      definirErro('Marque sua posição no mapa antes de ficar online.')
      return
    }
    try {
      await api.definirDisponibilidade(sessao.token, !online)
      definirOnline(!online)
      definirErro(null)
    } catch (falha) {
      definirErro(falha.message)
    }
  }

  /**
   * Simula o deslocamento: percorre o trajeto real, cruzamento por cruzamento,
   * enviando um ping de GPS a cada passo. O passageiro vê o carro andar pelas
   * ruas, via WebSocket — não é interpolação em linha reta.
   */
  function iniciarSimulacao() {
    if (trajeto.length < 2 || simulando) return
    definirSimulando(true)
    let i = 0
    cronometroRef.current = setInterval(async () => {
      if (i >= trajeto.length) { pararSimulacao(); return }
      const [lat, lon] = trajeto[i]
      i += 1
      await enviarPosicao(lat, lon)
    }, 700)
  }

  function pararSimulacao() {
    if (cronometroRef.current) clearInterval(cronometroRef.current)
    cronometroRef.current = null
    definirSimulando(false)
  }

  const dica = !posicao
    ? 'Clique no mapa para marcar onde você está'
    : corridaId ? null : 'Fique online para receber corridas'

  // A bússola do motorista aponta para o passageiro: o primeiro ponto do
  // trajeto é onde ele está, o último é onde o passageiro espera.
  const alvo = trajeto.length > 1
    ? { lat: trajeto[trajeto.length - 1][0], lon: trajeto[trajeto.length - 1][1] }
    : null

  return (
    <div className="corpo">
      <aside className="lateral">
        <CartaoBussola origem={posicao} destino={alvo} rotulo="Rumo ao passageiro" />

        <div className="cartao entra entra-2">
          <div className="cartao-titulo">
            Status{' '}
            <span className={`selo ${online ? 'ativo' : ''}`}>
              <span className={`ponto ${online ? 'pulsando' : ''}`} />
              {online ? 'disponível' : 'offline'}
            </span>
          </div>
          <div className="tenue" style={{ marginBottom: 11 }}>
            Posição:{' '}
            <span className="mono">
              {posicao ? `${posicao.lat.toFixed(4)}, ${posicao.lon.toFixed(4)}` : 'não marcada'}
            </span>
          </div>
          <button className={`botao ${online ? 'secundario' : ''}`}
                  onClick={alternarDisponibilidade}>
            {online ? 'Ficar offline' : 'Ficar online'}
          </button>
          {erro && <div className="aviso erro" style={{ marginTop: 10 }} role="alert">{erro}</div>}
        </div>

        {!corridaId && (
          <div className="aviso neutro">
            {online
              ? 'Você está na fila. Quando um passageiro pedir corrida por perto, o pareamento reverso mede seu tempo real até ele — não a distância em linha reta.'
              : 'Marque sua posição no mapa e fique online.'}
          </div>
        )}

        {corridaId && corrida && (
          <>
            <div className="cartao entra entra-3">
              <div className="cartao-titulo">Corrida #{corrida.id}</div>
              <div className="metricas">
                <div className="metrica">
                  <div className="metrica-rotulo">Seu tempo até o passageiro</div>
                  <div className="metrica-valor">
                    {corrida.eta_segundos != null
                      ? (corrida.eta_segundos / 60).toFixed(1) : '—'} <small>min</small>
                  </div>
                </div>
                <div className="metrica">
                  <div className="metrica-rotulo">Valor da corrida</div>
                  <div className="metrica-valor">
                    <small>R$ </small>
                    {corrida.custo_estimado != null
                      ? corrida.custo_estimado.toFixed(2).replace('.', ',') : '—'}
                  </div>
                </div>
              </div>
              <div className="linha-botoes" style={{ marginTop: 11 }}>
                <button className="botao pequeno"
                        onClick={simulando ? pararSimulacao : iniciarSimulacao}
                        disabled={trajeto.length < 2}>
                  {simulando ? 'Parar deslocamento' : 'Simular deslocamento'}
                </button>
              </div>
              <div className="tenue" style={{ marginTop: 9 }}>
                {trajeto.length > 1
                  ? `Trajeto com ${trajeto.length} cruzamentos até o passageiro. A simulação percorre as ruas de verdade, enviando GPS a cada passo.`
                  : 'Trajeto indisponível.'}
              </div>
            </div>
            <LinhaDeEstados estadoAtual={estado} />
          </>
        )}
      </aside>

      <Mapa centro={malha?.centro} trechos={malha?.trechos ?? []}
            semaforos={malha?.semaforos ?? []}
            origem={corrida ? undefined : undefined}
            motorista={posicao}
            rotaMotorista={trajeto}
            aoClicar={(lat, lon) => enviarPosicao(lat, lon)}
            dica={dica} />
    </div>
  )
}
