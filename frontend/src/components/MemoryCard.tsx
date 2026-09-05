import type { Genome } from '../types'

export default function MemoryCard({ memory }: { memory: Genome }) {
  const renderList = (title: string, items: string[] | null | undefined, isUncertain = false) => {
    if (!items || items.length === 0) return null
    return (
      <div className="mb-6 last:mb-0">
        <h3 className="text-xs font-bold uppercase tracking-widest text-shadowGrey/60 mb-3">{title}</h3>
        <ul className="flex flex-wrap gap-2">
          {items.map((item, idx) => (
            <li 
              key={idx} 
              className={`px-3 py-1.5 text-sm font-medium border-2 ${
                isUncertain 
                  ? 'border-amberEarth bg-amberEarth/10 text-prussianBlue' 
                  : 'border-prussianBlue bg-prussianBlue text-floralWhite'
              }`}
            >
              <span className={isUncertain ? 'text-amberEarth font-bold mr-1' : 'text-brownRed font-bold mr-1'}>
                {isUncertain ? '?' : '✓'}
              </span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  const objectiveArray = memory.objective ? [memory.objective] : []

  return (
    <div className="border-2 border-prussianBlue bg-white p-6 md:p-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
        <div>
          {renderList('Concepts', memory.concepts)}
          {renderList('Operations', memory.operations)}
          {renderList('Objective', objectiveArray)}
        </div>
        <div>
          {renderList('Constraints', memory.constraints)}
          {renderList('Data Structures', memory.data_structures)}
          {renderList('Algorithm Hints', memory.algorithm_hints)}
        </div>
      </div>
      
      {memory.uncertainties && memory.uncertainties.length > 0 && (
        <div className="mt-6 pt-6 border-t-2 border-shadowGrey/20">
          {renderList('Uncertainties', memory.uncertainties, true)}
        </div>
      )}
    </div>
  )
}

