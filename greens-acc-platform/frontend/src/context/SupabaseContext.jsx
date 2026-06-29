import { createContext, useContext, useMemo } from 'react'
import { createClient } from '@supabase/supabase-js'

const SupabaseContext = createContext(null)

function createSupabaseClient() {
  const url = import.meta.env.VITE_SUPABASE_URL
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

  if (!url || !anonKey) {
    return null
  }

  return createClient(url, anonKey)
}

export function SupabaseProvider({ children }) {
  const client = useMemo(() => createSupabaseClient(), [])

  return <SupabaseContext.Provider value={client}>{children}</SupabaseContext.Provider>
}

export function useSupabaseContext() {
  return useContext(SupabaseContext)
}
