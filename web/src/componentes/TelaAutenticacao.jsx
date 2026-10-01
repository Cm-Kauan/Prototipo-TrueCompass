import { useState } from 'react'
import { api } from '../api'
import { Bussola } from './Bussola'

export function TelaAutenticacao({ aoEntrar }) {
  const [modo, definirModo] = useState('entrar')
  const [tipo, definirTipo] = useState('passageiro')
  const [nome, definirNome] = useState('')
  const [email, definirEmail] = useState('')
  const [senha, definirSenha] = useState('')
  const [placa, definirPlaca] = useState('')
  const [erro, definirErro] = useState(null)
  const [enviando, definirEnviando] = useState(false)

  const registrando = modo === 'registrar'

  async function enviar(evento) {
    evento.preventDefault()
    definirErro(null)
    definirEnviando(true)
    try {
      const sessao = registrando
        ? await api.registrar({
            nome, email, senha, tipo,
            placa: tipo === 'motorista' ? placa : undefined,
          })
        : await api.entrar(email, senha)
      aoEntrar(sessao)
    } catch (falha) {
      definirErro(falha.message)
    } finally {
      definirEnviando(false)
    }
  }

  return (
    <div className="tela-entrada">
      <form className="caixa-entrada cartao" onSubmit={enviar}>
        <div className="cabecalho-entrada">
          <Bussola tamanho={86} />
          <div className="marca" style={{ marginTop: 10 }}>
            <span><b>True</b><i>Compass</i></span>
          </div>
          <div className="subtitulo">Sua corrida, no caminho certo.</div>
        </div>

        {registrando && (
          <>
            <div className="campo">
              <label htmlFor="tipo">Entrar como</label>
              <select id="tipo" value={tipo} onChange={(e) => definirTipo(e.target.value)}>
                <option value="passageiro">Passageiro</option>
                <option value="motorista">Motorista</option>
              </select>
            </div>
            <div className="campo">
              <label htmlFor="nome">Nome</label>
              <input id="nome" value={nome} required minLength={2}
                     onChange={(e) => definirNome(e.target.value)} />
            </div>
          </>
        )}

        <div className="campo">
          <label htmlFor="email">E-mail</label>
          <input id="email" type="email" value={email} required
                 autoComplete="username"
                 onChange={(e) => definirEmail(e.target.value)} />
        </div>

        <div className="campo">
          <label htmlFor="senha">Senha</label>
          <input id="senha" type="password" value={senha} required minLength={8}
                 autoComplete={registrando ? 'new-password' : 'current-password'}
                 onChange={(e) => definirSenha(e.target.value)} />
        </div>

        {registrando && tipo === 'motorista' && (
          <div className="campo">
            <label htmlFor="placa">Placa</label>
            <input id="placa" value={placa} required maxLength={10}
                   onChange={(e) => definirPlaca(e.target.value.toUpperCase())} />
          </div>
        )}

        {erro && <div className="aviso erro" role="alert">{erro}</div>}

        <button className="botao" type="submit" disabled={enviando}>
          {enviando ? 'Aguarde…' : registrando ? 'Criar conta' : 'Entrar'}
        </button>

        <div className="rodape-entrada">
          {registrando ? 'Já tem conta? ' : 'Ainda não tem conta? '}
          <button type="button" onClick={() => { definirModo(registrando ? 'entrar' : 'registrar'); definirErro(null) }}>
            {registrando ? 'Entrar' : 'Criar agora'}
          </button>
        </div>

        {registrando && (
          <div className="tenue" style={{ marginTop: 10 }}>
            A senha precisa de no mínimo 8 caracteres. Ela é guardada com bcrypt —
            o servidor nunca armazena a senha em texto.
          </div>
        )}
      </form>
    </div>
  )
}
