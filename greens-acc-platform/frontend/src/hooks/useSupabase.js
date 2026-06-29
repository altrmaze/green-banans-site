import { useMemo } from 'react'
import { useSupabaseContext } from '../context/SupabaseContext'

function useSupabase() {
  const client = useSupabaseContext()

  return useMemo(
    () => ({
      client,
      isConfigured: Boolean(client),
    }),
    [client],
  )
}

export default useSupabase
