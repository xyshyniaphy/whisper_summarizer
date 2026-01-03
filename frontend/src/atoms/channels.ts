/**
 * Channel state management with Jotai
 */

import { atom } from 'jotai'

// Channel interface
export interface Channel {
  id: string
  name: string
  description?: string
  created_by?: string
  created_at: string
  updated_at: string
  member_count?: number
}

// Primitive atoms
export const channelsAtom = atom<Channel[]>([])
export const channelFilterAtom = atom<string | null>(null)
export const selectedChannelsAtom = atom<Set<string>>(new Set())

// Derived atom for user's channels (fetched from backend)
export const userChannelsAtom = atom<Channel[]>([])

// Derived atom for filtered channels
export const filteredChannelsAtom = atom((get) => {
  const channels = get(channelsAtom)
  const filter = get(channelFilterAtom)
  if (!filter) return channels
  return channels.filter(c => c.name.toLowerCase().includes(filter.toLowerCase()))
})
