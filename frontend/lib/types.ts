export interface RepoInfo {
  name: string
  top_language: string
  languages: string[]
  commit_count_90d: number
  repo_size_kb: number
  is_org: boolean
}

export interface VerificationReport {
  skill_level: 'Junior' | 'Mid-Level' | 'Senior' | 'Principal'
  top_language: string
  security_score: number          // 0–100
  confidence: 'Low' | 'Medium' | 'High'
  languages_detected: string[]
  commit_frequency: string
  complexity_rating: 'Low' | 'Medium' | 'High' | 'Very High'
  repos_analyzed: string[]
  reasoning: string
  generated_at: string            // ISO 8601
}
