export type IndustryTemplate = 'GENERAL' | 'FINANCE' | 'HEALTHCARE' | 'ECOMMERCE'

export interface PendingSignupDetails {
  fullName: string
  companyName: string
  workspaceName: string
  template: IndustryTemplate
}

const STORAGE_KEY = 'agentmesh.pending-signup'

export function savePendingSignup(details: PendingSignupDetails): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(details))
}

export function readPendingSignup(): PendingSignupDetails | null {
  const value = localStorage.getItem(STORAGE_KEY)
  if (!value) return null
  try {
    const parsed = JSON.parse(value) as Partial<PendingSignupDetails>
    if (
      typeof parsed.fullName !== 'string' ||
      typeof parsed.companyName !== 'string' ||
      typeof parsed.workspaceName !== 'string' ||
      !['GENERAL', 'FINANCE', 'HEALTHCARE', 'ECOMMERCE'].includes(String(parsed.template))
    ) return null
    return parsed as PendingSignupDetails
  } catch {
    return null
  }
}

export function clearPendingSignup(): void {
  localStorage.removeItem(STORAGE_KEY)
}
