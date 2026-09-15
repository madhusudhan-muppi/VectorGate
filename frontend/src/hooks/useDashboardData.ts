import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ActivityBucket, ApiState } from '../types'

const initialState: ApiState = {
  health: null,
  summary: null,
  nodes: [],
  detections: [],
  activity: [],
  loading: true,
  error: null,
  lastRefresh: null,
}

export function useDashboardData(selectedNodeId: string | null) {
  const [state, setState] = useState<ApiState>(initialState)
  const seenIds = useRef<Set<number>>(new Set())
  const [newDetectionIds, setNewDetectionIds] = useState<Set<number>>(new Set())

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const [health, summary, nodes, detections] = await Promise.all([
        api.health(signal),
        api.summary(signal),
        api.nodes(signal),
        api.detections(signal),
      ])
      const freshIds = new Set(detections.map((item) => item.id).filter((id) => !seenIds.current.has(id)))
      if (seenIds.current.size > 0 && freshIds.size > 0) {
        setNewDetectionIds(freshIds)
        window.setTimeout(() => setNewDetectionIds(new Set()), 1600)
      }
      seenIds.current = new Set(detections.map((item) => item.id))
      setState((previous) => ({ ...previous, health, summary, nodes, detections, loading: false, error: null, lastRefresh: new Date() }))
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setState((previous) => ({ ...previous, loading: false, error: error instanceof Error ? error.message : 'Unknown backend error' }))
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    const timer = window.setInterval(() => void refresh(), 4000)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [refresh])

  useEffect(() => {
    if (!selectedNodeId) {
      setState((previous) => ({ ...previous, activity: [] }))
      return
    }
    const controller = new AbortController()
    const loadActivity = async () => {
      try {
        const activity: ActivityBucket[] = await api.activity(selectedNodeId, controller.signal)
        setState((previous) => ({ ...previous, activity }))
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState((previous) => ({ ...previous, activity: [] }))
      }
    }
    void loadActivity()
    const timer = window.setInterval(() => void loadActivity(), 8000)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [selectedNodeId])

  return { ...state, newDetectionIds, refresh }
}
