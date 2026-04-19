import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// ----- Server-sent question (open-ended) -----
export interface Question {
  id: number;
  text: string;
  hint: string;
  dimension: 'EI' | 'SN' | 'TF' | 'JP' | 'MIX';
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

// ----- Analyze payload -----
export interface AnalyzeAnswer {
  question_id: number;
  text: string;
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
  analysis: string;
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

  /** Save (or overwrite) a single free-text answer for one question. */
  saveAnswer(sessionId: string, questionId: number, text: string): Observable<AnswerResponse> {
    return this.http.post<AnswerResponse>(`${this.base}/session/${sessionId}/answer`, {
      question_id: questionId,
      text,
    });
  }

  /**
   * Submit all answers at once and get MBTI analysis back.
   * Can be slow (LLM inference) — typically 15-90s on CPU.
   */
  analyze(sessionId: string, answers: AnalyzeAnswer[]): Observable<Result> {
    return this.http.post<Result>(`${this.base}/session/${sessionId}/analyze`, {
      answers,
    });
  }

  getResult(sessionId: string): Observable<Result> {
    return this.http.get<Result>(`${this.base}/session/${sessionId}/result`);
  }
}
