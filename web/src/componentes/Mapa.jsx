import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

/**
 * Mapa Leaflet.
 *
 * Duas decisões que evitam armadilhas conhecidas:
 *
 * 1. MARCADORES COMO CÍRCULOS, não ícones. Os ícones padrão do Leaflet quebram
 *    sob bundler (Vite/Webpack) porque as imagens são resolvidas por caminho
 *    relativo ao CSS. `circleMarker` é desenhado em SVG e não depende de asset.
 *
 * 2. A MALHA INTEIRA EM DUAS CAMADAS, não uma por rua. `L.polyline` aceita
 *    array de arrays e desenha vários segmentos como UMA camada. Com milhares
 *    de trechos, criar uma camada por rua trava o navegador.
 */
export function Mapa({
  centro, trechos = [], semaforos = [], origem, destino, motorista,
  rota = [], rotaMotorista = [], aoClicar, dica, buscando = false,
}) {
  const divRef = useRef(null)
  const mapaRef = useRef(null)
  const camadasRef = useRef({})
  const aoClicarRef = useRef(aoClicar)

  // Mantém o callback atualizado sem recriar o mapa a cada render.
  useEffect(() => { aoClicarRef.current = aoClicar }, [aoClicar])

  function cor(nome, alternativa) {
    const valor = getComputedStyle(document.documentElement)
      .getPropertyValue(nome).trim()
    return valor || alternativa
  }

  // ---- criação do mapa (uma vez)
  useEffect(() => {
    if (mapaRef.current || !divRef.current) return

    const mapa = L.map(divRef.current, {
      center: centro ? [centro.lat, centro.lon] : [-23.5325, -46.6225],
      zoom: 15, zoomControl: true, attributionControl: true,
    })

    // Tiles do OpenStreetMap: pano de fundo OPCIONAL. Sem acesso à internet o
    // mapa continua utilizável, porque a malha vem da nossa própria API.
    // Após algumas falhas seguidas removemos a camada, em vez de deixar o
    // navegador repetindo requisições que não vão completar.
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, opacity: 0.35,
      attribution: '&copy; OpenStreetMap',
    })
    let falhasDeTile = 0
    tiles.on('tileerror', () => {
      falhasDeTile += 1
      if (falhasDeTile === 8 && mapa.hasLayer(tiles)) mapa.removeLayer(tiles)
    })
    tiles.addTo(mapa)

    camadasRef.current = {
      maoDupla: L.polyline([], { color: cor('--mapa-rua', '#2A3036'), weight: 2 }).addTo(mapa),
      maoUnica: L.polyline([], {
        color: cor('--mapa-rua', '#2A3036'), weight: 2, dashArray: '5,4',
      }).addTo(mapa),
      rotaMotorista: L.polyline([], {
        color: cor('--vermelho', '#D64550'), weight: 3, dashArray: '7,5', opacity: 0.9,
      }).addTo(mapa),
      rota: L.polyline([], {
        color: cor('--verde', '#5C9A6B'), weight: 5, opacity: 0.95,
      }).addTo(mapa),
      semaforos: L.layerGroup().addTo(mapa),
      marcadores: L.layerGroup().addTo(mapa),
    }

    mapa.on('click', (evento) => {
      aoClicarRef.current?.(evento.latlng.lat, evento.latlng.lng)
    })

    mapaRef.current = mapa
    // O contêiner costuma ser medido antes do layout final; sem isto o mapa
    // renderiza cortado.
    setTimeout(() => mapa.invalidateSize(), 60)

    return () => { mapa.remove(); mapaRef.current = null }
  }, [])

  // ---- centro
  useEffect(() => {
    if (mapaRef.current && centro) mapaRef.current.setView([centro.lat, centro.lon], 15)
  }, [centro?.lat, centro?.lon])

  // ---- malha viária
  useEffect(() => {
    const camadas = camadasRef.current
    if (!camadas.maoDupla) return
    const duplas = [], unicas = []
    for (const [lat1, lon1, lat2, lon2, maoUnica] of trechos) {
      (maoUnica ? unicas : duplas).push([[lat1, lon1], [lat2, lon2]])
    }
    camadas.maoDupla.setLatLngs(duplas)
    camadas.maoUnica.setLatLngs(unicas)
  }, [trechos])

  // ---- semaforos
  useEffect(() => {
    const grupo = camadasRef.current.semaforos
    if (!grupo) return
    grupo.clearLayers()
    for (const sinal of semaforos) {
      // O raio cresce com o atraso: sinal que atrasa mais aparece maior.
      // sqrt para que a AREA, e nao o raio, acompanhe o atraso -- e a area
      // que o olho compara.
      const raio = 2.5 + Math.sqrt(sinal.atraso_medio) * 0.9
      L.circleMarker([sinal.lat, sinal.lon], {
        radius: raio, color: cor('--vermelho', '#D64550'), weight: 1.5,
        fillColor: cor('--vermelho', '#D64550'), fillOpacity: 0.35,
      }).bindTooltip(
        `Semáforo · vermelho ${sinal.vermelho}s em ciclo de ${sinal.ciclo}s` +
        `<br/>espera média ${sinal.atraso_medio}s`,
        { direction: 'top', offset: [0, -6] },
      ).addTo(grupo)
    }
  }, [semaforos])

  // ---- rota, com animação de traçado
  useEffect(() => {
    const camada = camadasRef.current.rota
    if (!camada) return
    camada.setLatLngs(rota)
    if (rota.length > 1 && mapaRef.current) {
      mapaRef.current.fitBounds(L.latLngBounds(rota).pad(0.18))
      // A rota se desenha progressivamente. O <path> só existe depois que o
      // Leaflet renderiza, daí o reflow forçado antes de religar a classe --
      // sem ele o navegador não reinicia a animação numa rota nova.
      const elemento = camada.getElement?.()
      if (elemento) {
        elemento.classList.remove('rota-desenhando')
        void elemento.getBoundingClientRect()
        elemento.classList.add('rota-desenhando')
      }
    }
  }, [rota])

  useEffect(() => {
    camadasRef.current.rotaMotorista?.setLatLngs(rotaMotorista)
  }, [rotaMotorista])

  // ---- marcador do motorista, interpolado
  //
  // O GPS chega em saltos de alguns segundos. Mover o marcador de uma vez
  // produziria teleporte; interpolamos quadro a quadro entre a posição antiga
  // e a nova, e o carro desliza pela rua.
  const motoristaAnimadoRef = useRef(null)
  const quadroRef = useRef(null)
  const [motoristaSuave, definirMotoristaSuave] = useState(null)

  useEffect(() => {
    if (!motorista) {
      motoristaAnimadoRef.current = null
      definirMotoristaSuave(null)
      return
    }
    const de = motoristaAnimadoRef.current
    if (!de) {
      motoristaAnimadoRef.current = motorista
      definirMotoristaSuave(motorista)
      return
    }
    const inicio = performance.now()
    const duracao = 650
    cancelAnimationFrame(quadroRef.current)

    const passo = (agora) => {
      const t = Math.min(1, (agora - inicio) / duracao)
      const suave = t * (2 - t)                       // easing quadrático
      const atual = {
        lat: de.lat + (motorista.lat - de.lat) * suave,
        lon: de.lon + (motorista.lon - de.lon) * suave,
      }
      definirMotoristaSuave(atual)
      if (t < 1) quadroRef.current = requestAnimationFrame(passo)
      else motoristaAnimadoRef.current = motorista
    }
    quadroRef.current = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadroRef.current)
  }, [motorista?.lat, motorista?.lon])

  // ---- marcadores
  useEffect(() => {
    const grupo = camadasRef.current.marcadores
    if (!grupo) return
    grupo.clearLayers()

    const pino = (ponto, corPreenchimento, rotulo, raio = 8) => {
      if (!ponto) return
      L.circleMarker([ponto.lat, ponto.lon], {
        radius: raio, color: '#fff', weight: 2,
        fillColor: corPreenchimento, fillOpacity: 1,
      }).bindTooltip(rotulo, { direction: 'top', offset: [0, -8] }).addTo(grupo)
    }

    pino(origem, cor('--verde', '#5C9A6B'), 'Origem')
    pino(destino, cor('--vermelho', '#D64550'), 'Destino')
    if (motoristaSuave) {
      L.circleMarker([motoristaSuave.lat, motoristaSuave.lon], {
        radius: 7, color: cor('--verde-sobre', '#0C1710'), weight: 2,
        fillColor: '#F3F1E7', fillOpacity: 1,
      }).bindTooltip('Motorista', { direction: 'top', offset: [0, -8] }).addTo(grupo)
    }
  }, [origem, destino, motoristaSuave])

  return (
    <div className="area-mapa">
      {dica && <div className="dica-mapa">{dica}</div>}
      {buscando && (
        <>
          <div className="pulso-busca" />
          <div className="pulso-busca atraso" />
        </>
      )}
      <div ref={divRef} style={{ width: '100%', height: '100%' }} />
      <div className="legenda">
        <div className="legenda-item">
          <span className="legenda-amostra" style={{ background: 'var(--mapa-rua)' }} />
          rua de mão dupla
        </div>
        <div className="legenda-item">
          <span className="legenda-amostra" style={{
            background: 'repeating-linear-gradient(90deg,var(--mapa-rua) 0 5px,transparent 5px 9px)',
          }} />
          mão única
        </div>
        <div className="legenda-item">
          <span className="legenda-amostra" style={{
            background: 'var(--vermelho)', height: 9, width: 9, borderRadius: '50%',
            opacity: .5,
          }} />
          semáforo (área ∝ espera)
        </div>
        <div className="legenda-item">
          <span className="legenda-amostra" style={{ background: 'var(--verde)', height: 4 }} />
          rota da corrida (A*)
        </div>
        <div className="legenda-item">
          <span className="legenda-amostra" style={{
            background: 'repeating-linear-gradient(90deg,var(--vermelho) 0 7px,transparent 7px 12px)',
          }} />
          motorista até você
        </div>
      </div>
    </div>
  )
}
