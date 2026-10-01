/**
 * Visualiza o DAG do ciclo da corrida.
 *
 * A ordem exibida é exatamente a ordenação topológica que o backend valida por
 * Kahn na inicialização. Ver a linha andar é ver o teorema funcionando: nunca
 * se pula etapa, nunca se volta atrás.
 */
const ETAPAS = [
  { chave: 'pedido', nome: 'Pedido registrado', nota: 'pedido' },
  { chave: 'alocacao', nome: 'Motorista alocado', nota: 'busca reversa no grafo' },
  { chave: 'rota', nome: 'Rota calculada', nota: 'A* com heurística haversine' },
  { chave: 'em_curso', nome: 'Corrida em andamento', nota: 'em_curso' },
  { chave: 'concluida', nome: 'Corrida concluída', nota: 'concluida' },
  { chave: 'paga', nome: 'Pagamento liberado', nota: 'só a partir de concluida' },
]

export function LinhaDeEstados({ estadoAtual }) {
  const cancelada = estadoAtual === 'cancelada'
  const indiceAtual = ETAPAS.findIndex((e) => e.chave === estadoAtual)

  return (
    <div className="cartao">
      <div className="cartao-titulo">Fluxo da corrida</div>
      <div className="linha-estados">
        {ETAPAS.map((etapa, i) => {
          const concluida = indiceAtual > i
          const atual = indiceAtual === i
          const classes = ['etapa']
          if (concluida) classes.push('concluida')
          if (atual) classes.push('atual')
          return (
            <div key={etapa.chave} className={classes.join(' ')}>
              <div className="etapa-marca">
                <div className="etapa-bola">{concluida ? '✓' : ''}</div>
                {i < ETAPAS.length - 1 && <div className="etapa-traco" />}
              </div>
              <div className="etapa-texto">
                <div className="etapa-nome">{etapa.nome}</div>
                <div className="etapa-nota">{etapa.nota}</div>
              </div>
            </div>
          )
        })}
        {cancelada && (
          <div className="etapa cancelada">
            <div className="etapa-marca"><div className="etapa-bola">×</div></div>
            <div className="etapa-texto">
              <div className="etapa-nome">Corrida cancelada</div>
              <div className="etapa-nota">estado final do DAG</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
