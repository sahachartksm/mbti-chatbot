import { Component, OnInit, OnDestroy, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ChatService, Question, AnalyzeAnswer } from '../../services/chat.service';
import { ConfirmDialogComponent } from '../confirm-dialog/confirm-dialog.component';

const LS_PREFIX = 'mbti_answers_';
const SS_PREFIX = 'mbti_questions_';

@Component({
  selector: 'app-questionnaire',
  standalone: true,
  imports: [FormsModule, ConfirmDialogComponent],
  template: `
    @if (loading()) {
      <section class="card center">
        <div class="spinner"></div>
        <p>กำลังเตรียมคำถาม...</p>
      </section>
    } @else if (fetchError()) {
      <section class="card center">
        <h3>เกิดข้อผิดพลาด</h3>
        <p class="muted">{{ fetchError() }}</p>
        <button class="btn" (click)="goHome()">กลับหน้าแรก</button>
      </section>
    } @else {
      <section class="card shell">
        <!-- Header -->
        <header class="intro">
          <div class="badge">🧠 MBTI Interview</div>
          <h2>ตอบคำถาม {{ questions().length }} ข้อด้วยคำพูดของคุณเอง</h2>
          <p class="sub">
            เขียนคำตอบอย่างเปิดใจ เป็นภาษาไทยหรือภาษาอังกฤษก็ได้
            — ยิ่งละเอียดและตรงไปตรงมา การวิเคราะห์ยิ่งแม่นขึ้น
          </p>

          <div class="progress">
            <div class="bar">
              <div class="fill" [style.width.%]="progressPct()"></div>
            </div>
            <div class="progress-info">
              <span>ตอบแล้ว {{ filledCount() }} / {{ questions().length }}</span>
              <span class="saved" [class.dirty]="saveState() === 'dirty'">
                @switch (saveState()) {
                  @case ('saved') { ✓ บันทึกอัตโนมัติแล้ว }
                  @case ('dirty') { • ยังไม่ได้บันทึก }
                  @default { · }
                }
              </span>
            </div>
          </div>
        </header>

        <!-- Questions list -->
        <div class="qlist">
          @for (q of questions(); track q.id; let i = $index) {
            <article class="qcard" [class.filled]="answerOf(q.id).trim().length >= 10">
              <div class="qhead">
                <span class="qnum">{{ i + 1 }}</span>
                <span class="qdim" [attr.data-dim]="q.dimension">{{ dimLabel(q.dimension) }}</span>
              </div>
              <h4 class="qtext">{{ q.text }}</h4>
              @if (q.hint) {
                <p class="qhint">💡 {{ q.hint }}</p>
              }
              <textarea
                class="qinput"
                [ngModel]="answerOf(q.id)"
                (ngModelChange)="onChange(q.id, $event)"
                placeholder="พิมพ์คำตอบของคุณที่นี่... (ตอบยาวเท่าไหร่ก็ได้)"
                rows="4"
                [attr.aria-label]="'Answer for question ' + (i + 1)"
              ></textarea>
              <div class="qfoot">
                <span class="count">{{ answerOf(q.id).length }} ตัวอักษร</span>
                @if (answerOf(q.id).trim().length > 0 && answerOf(q.id).trim().length < 10) {
                  <span class="warn">คำตอบสั้นมาก — LLM อาจวิเคราะห์ได้ไม่ละเอียด</span>
                }
              </div>
            </article>
          }
        </div>

        <!-- Actions -->
        <div class="actions">
          <button class="btn-ghost" (click)="askClear()" [disabled]="submitting()">
            🗑️ ล้างคำตอบทั้งหมด
          </button>
          <button
            class="btn-primary"
            (click)="askSubmit()"
            [disabled]="!canSubmit() || submitting()"
          >
            @if (submitting()) {
              <span class="spinner-inline"></span> กำลังวิเคราะห์...
            } @else {
              ✨ ส่งคำตอบให้ AI วิเคราะห์
            }
          </button>
        </div>

        @if (submitting()) {
          <p class="submitting-note">
            AI กำลังสวมบทนักจิตวิทยาอ่านและตีความคำตอบของคุณอย่างละเอียด<br>
            ขั้นตอนนี้อาจใช้เวลา <strong>30-90 วินาที</strong> — โปรดอย่าปิดหน้านี้
          </p>
        }

        @if (submitError()) {
          <div class="err" role="alert">
            ⚠️ {{ submitError() }}
          </div>
        }

        <p class="privacy">🔒 คำตอบของคุณถูกเก็บไว้ในเบราว์เซอร์ (localStorage) จนกว่าจะส่งหรือล้าง</p>
      </section>
    }

    <!-- Confirm dialogs -->
    @if (showClearDialog()) {
      <app-confirm-dialog
        title="ล้างคำตอบทั้งหมด?"
        message="คำตอบทั้งหมดจะถูกลบออกจากเบราว์เซอร์ และการกระทำนี้ย้อนกลับไม่ได้"
        confirmLabel="ล้างทั้งหมด"
        cancelLabel="ยกเลิก"
        variant="danger"
        (confirm)="onClearConfirmed()"
        (cancel)="showClearDialog.set(false)"
      />
    }

    @if (showSubmitDialog()) {
      <app-confirm-dialog
        title="ส่งคำตอบเพื่อวิเคราะห์?"
        [message]="submitDialogMessage()"
        confirmLabel="ส่งให้ AI วิเคราะห์"
        cancelLabel="ยังไม่ส่ง"
        [busy]="submitting()"
        (confirm)="onSubmitConfirmed()"
        (cancel)="onSubmitDialogCancel()"
      />
    }
  `,
  styles: [`
    .shell { max-width: 880px; width: 100%; padding: 32px; }
    .center { text-align: center; padding: 80px 32px; max-width: 520px; width: 100%; }

    .intro { margin-bottom: 28px; text-align: center; }
    .badge {
      display: inline-block;
      padding: 6px 14px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 600;
      letter-spacing: 0.3px;
      margin-bottom: 12px;
    }
    .intro h2 {
      font-size: 1.55rem;
      margin-bottom: 10px;
      color: var(--text);
    }
    .sub {
      color: var(--text-muted);
      line-height: 1.65;
      max-width: 640px;
      margin: 0 auto;
    }

    .progress {
      margin-top: 22px;
      max-width: 520px;
      margin-left: auto; margin-right: auto;
    }
    .bar {
      height: 10px;
      background: #eef2ff;
      border-radius: 999px;
      overflow: hidden;
      margin-bottom: 6px;
    }
    .fill {
      height: 100%;
      background: linear-gradient(90deg, var(--primary), var(--accent));
      border-radius: 999px;
      transition: width 0.4s ease;
    }
    .progress-info {
      display: flex; justify-content: space-between;
      font-size: 0.82rem; color: var(--text-muted);
    }
    .saved.dirty { color: #d97706; }

    .qlist {
      display: flex; flex-direction: column; gap: 16px;
      margin-bottom: 28px;
    }

    .qcard {
      background: #fafafa;
      border: 2px solid #eef0f5;
      border-radius: 16px;
      padding: 20px;
      transition: border-color 0.2s ease, background 0.2s ease, transform 0.18s ease;
    }
    .qcard:focus-within {
      border-color: var(--primary);
      background: white;
      box-shadow: 0 8px 24px rgba(99,102,241,0.12);
      transform: translateY(-1px);
    }
    .qcard.filled {
      border-color: #d1fae5;
      background: linear-gradient(180deg, #f0fdf4, #ffffff 60%);
    }
    .qcard.filled:focus-within {
      border-color: var(--primary);
    }

    .qhead {
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 10px;
    }
    .qnum {
      width: 30px; height: 30px; flex-shrink: 0;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-weight: 700;
      font-size: 0.92rem;
    }
    .qdim {
      font-size: 0.72rem;
      padding: 3px 10px;
      border-radius: 999px;
      font-weight: 600;
      letter-spacing: 0.4px;
    }
    .qdim[data-dim="EI"] { background: #fce7f3; color: #be185d; }
    .qdim[data-dim="SN"] { background: #dbeafe; color: #1d4ed8; }
    .qdim[data-dim="TF"] { background: #fef3c7; color: #a16207; }
    .qdim[data-dim="JP"] { background: #dcfce7; color: #166534; }
    .qdim[data-dim="MIX"] { background: #e0e7ff; color: #4338ca; }

    .qtext {
      font-size: 1.04rem;
      line-height: 1.55;
      color: var(--text);
      margin-bottom: 8px;
      font-weight: 500;
    }
    .qhint {
      font-size: 0.85rem;
      color: var(--text-muted);
      background: #fffbeb;
      padding: 8px 12px;
      border-radius: 8px;
      border-left: 3px solid #fbbf24;
      margin-bottom: 12px;
      line-height: 1.5;
    }

    .qinput {
      width: 100%;
      min-height: 100px;
      padding: 12px 14px;
      border: 1.5px solid #e5e7eb;
      border-radius: 12px;
      font-family: inherit;
      font-size: 0.98rem;
      line-height: 1.55;
      resize: vertical;
      transition: border-color 0.18s ease, box-shadow 0.18s ease;
      background: white;
      color: var(--text);
    }
    .qinput:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
    }
    .qinput::placeholder { color: #9ca3af; }

    .qfoot {
      display: flex; justify-content: space-between; align-items: center;
      margin-top: 6px;
      font-size: 0.78rem;
      color: var(--text-muted);
    }
    .qfoot .warn { color: #d97706; }

    .actions {
      display: flex; gap: 12px; flex-wrap: wrap;
      justify-content: space-between;
      padding-top: 12px;
      border-top: 1px solid var(--border);
      margin-top: 8px;
    }
    .btn-ghost {
      padding: 12px 20px;
      border-radius: 12px;
      background: transparent;
      color: #ef4444;
      border: 1.5px solid #fecaca;
      font-size: 0.95rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.18s ease;
    }
    .btn-ghost:hover:not(:disabled) {
      background: #fef2f2;
      border-color: #ef4444;
    }
    .btn-primary {
      flex: 1; min-width: 220px;
      padding: 14px 28px;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      font-size: 1.02rem;
      font-weight: 600;
      border: none;
      cursor: pointer;
      box-shadow: 0 8px 22px rgba(99,102,241,0.35);
      transition: all 0.2s ease;
      display: inline-flex; align-items: center; justify-content: center; gap: 10px;
    }
    .btn-primary:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 12px 28px rgba(99,102,241,0.45);
    }
    .btn-primary:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }

    .spinner-inline {
      width: 18px; height: 18px;
      border: 2.5px solid rgba(255,255,255,0.4);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    .spinner {
      width: 48px; height: 48px;
      border: 4px solid #e5e7eb; border-top-color: var(--primary);
      border-radius: 50%;
      margin: 0 auto 16px;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .submitting-note {
      text-align: center;
      color: var(--text-muted);
      font-size: 0.9rem;
      margin-top: 18px;
      line-height: 1.7;
      padding: 16px;
      background: #fef3c7;
      border-radius: 12px;
      border: 1px solid #fde68a;
    }

    .err {
      background: #fee2e2;
      color: #991b1b;
      padding: 14px 16px;
      border-radius: 10px;
      margin-top: 18px;
      font-size: 0.92rem;
      border-left: 3px solid #ef4444;
    }

    .privacy {
      text-align: center;
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 24px;
    }

    .muted { color: var(--text-muted); margin-bottom: 20px; }
  `],
})
export class QuestionnaireComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private chat = inject(ChatService);

  sessionId = '';
  questions = signal<Question[]>([]);
  answers = signal<Record<number, string>>({});
  loading = signal(true);
  fetchError = signal<string | null>(null);
  submitting = signal(false);
  submitError = signal<string | null>(null);
  saveState = signal<'idle' | 'dirty' | 'saved'>('idle');

  showClearDialog = signal(false);
  showSubmitDialog = signal(false);

  filledCount = computed(() => {
    const a = this.answers();
    return Object.values(a).filter((v) => v.trim().length > 0).length;
  });
  progressPct = computed(() => {
    const total = this.questions().length || 1;
    return Math.round((this.filledCount() / total) * 100);
  });
  canSubmit = computed(() => {
    const total = this.questions().length;
    return total > 0 && this.filledCount() === total;
  });

  submitDialogMessage = computed(() => {
    const filled = this.filledCount();
    const total = this.questions().length;
    const short = Object.values(this.answers()).filter(
      (v) => v.trim().length > 0 && v.trim().length < 10,
    ).length;
    const lines = [
      `คุณตอบครบ ${filled}/${total} ข้อ`,
      short > 0 ? `⚠️ มี ${short} ข้อที่คำตอบสั้นกว่า 10 ตัวอักษร` : '',
      '',
      'AI จะสวมบทนักจิตวิทยาวิเคราะห์อย่างละเอียด',
      'การวิเคราะห์ใช้เวลาประมาณ 30-90 วินาที',
    ].filter(Boolean);
    return lines.join('\n');
  });

  private saveTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    if (!this.sessionId) {
      this.router.navigate(['/']);
      return;
    }

    // Try sessionStorage cache first (set by home on /session/start)
    const cached = sessionStorage.getItem(SS_PREFIX + this.sessionId);
    if (cached) {
      try {
        const qs = JSON.parse(cached) as Question[];
        this.questions.set(qs);
        this.loadAnswers();
        this.loading.set(false);
        return;
      } catch {
        /* fall-through */
      }
    }
    // No cache → go back home (user needs to start a fresh session)
    this.fetchError.set('ไม่พบคำถาม กรุณาเริ่มทำแบบทดสอบใหม่');
    this.loading.set(false);
  }

  ngOnDestroy() {
    if (this.saveTimer) clearTimeout(this.saveTimer);
  }

  // ---------- Input + persistence ----------

  onChange(qid: number, value: string) {
    this.answers.update((a) => ({ ...a, [qid]: value }));
    this.saveState.set('dirty');
    this.debouncedSave();
  }

  private debouncedSave() {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => {
      localStorage.setItem(LS_PREFIX + this.sessionId, JSON.stringify(this.answers()));
      this.saveState.set('saved');
    }, 400);
  }

  private loadAnswers() {
    const raw = localStorage.getItem(LS_PREFIX + this.sessionId);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as Record<number, string>;
      this.answers.set(parsed);
      this.saveState.set('saved');
    } catch {
      /* ignore corrupt cache */
    }
  }

  // ---------- Dialog triggers ----------

  askClear() {
    this.showClearDialog.set(true);
  }
  onClearConfirmed() {
    this.answers.set({});
    localStorage.removeItem(LS_PREFIX + this.sessionId);
    this.saveState.set('idle');
    this.showClearDialog.set(false);
    this.submitError.set(null);
  }

  askSubmit() {
    if (!this.canSubmit()) return;
    this.submitError.set(null);
    this.showSubmitDialog.set(true);
  }
  onSubmitDialogCancel() {
    if (this.submitting()) return; // don't allow cancel while in-flight
    this.showSubmitDialog.set(false);
  }

  onSubmitConfirmed() {
    if (this.submitting() || !this.canSubmit()) return;
    this.submitting.set(true);
    this.submitError.set(null);

    const payload: AnalyzeAnswer[] = this.questions().map((q) => ({
      question_id: q.id,
      text: (this.answers()[q.id] ?? '').trim(),
    }));

    this.chat.analyze(this.sessionId, payload).subscribe({
      next: () => {
        // Keep localStorage cleared after successful submit
        localStorage.removeItem(LS_PREFIX + this.sessionId);
        this.submitting.set(false);
        this.showSubmitDialog.set(false);
        this.router.navigate(['/result', this.sessionId]);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err?.error?.error || err?.message || 'ส่งไม่สำเร็จ — ตรวจสอบว่า AI service และ Ollama ทำงานอยู่';
        this.submitError.set(msg);
        console.error('analyze error', err);
      },
    });
  }

  // ---------- UI helpers ----------

  /** Safely read the current answer for a question id (always returns a string). */
  answerOf(qid: number): string {
    return this.answers()[qid] ?? '';
  }

  dimLabel(d: Question['dimension']) {
    return (
      {
        EI: 'Energy · E/I',
        SN: 'Information · S/N',
        TF: 'Decision · T/F',
        JP: 'Lifestyle · J/P',
        MIX: 'Overall',
      }[d] ?? d
    );
  }

  goHome() {
    this.router.navigate(['/']);
  }
}
