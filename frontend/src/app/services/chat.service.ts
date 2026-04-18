import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Choice {
  id: string;
  text: string;
}

export interface Question {
  id: number;
  text: string;
  choices: Choice[];
}

export interface StartResponse {
  session_id: string;
  lang: string;
  questions: Question[];
  total: number;
}

export interface AnswerResponse {
  ok: boolean;
  answered_count: number;
  total: number;
}

export interface Dimensions {
  E: number; I: number;
  S: number; N: number;
  T: number; F: number;
  J: number; P: number;
}

export interface Result {
  session_id: string;
  mbti_type: string;
  nickname: string;
  dimensions: Dimensions;
  confidence: number;
  description: string;
  strengths: string[];
  weaknesses: string[];
  careers: string[];
  famous_people: string[];
  compatible_types: string[];
  analyzed_at: string;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  start(lang: 'th' | 'en' = 'th'): Observable<StartResponse> {
    return this.http.post<StartResponse>(`${this.base}/session/start`, { lang });
  }

  answer(sessionId: string, questionId: number, choiceId: string): Observable<AnswerResponse> {
    return this.http.post<AnswerResponse>(`${this.base}/session/${sessionId}/answer`, {
      question_id: questionId,
      choice_id: choiceId,
    });
  }

  analyze(sessionId: string, freeText?: string): Observable<Result> {
    return this.http.post<Result>(`${this.base}/session/${sessionId}/analyze`, {
      free_text: freeText || '',
    });
  }

  getResult(sessionId: string): Observable<Result> {
    return this.http.get<Result>(`${this.base}/session/${sessionId}/result`);
  }
}
