import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Result } from './chat.service';

export interface ChatMessage {
  role: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

export interface StartChatResponse {
  session_id: string;
  greeting: string;
}

export interface SendMessageResponse {
  reply: string;
  is_completed: boolean;    // canonical — chat analysis is done, show result button
  show_result_button: boolean; // legacy alias from backend
  is_valid: boolean;
  session_id: string;
  turn_count: number;
}

const STORAGE_KEY = 'mbti_gemini_api_key';

@Injectable({ providedIn: 'root' })
export class FabChatService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  sessionId = signal<string | null>(null);
  apiKey = signal<string>(localStorage.getItem(STORAGE_KEY) ?? '');

  saveApiKey(key: string) {
    const trimmed = key.trim();
    this.apiKey.set(trimmed);
    if (trimmed) {
      localStorage.setItem(STORAGE_KEY, trimmed);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  async startSession(): Promise<string> {
    const res = await firstValueFrom(
      this.http.post<StartChatResponse>(`${this.base}/chat/start`, {})
    );
    this.sessionId.set(res.session_id);
    return res.greeting;
  }

  async sendMessage(text: string): Promise<SendMessageResponse> {
    const body: Record<string, unknown> = { session_id: this.sessionId(), text };
    const key = this.apiKey();
    if (key) body['api_key'] = key;
    const resp = await firstValueFrom(
      this.http.post<SendMessageResponse>(`${this.base}/chat/message`, body)
    );
    // Debug: inspect full API response in browser DevTools (F12 → Console)
    console.log('[FabChat] /chat/message response:', resp);
    return resp;
  }

  async getResult(): Promise<Result> {
    const body: Record<string, unknown> = { session_id: this.sessionId() };
    const key = this.apiKey();
    if (key) body['api_key'] = key;
    return firstValueFrom(
      this.http.post<Result>(`${this.base}/chat/result`, body)
    );
  }

  reset() {
    this.sessionId.set(null);
  }
}
