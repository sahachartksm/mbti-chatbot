import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Result } from './chat.service';

export interface ChatMessage {
  role: 'user' | 'ai';
  text: string;
  showResultButton?: boolean;
  timestamp: Date;
}

export interface StartChatResponse {
  session_id: string;
  greeting: string;
}

export interface SendMessageResponse {
  reply: string;
  show_result_button: boolean;
  session_id: string;
  turn_count: number;
}

@Injectable({ providedIn: 'root' })
export class FabChatService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  sessionId = signal<string | null>(null);

  async startSession(): Promise<string> {
    const res = await firstValueFrom(
      this.http.post<StartChatResponse>(`${this.base}/chat/start`, {})
    );
    this.sessionId.set(res.session_id);
    return res.greeting;
  }

  async sendMessage(text: string): Promise<SendMessageResponse> {
    return firstValueFrom(
      this.http.post<SendMessageResponse>(`${this.base}/chat/message`, {
        session_id: this.sessionId(),
        text,
      })
    );
  }

  async getResult(): Promise<Result> {
    return firstValueFrom(
      this.http.post<Result>(`${this.base}/chat/result`, {
        session_id: this.sessionId(),
      })
    );
  }

  reset() {
    this.sessionId.set(null);
  }
}
