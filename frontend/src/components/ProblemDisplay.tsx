import type { Problem, Provenance, Example } from '../types'
import React from 'react'

export default function ProblemDisplay({ problem }: { problem: Problem }) {
  const getProvenanceStyle = (key: string) => {
    const p = problem.provenance?.[key] as Provenance | undefined
    if (p === 'remembered') {
      return {
        wrapper: 'border-l-4 border-brownRed pl-4 -ml-[6px]',
        indicator: <span className="text-brownRed font-bold mr-2 text-sm" title="You remembered this">✓</span>
      }
    }
    if (p === 'inferred') {
      return {
        wrapper: 'border-l-4 border-dashed border-amberEarth pl-4 -ml-[6px]',
        indicator: <span className="text-amberEarth font-bold mr-2 text-sm cursor-help" title="Inferred by AI based on context">⚠</span>
      }
    }
    return {
      wrapper: '',
      indicator: null
    }
  }

  const renderSection = (title: string, key: string, content: React.ReactNode) => {
    const style = getProvenanceStyle(key)
    return (
      <div className={`mb-8 ${style.wrapper}`}>
        <h3 className="text-xs font-bold uppercase tracking-widest text-shadowGrey/60 mb-3 flex items-center">
          {style.indicator} {title}
        </h3>
        <div className="text-prussianBlue text-base leading-relaxed">
          {content}
        </div>
      </div>
    )
  }

  return (
    <article className="bg-white border-2 border-prussianBlue p-8 md:p-10 shadow-[8px_8px_0px_#191D32]">
      {renderSection('Problem', 'title', <h2 className="text-3xl font-bold tracking-tight text-prussianBlue">{problem.title}</h2>)}
      
      {renderSection('Description', 'description', <p className="whitespace-pre-wrap">{problem.description}</p>)}
      
      {problem.examples && problem.examples.length > 0 && renderSection('Examples', 'examples', 
        <div className="space-y-6">
          {problem.examples.map((ex, i) => (
            <div key={i} className="bg-floralWhite p-5 border-l-2 border-shadowGrey/20 text-sm">
              <div className="mb-3"><span className="font-bold text-xs uppercase text-shadowGrey/70 tracking-wider">Input:</span> <span className="font-mono ml-2 text-prussianBlue">{ex.input}</span></div>
              <div className="mb-3"><span className="font-bold text-xs uppercase text-shadowGrey/70 tracking-wider">Output:</span> <span className="font-mono ml-2 text-brownRed font-semibold">{ex.output}</span></div>
              {ex.explanation && <div><span className="font-bold text-xs uppercase text-shadowGrey/70 tracking-wider">Explanation:</span> <span className="ml-2">{ex.explanation}</span></div>}
            </div>
          ))}
        </div>
      )}

      {problem.constraints && problem.constraints.length > 0 && renderSection('Constraints', 'constraints', 
        <ul className="list-none space-y-2">
          {problem.constraints.map((c, i) => (
             <li key={i} className="flex items-start">
               <span className="text-brownRed mr-3 opacity-60">■</span>
               <span className="font-mono text-sm">{c}</span>
             </li>
          ))}
        </ul>
      )}

      {problem.notes && problem.notes.length > 0 && (
        <div className="mt-12 pt-8 border-t-2 border-shadowGrey/10">
          <h3 className="text-xs font-bold uppercase tracking-widest text-amberEarth mb-4">Implementation Notes</h3>
          <ul className="space-y-3">
            {problem.notes.map((note, i) => (
              <li key={i} className="text-sm text-shadowGrey flex items-start bg-amberEarth/5 p-3 border border-amberEarth/20">
                <span className="text-amberEarth mr-3 font-bold">ℹ</span> {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  )
}

