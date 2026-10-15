export interface LoanApplication {
  id: number;
  borrower_id?: number;
  requested_amount: number | string;
  loan_purpose: string;
  status: string;
}

export interface Evidence {
  id: number;
  key: string;
  value: unknown;
  candidates: unknown[];
  verified: boolean;
  version: number;
  document_id: number | null;
}

export interface EvidenceRevision {
  version: number;
  value: unknown;
  candidates: unknown[];
  verified: boolean;
  actor_id: number;
}

export interface Document {
  id: number;
  label: string;
  filename: string;
  sha256: string;
}

export interface LoanProduct {
  id: number;
  lender_id: number;
  name: string;
  min_amount: number;
  max_amount: number;
  apr: number;
}

export interface Lender { id: number; name: string }

export interface LendingRule {
  id: number;
  field_key: string;
  operator: string;
  target: unknown;
  required: boolean;
}

export interface LenderPolicy {
  id: number;
  version: number;
  active: boolean;
  rules: LendingRule[];
}

export interface RuleEvaluation {
  rule_id: number;
  status: string;
  observed: unknown;
  explanation: string;
}

export interface Evaluation {
  id: number;
  lender_id: number;
  policy_id: number;
  decision: 'PASS' | 'FAIL' | 'UNKNOWN';
  stable: boolean | null;
  current: boolean;
  evidence_versions: Record<string, number>;
  rules: RuleEvaluation[];
}

export interface Counterfactual {
  lender_id: number;
  policy_id: number;
  stable: boolean | null;
  worlds: number;
  outcomes: string[];
  reason: string;
}

export interface ReviewTask {
  id: number;
  application_id: number;
  fact_id: number;
  priority: number;
  reason: string;
  status: string;
}

export interface LoanOffer {
  id: number;
  lender_id: number;
  amount: number;
  apr: number;
  status: string;
  simulation: boolean;
}

export interface SimulatedLoan {
  id: number;
  offer_id: number;
  application_id: number;
  status: string;
  amount: number;
  apr: number;
  lender_id: number;
  disbursed_at: string | null;
}

export interface Installment {
  installment: number;
  due_at: string;
  amount_due: number;
  amount_paid: number;
  status: string;
}

export interface UtilizationClaim {
  id: number;
  category: string;
  amount: number;
  note: string;
  status: string;
  links: { document_id: number; annotation: string }[];
}
