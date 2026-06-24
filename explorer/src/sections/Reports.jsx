import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useText, figURL } from '../lib/data.js'

const DOCS = [['results.md', 'Results'], ['methods.md', 'Methods']]

// rewrite ../figures/foo.png (and any image) to the served figures path
const mapImg = src => figURL((src || '').split('/').pop())

export default function Reports() {
  const [doc, setDoc] = useState('results.md')
  const { data: text, error } = useText(`reports/${doc}`)

  return (
    <div>
      <div className="sec-tag">Write-up</div>
      <h1 className="sec-title">Reports</h1>
      <p className="sec-desc">
        The generated methods and results documents, rendered with their figures inline.
        Source lives in <span className="kbd">reports/</span>.
      </p>

      <div style={{ display: 'flex', gap: 6, marginBottom: 22 }}>
        {DOCS.map(([f, l]) => (
          <button key={f} className={`btn${doc === f ? ' active' : ''}`} onClick={() => { setDoc(f); window.scrollTo(0, 0) }}>{l}</button>
        ))}
      </div>

      <div className="card md">
        {error && <div style={{ color: 'var(--red)' }}>Couldn’t load {doc}: {error}</div>}
        {!text && !error && <div className="loading">Loading {doc}…</div>}
        {text && (
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              img: ({ src, alt }) => <img src={mapImg(src)} alt={alt} loading="lazy" />,
              a: ({ href, children }) => {
                const external = /^https?:/.test(href || '')
                return external
                  ? <a href={href} target="_blank" rel="noreferrer">{children}</a>
                  : <span title={href}>{children}</span>  // local file links → plain text
              },
            }}
          >{text}</Markdown>
        )}
      </div>
    </div>
  )
}
