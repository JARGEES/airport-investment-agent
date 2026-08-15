export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  tools_called: string[];
  data_vintage: string;
  assumptions: string[];
}

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
}

export interface HealthResponse {
  status: string;
  model: string;
  analysis_mode: "fast" | "deep";
  available_models: ModelOption[];
  data_vintage: {
    source: string;
    years_covered: number[];
    latest_period: string;
    record_count: number;
  } | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  tools_called?: string[];
  assumptions?: string[];
  data_vintage?: string;
}
