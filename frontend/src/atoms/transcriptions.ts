/**
 * Transcriptions state management with Jotai
 */

import { atom } from 'jotai'
import type { Transcription } from '../types'

export const transcriptionsAtom = atom<Transcription[]>([])
export const selectedTranscriptionAtom = atom<Transcription | null>(null)

// Filter transcriptions for current user
export const userTranscriptionsAtom = atom((get) => {
  const transcriptions = get(transcriptionsAtom)
  // Note: userId will be checked when used with auth context
  return transcriptions
})

// Loading state
export const transcriptionsLoadingAtom = atom(false)
