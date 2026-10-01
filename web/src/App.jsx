import { useEffect, useState } from 'react'
import { api } from './api'
import { Bussola } from './componentes/Bussola'
import { PainelMotorista } from './componentes/PainelMotorista'
import { PainelPassageiro } from './componentes/PainelPassageiro'
import { TelaAutenticacao } from './componentes/TelaAutenticacao'

const CHAVE_SESSAO = 'truecompass.sessao'
const CHAVE_TEMA = 'truecompass.tema'

function lerArmazenado(chave) {
  // Navegação privada e bloqueio de cookies fazem localStorage lançar.
  try { return JSON.parse(localStorage.getItem(chave)) } catch { return null }
}
function gravarArmazenado(chave, valor) {
  try {
    if (valor == null) localStorage.removeItem(chave)
    else localStorage.setItem(chave, JSON.stringify(valor))
  } catch { /* segue sem persistir */ }
}

export default function App() {
  const [sessao, definirSessao] = useState(() => lerArmazenado(CHAVE_SESSAO))
  const [tema, definirTema] = useState(() => lerArmazenado(CHAVE_TEMA) || 'escuro')
  const [malha, definirMalha] = useState(null)
  const [falhaBackend, definirFalhaBackend] = useState(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-tema', tema)
    gravarArmazenado(CHAVE_TEMA, tema)
  }, [tema])

  useEffect(() => { gravarArmazenado(CHAVE_SESSAO, sessao) }, [sessao])

  // A malha é carregada UMA vez e compartilhada entre os painéis: são milhares
  // de trechos, e recarregar a cada troca de tela seria desperdício.
  useEffect(() => {
    let vivo = true
    ;(async () => {
      try {
        const info = await api.infoDaMalha()
        if (!info.caixa) return
        const [{ trechos }, { semaforos }] = await Promise.all([
          api.trechos(info.caixa),
          api.semaforos(),
        ])
        if (vivo) definirMalha({ ...info, trechos, semaforos })
      } catch (falha) {
        if (vivo) definirFalhaBackend(falha.message)
      }
    })()
    return () => { vivo = false }
  }, [])

  function sair() {
    definirSessao(null)
  }

  if (!sessao) {
    return (
      <div className="aplicativo">
        {falhaBackend && (
          <div className="aviso erro" style={{ margin: 16 }} role="alert">
            {falhaBackend} — suba o backend com{' '}
            <span className="mono">uvicorn api.main:app --reload</span>
          </div>
        )}
        <TelaAutenticacao aoEntrar={definirSessao} />
      </div>
    )
  }

  const Painel = sessao.tipo === 'motorista' ? PainelMotorista : PainelPassageiro

  return (
    <div className="aplicativo">
      <header className="barra-topo">
        <div className="marca">
          <Bussola tamanho={26} mostrarLetras={false} />
          <span><b>True</b><i>Compass</i></span>
        </div>
        <span className="selo">{sessao.tipo}</span>
        <div className="espaco" />
        {malha && (
          <span className="tenue mono" title="malha carregada do backend">
            {malha.nos.toLocaleString('pt-BR')} cruzamentos
            {malha.semaforos?.length > 0 && ` · ${malha.semaforos.length} semáforos`}
          </span>
        )}
        <button className="interruptor-tema"
                onClick={() => definirTema(tema === 'escuro' ? 'claro' : 'escuro')}>
          {tema === 'escuro' ? 'claro' : 'escuro'}
        </button>
        <button className="interruptor-tema" onClick={sair}>sair</button>
      </header>

      {falhaBackend && (
        <div className="aviso erro" style={{ margin: 12 }} role="alert">{falhaBackend}</div>
      )}

      <Painel sessao={sessao} malha={malha} />
    </div>
  )
}
