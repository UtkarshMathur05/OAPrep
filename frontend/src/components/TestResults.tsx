import type { VerifyResponse } from '../types'
import { useState } from 'react'

export default function TestResults({ result }: { result: VerifyResponse }) {
  const [expanded, setExpanded] = useState(false)
  
  const isSuccess = result.status.toLowerCase().includes('accepted')
  
  return (
    <div className={`border-2 p-6 shadow-[4px_4px_0px_0px] ${
      isSuccess 
        ? 'border-[#2e7d32] bg-[#f1f8f1] shadow-[#2e7d32]' 
        : 'border-brownRed bg-brownRed/5 shadow-brownRed'
    }`}>
      <div className="flex justify-between items-end mb-4 border-b-2 border-current pb-4 opacity-80">
        <div>
          <h3 className={`text-2xl font-bold uppercase tracking-tight ${isSuccess ? 'text-[#2e7d32]' : 'text-brownRed'}`}>
            {isSuccess ? '✓ Accepted' : '✗ ' + result.status}
          </h3>
          <p className="text-sm font-medium mt-1 text-shadowGrey/70">
            {result.passed} / {result.total} test cases passed
          </p>
        </div>
        <div className="text-right text-sm font-mono text-shadowGrey/80">
          <div>Runtime: {result.runtime || 'N/A'}</div>
          <div>Memory: {result.memory || 'N/A'}</div>
        </div>
      </div>
      
      {result.results.length > 0 && !isSuccess && (
         <div className="mt-6">
            <button 
              onClick={() => setExpanded(!expanded)} 
              className="text-xs font-bold uppercase tracking-widest text-brownRed hover:opacity-70 transition-opacity flex items-center gap-2"
            >
              <span className="text-lg leading-none">{expanded ? '-' : '+'}</span>
              {expanded ? 'Hide Failing Cases' : 'View Failing Cases'}
            </button>
            
            {expanded && (
               <div className="space-y-4 mt-4">
                 {result.results.filter(r => !r.passed).map((r, idx) => (
                    <div key={idx} className="bg-white border-2 border-brownRed/30 p-4 font-mono text-sm">
                       <div className="text-xs font-bold text-shadowGrey/50 mb-3 uppercase tracking-wider">Test Case {r.index ?? idx + 1}</div>
                       <div className="mb-3"><span className="text-shadowGrey font-bold">Input:</span> <br/><span className="text-prussianBlue">{r.input}</span></div>
                       <div className="mb-3"><span className="text-[#2e7d32] font-bold">Expected Output:</span> <br/>{r.expected_output}</div>
                       <div><span className="text-brownRed font-bold">Actual Output:</span> <br/>{r.actual_output}</div>
                    </div>
                 ))}
               </div>
            )}
         </div>
      )}
    </div>
  )
}

