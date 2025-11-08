export interface Anomaly {
  id: string;
  type: 'amount_mismatch' | 'duplicate' | 'tax_calculation' | 'vendor_mismatch';
  priority: 'low' | 'medium' | 'high';
  description: string;
  details: string;
  resolved: boolean;
}

export interface Invoice {
  id: string;
  fileName: string;
  vendor: string;
  amount: number;
  date: string;
  status: 'pending' | 'verified' | 'flagged';
  anomalies: Anomaly[];
  uploadedAt: Date;
}