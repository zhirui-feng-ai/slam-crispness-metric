import { useEffect, useState } from 'react'

const BASE = import.meta.env.BASE_URL || '/'

/** Minimal CSV parser → array of row objects. Numbers coerced; no quoted-comma
 *  fields exist in our data (mode names use underscores). */
export function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/)
  const headers = lines[0].split(',')
  return lines.slice(1).map(line => {
    const cells = line.split(',')
    const row = {}
    headers.forEach((h, i) => {
      const v = cells[i]
      const num = v === '' || v === undefined ? NaN : Number(v)
      row[h] = v !== '' && v !== undefined && !Number.isNaN(num) ? num : v
    })
    return row
  })
}

function useFetch(path, transform) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    let alive = true
    fetch(BASE + path)
      .then(r => { if (!r.ok) throw new Error(`${r.status} ${path}`); return r.text() })
      .then(t => { if (alive) setData(transform(t)) })
      .catch(e => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [path])
  return { data, error }
}

export const useJSON = path => useFetch(path, t => JSON.parse(t))
export const useCSV = path => useFetch(path, parseCSV)
export const useText = path => useFetch(path, t => t)

export const figURL = name => `${BASE}figures/${name}`
export const reportURL = name => `${BASE}reports/${name}`
