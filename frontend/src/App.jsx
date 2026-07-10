import { useState } from 'react'
import './index.css'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getBadgeClass(status) {
  if (status === true) return 'verified'
  if (status === false) return 'flagged'
  if (status === 'could_not_verify') return 'uncertain'
  if (status === 'contradicted') return 'contradicted'
  if (status === 'unsupported') return 'unsupported'
  return 'uncertain'
}

function getBadgeLabel(status) {
  if (status === true) return '✓ Verified'
  if (status === false) return '✗ Flagged'
  if (status === 'could_not_verify') return '? Uncertain'
  if (status === 'contradicted') return '✗ Contradicted'
  if (status === 'unsupported') return '⚠ Unsupported'
  if (status === 'could_not_verify') return '? Cannot Verify'
  return '? Unknown'
}

function getCitationCardClass(cit) {
  const definiteFlag =
    cit.is_citation_real === false ||
    cit.is_proposition_supported === false ||
    cit.is_quote_accurate === false
  const abstained =
    cit.is_citation_real === 'could_not_verify' ||
    cit.is_proposition_supported === 'could_not_verify' ||
    cit.is_quote_accurate === 'could_not_verify'

  if (definiteFlag) return 'flagged-card'
  if (abstained) return 'uncertain-card'
  return 'verified-card'
}

function getOverallCitationStatus(cit) {
  if (
    cit.is_citation_real === false ||
    cit.is_proposition_supported === false ||
    cit.is_quote_accurate === false
  ) return false
  if (
    cit.is_citation_real === 'could_not_verify' ||
    cit.is_proposition_supported === 'could_not_verify' ||
    cit.is_quote_accurate === 'could_not_verify'
  ) return 'could_not_verify'
  return true
}

