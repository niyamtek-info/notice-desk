export interface Document {
  id: string;
  type: 'Sanction Letter' | 'Loan Agreement' | 'MODT' | 'Sales Deed' | 'Settlement Deed' | 'EC' | 'Power of Attorney' | 'Sale Deed (Merged)' | 'Foreclosure Statement' | 'Statement of Accounts';
  owner: string;
  owner_type: string;
  date: string;
  extent: string;
  status: 'verified' | 'missing' | 'mismatch';
  linked_form: string | null;
  year?: number;
  mismatch_info?: string;
  links_to?: string[];
  [key: string]: any;
}

export interface DocumentHierarchy extends Document {
  children?: DocumentHierarchy[];
  level?: number;
}

export interface FlowNode {
  id: string;
  type: 'documentNode';
  position: { x: number; y: number };
  data: Document;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type: 'smoothstep';
  animated: boolean;
}