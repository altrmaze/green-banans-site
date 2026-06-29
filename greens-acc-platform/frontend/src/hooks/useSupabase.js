import { useContext, useMemo } from 'react'
import { SupabaseContext } from '../context/supabaseContext'

function useSupabase() {
  const client = useContext(SupabaseContext)

  return useMemo(
    () => ({
      client,
      isConfigured: Boolean(client),
    }),
    [client],
  )
}

export default useSupabase
