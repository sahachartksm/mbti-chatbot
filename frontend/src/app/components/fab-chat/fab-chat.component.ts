import {
  Component, signal, inject, ElementRef, ViewChild, AfterViewChecked,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FabChatService, ChatMessage } from '../../services/fab-chat.service';
import { Result } from '../../services/chat.service';

@Component({
  selector: 'app-fab-chat',
  standalone: true,
  imports: [FormsModule],
  template: `
    <!-- ── FAB Button ────────────────────────────────────────────── -->
    <button
      class="fab"
      [class.open]="isOpen()"
      (click)="toggleChat()"
      title="คุยกับ AI วิเคราะห์ MBTI"
      aria-label="เปิด/ปิด MBTI Chatbot"
    >
      <span class="fab-icon">{{ isOpen() ? '✕' : '🧠' }}</span>
    </button>

    <!-- ── Chat Window ───────────────────────────────────────────── -->
    <div class="chat-window" [class.visible]="isOpen()" role="dialog" aria-label="MBTI Chatbot">

      <!-- Header -->
      <div class="chat-header">
        <div class="header-info">
          <span class="header-avatar">🧠</span>
          <div>
            <div class="header-title">MBTI AI Chat</div>
            <div class="header-sub">วิเคราะห์บุคลิกภาพจากบทสนทนา</div>
          </div>
        </div>
        <button class="close-btn" (click)="toggleChat()">✕</button>
      </div>

      <!-- Messages -->
      <div class="messages" #scrollContainer>
        @if (isStarting()) {
          <div class="msg-row ai">
            <div class="avatar">🧠</div>
            <div class="bubble ai-bubble typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        }

        @for (msg of messages(); track $index) {
          <div class="msg-row" [class.user]="msg.role === 'user'" [class.ai]="msg.role === 'ai'">
            @if (msg.role === 'ai') { <div class="avatar">🧠</div> }
            <div class="bubble" [class.ai-bubble]="msg.role === 'ai'" [class.user-bubble]="msg.role === 'user'">
              {{ msg.text }}
              @if (msg.showResultButton && !mbtiResult()) {
                <button class="result-btn" (click)="showResult()" [disabled]="isLoadingResult()">
                  {{ isLoadingResult() ? 'กำลังวิเคราะห์...' : '✨ ดูผล MBTI ของคุณ' }}
                </button>
              }
            </div>
            @if (msg.role === 'user') { <div class="avatar user-avatar">👤</div> }
          </div>
        }

        @if (isLoading()) {
          <div class="msg-row ai">
            <div class="avatar">🧠</div>
            <div class="bubble ai-bubble typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        }

        <!-- Inline Result Card -->
        @if (mbtiResult(); as r) {
          <div class="result-card">
            <div class="result-type">{{ r.mbti_type }}</div>
            <div class="result-nick">{{ r.nickname }}</div>
            <div class="result-conf">ความมั่นใจ: {{ (r.confidence * 100).toFixed(0) }}%</div>
            <div class="result-dims">
              @for (pair of dimPairs; track pair[0]) {
                <div class="dim-row">
                  <span class="dim-label">{{ pair[0] }}</span>
                  <div class="dim-bar">
                    <div class="dim-fill" [style.width.%]="getDimValue(r, pair[0])"></div>
                  </div>
                  <span class="dim-label dim-right">{{ pair[1] }}</span>
                </div>
              }
            </div>
            <div class="result-desc">{{ r.description }}</div>
            <button class="restart-btn" (click)="restart()">🔄 ทำใหม่อีกครั้ง</button>
          </div>
        }
      </div>

      <!-- Error -->
      @if (error()) {
        <div class="chat-error">{{ error() }}</div>
      }

      <!-- Input Bar -->
      @if (!mbtiResult()) {
        <div class="input-bar">
          <input
            #inputEl
            class="chat-input"
            type="text"
            placeholder="พิมพ์ข้อความ..."
            [(ngModel)]="inputText"
            (keyup.enter)="sendMessage()"
            [disabled]="isLoading() || isStarting()"
            maxlength="500"
          />
          <button
            class="send-btn"
            (click)="sendMessage()"
            [disabled]="!inputText.trim() || isLoading() || isStarting()"
          >
            ส่ง
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    /* ── FAB ─────────────────────────────────────────────────────── */
    :host {
      position: fixed;
      bottom: 28px;
      right: 28px;
      z-index: 1000;
      display: block;
    }

    .fab {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      box-shadow: 0 6px 20px rgba(102,126,234,0.55);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .fab:hover { transform: scale(1.1); box-shadow: 0 8px 26px rgba(102,126,234,0.7); }
    .fab.open { transform: rotate(0deg); background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }

    .fab-icon { font-size: 26px; line-height: 1; }

    /* ── Chat Window ─────────────────────────────────────────────── */
    .chat-window {
      position: fixed;
      bottom: 100px;
      right: 28px;
      width: 360px;
      height: 520px;
      border-radius: 18px;
      background: #fff;
      box-shadow: 0 20px 60px rgba(0,0,0,0.18);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      transform: translateY(16px) scale(0.96);
      transform-origin: bottom right;
      pointer-events: none;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }
    .chat-window.visible {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: all;
    }

    /* ── Header ──────────────────────────────────────────────────── */
    .chat-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 16px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      flex-shrink: 0;
    }
    .header-info { display: flex; align-items: center; gap: 10px; }
    .header-avatar { font-size: 24px; }
    .header-title { font-weight: 700; font-size: 0.95rem; }
    .header-sub { font-size: 0.75rem; opacity: 0.85; margin-top: 1px; }
    .close-btn {
      background: rgba(255,255,255,0.2); border: none; color: white;
      width: 28px; height: 28px; border-radius: 50%;
      cursor: pointer; font-size: 0.85rem; display: flex; align-items: center; justify-content: center;
    }
    .close-btn:hover { background: rgba(255,255,255,0.35); }

    /* ── Messages ────────────────────────────────────────────────── */
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }

    .msg-row { display: flex; align-items: flex-end; gap: 8px; }
    .msg-row.user { flex-direction: row-reverse; }

    .avatar {
      width: 32px; height: 32px; border-radius: 50%;
      background: linear-gradient(135deg, #667eea, #764ba2);
      display: flex; align-items: center; justify-content: center;
      font-size: 16px; flex-shrink: 0;
    }
    .user-avatar { background: linear-gradient(135deg, #f093fb, #f5576c); }

    .bubble {
      max-width: 75%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 0.88rem;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .ai-bubble {
      background: #f3f4f6;
      border-bottom-left-radius: 4px;
      color: #1f2937;
    }
    .user-bubble {
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
      border-bottom-right-radius: 4px;
    }

    /* ── Typing indicator ────────────────────────────────────────── */
    .typing {
      display: flex;
      gap: 4px;
      align-items: center;
      padding: 12px 16px;
    }
    .typing span {
      width: 7px; height: 7px; border-radius: 50%;
      background: #9ca3af;
      animation: bounce 1.2s infinite;
    }
    .typing span:nth-child(2) { animation-delay: 0.2s; }
    .typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-6px); }
    }

    /* ── Result button inside bubble ─────────────────────────────── */
    .result-btn {
      display: block;
      margin-top: 10px;
      width: 100%;
      padding: 8px 12px;
      border-radius: 10px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
      border: none;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .result-btn:hover:not(:disabled) { opacity: 0.88; }
    .result-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── Inline Result Card ──────────────────────────────────────── */
    .result-card {
      background: linear-gradient(135deg, #f0f4ff, #fdf4ff);
      border: 1px solid #e0d7ff;
      border-radius: 14px;
      padding: 16px;
      margin: 4px 0;
    }
    .result-type {
      font-size: 2rem; font-weight: 800; letter-spacing: 2px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      -webkit-background-clip: text; background-clip: text; color: transparent;
      text-align: center;
    }
    .result-nick { text-align: center; font-weight: 600; font-size: 1rem; margin-bottom: 4px; }
    .result-conf { text-align: center; font-size: 0.78rem; color: #6b7280; margin-bottom: 12px; }

    .result-dims { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
    .dim-row { display: grid; grid-template-columns: 18px 1fr 18px; gap: 6px; align-items: center; }
    .dim-label { font-size: 0.75rem; font-weight: 700; color: #6366f1; text-align: center; }
    .dim-right { color: #ec4899; }
    .dim-bar { height: 7px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
    .dim-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 4px; }

    .result-desc { font-size: 0.82rem; color: #374151; line-height: 1.5; margin-bottom: 12px; }
    .restart-btn {
      width: 100%; padding: 8px; border-radius: 10px;
      background: white; border: 1px solid #667eea;
      color: #667eea; font-size: 0.85rem; font-weight: 600; cursor: pointer;
    }
    .restart-btn:hover { background: #f3f4f6; }

    /* ── Error ───────────────────────────────────────────────────── */
    .chat-error {
      padding: 8px 14px;
      background: #fee2e2;
      color: #991b1b;
      font-size: 0.82rem;
      flex-shrink: 0;
    }

    /* ── Input Bar ───────────────────────────────────────────────── */
    .input-bar {
      display: flex;
      gap: 8px;
      padding: 12px 14px;
      border-top: 1px solid #f3f4f6;
      flex-shrink: 0;
    }
    .chat-input {
      flex: 1;
      padding: 9px 14px;
      border: 1px solid #e5e7eb;
      border-radius: 20px;
      font-size: 0.88rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }
    .chat-input:focus { border-color: #667eea; }
    .chat-input:disabled { background: #f9fafb; }

    .send-btn {
      padding: 9px 16px;
      border-radius: 20px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
      border: none;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      flex-shrink: 0;
      transition: opacity 0.2s;
    }
    .send-btn:hover:not(:disabled) { opacity: 0.88; }
    .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    /* ── Mobile responsive ───────────────────────────────────────── */
    @media (max-width: 420px) {
      .chat-window { width: calc(100vw - 32px); right: 16px; }
      :host { right: 16px; bottom: 20px; }
    }
  `],
})
export class FabChatComponent implements AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef<HTMLDivElement>;

  private fabChat = inject(FabChatService);

  isOpen = signal(false);
  messages = signal<ChatMessage[]>([]);
  inputText = '';
  isStarting = signal(false);
  isLoading = signal(false);
  isLoadingResult = signal(false);
  mbtiResult = signal<Result | null>(null);
  error = signal<string | null>(null);

  readonly dimPairs = [['E', 'I'], ['S', 'N'], ['T', 'F'], ['J', 'P']];

  private shouldScroll = false;

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  async toggleChat() {
    this.isOpen.update(v => !v);
    if (this.isOpen() && this.messages().length === 0) {
      await this.startConversation();
    }
  }

  private async startConversation() {
    this.isStarting.set(true);
    this.error.set(null);
    try {
      const greetingText = await this.fabChat.startSession();
      this.messages.update(msgs => [...msgs, {
        role: 'ai',
        text: greetingText,
        timestamp: new Date(),
      }]);
      this.shouldScroll = true;
    } catch {
      this.error.set('ไม่สามารถเชื่อมต่อ backend ได้ กรุณาตรวจสอบว่าเปิด server แล้ว');
    } finally {
      this.isStarting.set(false);
    }
  }

  async sendMessage() {
    const text = this.inputText.trim();
    if (!text || this.isLoading()) return;

    this.inputText = '';
    this.error.set(null);

    // แสดง user bubble ทันที (optimistic)
    this.messages.update(msgs => [...msgs, {
      role: 'user',
      text,
      timestamp: new Date(),
    }]);
    this.shouldScroll = true;
    this.isLoading.set(true);

    try {
      const resp = await this.fabChat.sendMessage(text);
      this.messages.update(msgs => [...msgs, {
        role: 'ai',
        text: resp.reply,
        showResultButton: resp.show_result_button,
        timestamp: new Date(),
      }]);
      this.shouldScroll = true;
    } catch {
      this.error.set('ส่งข้อความไม่สำเร็จ กรุณาลองใหม่');
    } finally {
      this.isLoading.set(false);
    }
  }

  async showResult() {
    this.isLoadingResult.set(true);
    this.error.set(null);
    try {
      const result = await this.fabChat.getResult();
      this.mbtiResult.set(result);
      this.shouldScroll = true;
    } catch {
      this.error.set('วิเคราะห์ผลไม่สำเร็จ กรุณาลองใหม่');
    } finally {
      this.isLoadingResult.set(false);
    }
  }

  restart() {
    this.messages.set([]);
    this.mbtiResult.set(null);
    this.error.set(null);
    this.fabChat.reset();
    this.startConversation();
  }

  getDimValue(result: Result, pole: string): number {
    return (result.dimensions as unknown as Record<string, number>)[pole] ?? 50;
  }

  private scrollToBottom() {
    try {
      const el = this.scrollContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    } catch { /* ignore */ }
  }
}
