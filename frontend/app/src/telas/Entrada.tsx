import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api'
import { vibrar } from '../lib/util'
import type { Ponto, Sessao, TipoUsuario } from '../tipos'
import { Bussola } from '../ui/Bussola'
import { Aviso } from '../ui/Folha'
import { Icone } from '../ui/Icone'
import { Botao } from '../ui/Movimento'
import { FundoCidade } from './FundoCidade'

function Campo({ id, rotulo, ...props }: { id: string; rotulo: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <motion.div className="campo" layout="position"
                initial={{ opacity: 0, height: 0, y: -8 }} animate={{ opacity: 1, height: 'auto', y: 0 }}
                exit={{ opacity: 0, height: 0, y: -8 }} transition={{ type: 'spring', stiffness: 380, damping: 32 }}>
      <input id={id} placeholder=" " {...props} />
      <label htmlFor={id}>{rotulo}</label>
      <span className="campo-linha" />
    </motion.div>
  )
}

const MARCA = [...'TrueCompass']

export function Entrada({ centro, falhaBackend, aoEntrar }:
  { centro: Ponto | null; falhaBackend: string | null; aoEntrar: (s: Sessao, de: { x: number; y: number }) => void }) {
  const [modo, definirModo] = useState<'entrar' | 'registrar'>('entrar')
  const [tipo, definirTipo] = useState<TipoUsuario>('passageiro')
  const [nome, definirNome] = useState('')
  const [email, definirEmail] = useState('')
  const [senha, definirSenha] = useState('')
  const [placa, definirPlaca] = useState('')
  const [modelo, definirModelo] = useState('')
  const [erro, definirErro] = useState<string | null>(null)
  const [enviando, definirEnviando] = useState(false)
  const botaoRef = useRef<HTMLDivElement>(null)
  // A agulha gira procurando e "acha o norte" quando a tela abre.
  const [rumo, definirRumo] = useState<number | null>(null)
  useEffect(() => {
    const ids = [setTimeout(() => definirRumo(220), 500), setTimeout(() => definirRumo(0), 1300)]
    return () => ids.forEach(clearTimeout)
  }, [])

  const registrando = modo === 'registrar'

  async function enviar(e: FormEvent) {
    e.preventDefault()
    definirErro(null)
    definirEnviando(true)
    try {
      const sessao = registrando
        ? await api.registrar({ nome, email, senha, tipo, ...(tipo === 'motorista' ? { placa, modelo } : {}) })
        : await api.entrar(email, senha)
      vibrar([15, 40, 15])
      const caixa = botaoRef.current?.getBoundingClientRect()
      aoEntrar(sessao, caixa ? { x: caixa.left + caixa.width / 2, y: caixa.top + caixa.height / 2 }
                             : { x: window.innerWidth / 2, y: window.innerHeight / 2 })
    } catch (falha) {
      vibrar([40, 30, 40])
      definirErro((falha as Error).message)
    } finally {
      definirEnviando(false)
    }
  }

  return (
    <div className="tela-entrada">
      <FundoCidade centro={centro} />
      <div className="entrada-vinheta" />

      <div className="entrada-heroi">
        <motion.div initial={{ scale: 0.2, rotate: -180, opacity: 0 }} animate={{ scale: 1, rotate: 0, opacity: 1 }}
                    transition={{ type: 'spring', stiffness: 120, damping: 14 }}>
          <Bussola rumo={rumo} tamanho={112} inclinar />
        </motion.div>
        <h1 className="marca" aria-label="TrueCompass">
          {MARCA.map((letra, i) => (
            <motion.span key={i} className={i >= 4 ? 'marca-b' : ''} aria-hidden="true"
                         initial={{ opacity: 0, y: 30, rotateX: -90, filter: 'blur(8px)' }}
                         animate={{ opacity: 1, y: 0, rotateX: 0, filter: 'blur(0px)' }}
                         transition={{ delay: 0.35 + i * 0.045, type: 'spring', stiffness: 260, damping: 18,
                                       filter: { delay: 0.35 + i * 0.045, duration: 0.4 }, opacity: { delay: 0.35 + i * 0.045, duration: 0.3 } }}>
              {letra}
            </motion.span>
          ))}
        </h1>
        <motion.div className="subtitulo" initial={{ opacity: 0, letterSpacing: '0.4em' }}
                    animate={{ opacity: 1, letterSpacing: '0.02em' }} transition={{ delay: 0.9, duration: 0.9, ease: [0.16, 1, 0.3, 1] }}>
          Sua corrida, no caminho certo.
        </motion.div>
      </div>

      <motion.form className="entrada-form" onSubmit={enviar}
                   initial={{ opacity: 0, y: 120 }} animate={{ opacity: 1, y: 0 }}
                   transition={{ delay: 0.5, type: 'spring', stiffness: 160, damping: 22 }}>
        <div className="segmentado" role="tablist">
          {(['entrar', 'registrar'] as const).map((chave) => (
            <button key={chave} type="button" role="tab" aria-selected={modo === chave}
                    className={modo === chave ? 'ativo' : ''}
                    onClick={() => { vibrar(6); definirModo(chave); definirErro(null) }}>
              {modo === chave && <motion.span layoutId="segmento" className="segmento-fundo"
                                              transition={{ type: 'spring', stiffness: 500, damping: 34 }} />}
              <span>{chave === 'entrar' ? 'Entrar' : 'Criar conta'}</span>
            </button>
          ))}
        </div>

        <AnimatePresence>{falhaBackend && <Aviso tipo="erro">{falhaBackend}</Aviso>}</AnimatePresence>

        <AnimatePresence initial={false}>
          {registrando && (
            <motion.div key="perfis" className="perfis" initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              {([['passageiro', 'usuario', 'Passageiro', 'Peço corridas'], ['motorista', 'carro', 'Motorista', 'Faço corridas']] as const)
                .map(([chave, icone, titulo, nota]) => (
                  <motion.button key={chave} type="button" whileTap={{ scale: 0.94 }} whileHover={{ y: -3 }}
                                 className={`perfil ${tipo === chave ? 'ativo' : ''}`}
                                 onClick={() => { vibrar(6); definirTipo(chave) }}>
                    <motion.span animate={tipo === chave ? { rotate: [0, -14, 10, 0], scale: [1, 1.2, 1] } : {}}
                                 transition={{ duration: 0.5 }}>
                      <Icone nome={icone} tamanho={26} />
                    </motion.span>
                    <b>{titulo}</b><small>{nota}</small>
                    {tipo === chave && (
                      <motion.span className="perfil-check" layoutId="perfil-check" transition={{ type: 'spring', stiffness: 500, damping: 30 }}>
                        <Icone nome="check" tamanho={12} traco={3.4} />
                      </motion.span>
                    )}
                  </motion.button>
                ))}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence initial={false}>
          {registrando && (
            <Campo key="nome" id="nome" rotulo="Nome" value={nome} required minLength={2} autoComplete="name"
                   onChange={(e) => definirNome(e.target.value)} />
          )}
          <Campo key="email" id="email" rotulo="E-mail" type="email" value={email} required autoComplete="username"
                 inputMode="email" onChange={(e) => definirEmail(e.target.value)} />
          <Campo key="senha" id="senha" rotulo="Senha" type="password" value={senha} required minLength={8}
                 autoComplete={registrando ? 'new-password' : 'current-password'} onChange={(e) => definirSenha(e.target.value)} />
          {registrando && tipo === 'motorista' && (
            <Campo key="placa" id="placa" rotulo="Placa" value={placa} required maxLength={10} autoCapitalize="characters"
                   onChange={(e) => definirPlaca(e.target.value.toUpperCase())} />
          )}
          {registrando && tipo === 'motorista' && (
            <Campo key="modelo" id="modelo" rotulo="Modelo do carro" value={modelo} maxLength={60}
                   onChange={(e) => definirModelo(e.target.value)} />
          )}
        </AnimatePresence>

        <AnimatePresence>{erro && <Aviso tipo="erro">{erro}</Aviso>}</AnimatePresence>

        <div ref={botaoRef}>
          <Botao type="submit" carregando={enviando}>
            {registrando ? 'Criar conta' : 'Entrar'} <Icone nome="seta" tamanho={18} />
          </Botao>
        </div>

        {registrando && (
          <p className="texto-apoio">Mínimo de 8 caracteres. A senha é guardada com bcrypt — o servidor nunca a armazena em texto.</p>
        )}
      </motion.form>
    </div>
  )
}
