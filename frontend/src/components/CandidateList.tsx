import type { Candidate } from '../types'
import ConfidenceScore from './ConfidenceScore'

interface Props {
  candidates: Candidate[]
  onSelect: (candidate: Candidate) => void
}

export default function CandidateList({ candidates, onSelect }: Props) {
  return (
    <ul className="space-y-4">
      {candidates.map((c) => (
        <li key={c.id}>
          <button 
            className="w-full text-left group block border-2 border-shadowGrey/20 bg-white p-6 hover:border-prussianBlue hover:shadow-[4px_4px_0px_#191D32] transition-all"
            onClick={() => onSelect(c)}
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-xl font-bold text-prussianBlue group-hover:text-brownRed transition-colors pr-4">{c.title}</h3>
              <div className="w-24 shrink-0">
                <ConfidenceScore value={c.confidence} />
              </div>
            </div>
            
            <div className="text-sm font-mono text-shadowGrey/70 mb-4">
              {c.difficulty && <span className="uppercase text-amberEarth font-bold mr-2">{c.difficulty}</span>}
              {c.topics?.length > 0 && <span>· {c.topics.join(', ')}</span>}
            </div>
            
            {c.company_count > 0 && (
              <div className="text-sm text-prussianBlue mb-4 font-medium">
                Asked at <span className="font-bold">{c.companies.slice(0, 3).join(', ')}</span>
                {c.company_count > 3 && ` and ${c.company_count - 3} others`}
              </div>
            )}
            
            {c.reason && (
              <p className="text-shadowGrey italic border-l-4 border-amberEarth pl-4 text-sm py-1 bg-floralWhite/50">
                "{c.reason}"
              </p>
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}