function ConfidenceBar({ confidence }) {
  if (confidence == null) return null
  const pct = Math.round(confidence * 100)
  const fillClass = pct >= 80 ? 'high' : pct >= 55 ? 'medium' : 'low'
  return (
    <div className="confidence-row">
      <span className="confidence-label">Confidence</span>
      <div className="confidence-bar-bg">
        <div
          className={`confidence-bar-fill ${fillClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="confidence-pct">{pct}%</span>
    </div>
  )
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function SummaryBar({ stats, riskLevel }) {
  if (!stats) return null
  const riskClass = riskLevel?.toLowerCase() === 'high'
    ? 'risk-high' : riskLevel?.toLowerCase() === 'medium'
    ? 'risk-medium' : 'risk-low'

  return (
    <div className="summary-bar" id="summary-bar">
      <div className={`stat-card ${riskClass}`}>
        <div className="stat-label">Risk Level</div>
        <div className="stat-value">{riskLevel || '–'}</div>
        <div className="stat-sub">Overall assessment</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Total Findings</div>
        <div className="stat-value" style={{ color: '#f04141' }}>
          {stats.total_definitive_findings ?? '–'}
        </div>
        <div className="stat-sub">Definitive issues</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Citations</div>
        <div className="stat-value" style={{ color: '#60a5fa' }}>
          {stats.citation_definitive_flags ?? '–'}
          <span style={{ fontSize: '0.9rem', color: '#555b70' }}>
            /{stats.total_citations_examined ?? '–'}
          </span>
        </div>
        <div className="stat-sub">Flagged / examined</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Fact Issues</div>
        <div className="stat-value" style={{ color: '#f59e0b' }}>
          {(stats.fact_contradicted ?? 0) + (stats.fact_unsupported ?? 0)}
          <span style={{ fontSize: '0.9rem', color: '#555b70' }}>
            /{stats.total_fact_claims_examined ?? '–'}
          </span>
        </div>
        <div className="stat-sub">Flagged / examined</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Abstention Rate</div>
        <div className="stat-value" style={{ color: '#a78bfa' }}>
          {stats.abstention_rate != null
            ? `${Math.round(stats.abstention_rate * 100)}%`
            : '–'}
        </div>
        <div className="stat-sub">Honest uncertainty</div>
      </div>
    </div>
  )
}

function CitationCard({ cit, index }) {
  const [expanded, setExpanded] = useState(false)
  const cardClass = getCitationCardClass(cit)
  const overallStatus = getOverallCitationStatus(cit)

  return (
    <div className={`item-card ${cardClass}`} id={`citation-${index}`}>
      <div className="card-top">
        <span className="card-citation">{cit.citation}</span>
        <span className={`badge ${getBadgeClass(overallStatus)}`}>
          {getBadgeLabel(overallStatus)}
        </span>
      </div>

      {cit.proposition && (
        <div className="card-proposition">"{cit.proposition}"</div>
      )}

      {/* Per-field status pills when there's a mix */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        {cit.is_citation_real !== undefined && cit.is_citation_real !== null && (
          <span className={`badge ${getBadgeClass(cit.is_citation_real)}`} style={{ fontSize: '0.68rem' }}>
            Citation real: {cit.is_citation_real === true ? 'Yes' : cit.is_citation_real === false ? 'No' : '?'}
          </span>
        )}
        {cit.is_quote_accurate !== undefined && cit.is_quote_accurate !== null && (
          <span className={`badge ${getBadgeClass(cit.is_quote_accurate)}`} style={{ fontSize: '0.68rem' }}>
            Quote accurate: {cit.is_quote_accurate === true ? 'Yes' : cit.is_quote_accurate === false ? 'No' : '?'}
          </span>
        )}
        {cit.is_proposition_supported !== undefined && cit.is_proposition_supported !== null && (
          <span className={`badge ${getBadgeClass(cit.is_proposition_supported)}`} style={{ fontSize: '0.68rem' }}>
            Proposition supported: {cit.is_proposition_supported === true ? 'Yes' : cit.is_proposition_supported === false ? 'No' : '?'}
          </span>
        )}
      </div>

      {cit.quote && (
        <div className="card-quote">❝ {cit.quote}</div>
      )}

      {cit.explanation && (
        <>
          <div className="card-explanation" style={{
            maxHeight: expanded ? 'none' : '3.6em',
            overflow: 'hidden',
            position: 'relative',
          }}>
            {cit.explanation}
          </div>
          {cit.explanation.length > 160 && (
            <button
              onClick={() => setExpanded(e => !e)}
              style={{
                background: 'none', border: 'none', color: '#6366f1',
                fontSize: '0.78rem', cursor: 'pointer', padding: '4px 0', marginTop: '4px'
              }}
            >
              {expanded ? '▲ Show less' : '▼ Show more'}
            </button>
          )}
        </>
      )}
    </div>
  )
}

function FactCard({ issue, index }) {
  const [expanded, setExpanded] = useState(false)
  const status = issue.status || 'could_not_verify'
  const cardClass =
    status === 'contradicted' ? 'flagged-card' :
    status === 'unsupported' ? 'uncertain-card' : 'verified-card'

  return (
    <div className={`item-card ${cardClass}`} id={`fact-${index}`}>
      <div className="card-top">
        <span className="card-citation" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}>
          {issue.claim}
        </span>
        <span className={`badge ${getBadgeClass(status)}`}>
          {getBadgeLabel(status)}
        </span>
      </div>

      {issue.evidence && (
        <div className="evidence-block">
          <div className="evidence-label">Evidence</div>
          <div style={{ maxHeight: expanded ? 'none' : '4.8em', overflow: 'hidden' }}>
            {issue.evidence}
          </div>
          {issue.evidence.length > 200 && (
            <button
              onClick={() => setExpanded(e => !e)}
              style={{
                background: 'none', border: 'none', color: '#6366f1',
                fontSize: '0.75rem', cursor: 'pointer', padding: '4px 0', marginTop: '4px'
              }}
            >
              {expanded ? '▲ Show less' : '▼ Show more'}
            </button>
          )}
        </div>
      )}

      {issue.explanation && (
        <div className="card-explanation" style={{ marginTop: '10px' }}>
          {issue.explanation}
        </div>
      )}

      <ConfidenceBar confidence={issue.confidence} />
    </div>
  )
}

function JudicialMemo({ memo }) {
  if (!memo) return null
  const memoText = typeof memo === 'string' ? memo : memo.memo || ''
  if (!memoText) return null

  return (
    <div className="section" id="judicial-memo">
      <div className="section-header">
        <h2>Judicial Memo</h2>
      </div>
      <div className="judicial-memo-card">
        <div className="memo-header">
          <span className="memo-icon">⚖️</span>
          <h3>Synthesized for the Court — Generated by JudicialMemoAgent</h3>
        </div>
        <p>{memoText}</p>
      </div>
    </div>
  )
}

// ─── Main App ──────────────────────────────────────────────────────────────────

function App() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [runAt, setRunAt] = useState(null)

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    setReport(null)

    try {
      const response = await fetch('http://localhost:8002/analyze', {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`)
      }
      const data = await response.json()
      setReport(data.report)
      setRunAt(new Date().toLocaleString())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const citations = report?.citation_analysis?.citations ?? []
  const issues = report?.fact_analysis?.issues ?? []

  return (
    <div className="app-wrapper">
      {/* Header */}
      <header className="app-header">
        <div className="logo-icon">🔍</div>
        <div>
          <h1>BS Detector</h1>
          <div className="subtitle">
            Legal brief verification pipeline — Rivera v. Harmon Construction Group
          </div>
        </div>
      </header>

      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px', flexWrap: 'wrap' }}>
        <button
          id="run-analysis-btn"
          className="run-btn"
          onClick={runAnalysis}
          disabled={loading}
        >
          {loading ? (
            <>
              <div className="btn-spinner" />
              Analyzing…
            </>
          ) : (
            <>⚡ Run Analysis</>
          )}
        </button>
        {runAt && !loading && (
          <span style={{ fontSize: '0.78rem', color: '#555b70' }}>
            Last run: {runAt}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="error-banner">
          <span className="icon">⚠️</span>
          <div>
            <strong>Analysis failed:</strong> {error}
            <div style={{ marginTop: '4px', color: '#9ca3af' }}>
              Make sure the backend is running at <code>http://localhost:8002</code>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!report && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <p>Click <strong>Run Analysis</strong> to verify the case documents.</p>
          <p style={{ marginTop: '8px', fontSize: '0.8rem' }}>
            Pipeline: CitationAgent → FactCheckerAgent → ReportBuilder → JudicialMemoAgent
          </p>
        </div>
      )}

      {/* Report */}
      {report && (
        <>
          {/* Summary stats */}
          <SummaryBar stats={report.summary_stats} riskLevel={report.risk_level} />

          {/* Citation findings */}
          <section className="section" id="citation-section">
            <div className="section-header">
              <h2>Citation Findings</h2>
              <span className="section-count">{citations.length} examined</span>
            </div>
            {citations.length === 0 ? (
              <p style={{ color: '#555b70', fontSize: '0.875rem' }}>No citations found.</p>
            ) : (
              citations.map((cit, i) => (
                <CitationCard key={i} cit={cit} index={i} />
              ))
            )}
          </section>

          <hr className="section-divider" />

          {/* Fact issues */}
          <section className="section" id="fact-section">
            <div className="section-header">
              <h2>Fact-Check Issues</h2>
              <span className="section-count">{issues.length} claims examined</span>
            </div>
            {issues.length === 0 ? (
              <p style={{ color: '#555b70', fontSize: '0.875rem' }}>No fact issues found.</p>
            ) : (
              issues.map((issue, i) => (
                <FactCard key={i} issue={issue} index={i} />
              ))
            )}
          </section>

          <hr className="section-divider" />

          {/* Judicial memo */}
          <JudicialMemo memo={report.judicial_memo} />
        </>
      )}
    </div>
  )
}

export default App
