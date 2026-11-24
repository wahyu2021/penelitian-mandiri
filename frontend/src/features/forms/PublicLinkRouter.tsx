import { useParams } from 'react-router'
import { PublicAuditPage } from '@/features/forms/PublicAuditPage'
import { PublicFormPage } from '@/features/forms/PublicFormPage'
import { PublicRelevancePage } from '@/features/forms/PublicRelevancePage'

export function PublicLinkRouter() {
  const { token = '' } = useParams()
  if (token.startsWith('rv_')) {
    return <PublicRelevancePage />
  }
  if (token.startsWith('au_')) {
    return <PublicAuditPage />
  }
  return <PublicFormPage />
}
