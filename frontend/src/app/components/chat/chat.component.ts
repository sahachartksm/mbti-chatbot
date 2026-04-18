import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Question } from '../../services/chat.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  template: `
    <section class="card chat">
      @if (loading()) {
        <div class="loading">กำลังโหลด...</div>
      } @else if (currentQuestion()) {
        <div class="progress-bar">
          <div class="progress-fill" [style.width.%]="progress()"></div>
        </div>
        <div class="progress-text">
          ข้อ {{ index() + 1 }} / {{ total() }}
        </div>

        <div class="bubble">
          <div class="avatar">🤖</div>
          <div class="text">{{ currentQuestion()!.text }}</div>
        </div>

        <div class="choices">
          @for (choice of currentQuestion()!.choices; track choice.id) {
            <button
              class="choice-btn"
              [class.selected]="selectedChoice() === choice.id"
              (click)="selectChoice(choice.id)"
              [disabled]="submitting()"
            >
              <span class="letter">{{ choice.id.toUpperCase() }}</span>
              <span>{{ choice.text }}</span>
            </button>
          }
        </div>

        <div class="actions">
          <button class="btn-secondary" (click)="prev()" [disabled]="index() === 0">
            ← ก่อนหน้า
          </button>
          <button class="btn" (click)="next()" [disabled]="!selectedChoice() || submitting()">
            @if (index() === total() - 1) { ดูผลลัพธ์ } @else { ถัดไป → }
          </button>
        </div>
      } @else if (error()) {
        <div class="err">{{ error() }}</div>
        <button class="btn" (click)="goHome()">กลับหน้าแรก</button>
      }
    </section>
  `,
  styles: [`
    .chat { max-width: 680px; width: 100%; }
    .loading { text-align: center; padding: 60px 0; color: var(--text-muted); }

    .progress-bar {
      height: 8px; background: #e5e7eb; border-radius: 4px;
      overflow: hidden; margin-bottom: 6px;
    }
    .progress-fill {
      height: 100%; background: linear-gradient(90deg, var(--primary), var(--accent));
      transition: width 0.3s ease;
    }
    .progress-text {
      text-align: right; font-size: 0.85rem; color: var(--text-muted);
      margin-bottom: 24px;
    }

    .bubble {
      display: flex; gap: 12px; margin-bottom: 24px;
      background: #f9fafb; padding: 18px; border-radius: 14px;
    }
    .avatar {
      width: 44px; height: 44px; background: var(--primary);
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      font-size: 1.3rem; flex-shrink: 0;
    }
    .text { font-size: 1.1rem; line-height: 1.5; padding-top: 6px; }

    .choices { display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; }
    .choice-btn {
      display: flex; align-items: center; gap: 14px;
      padding: 14px 18px; border-radius: 12px;
      background: white; border: 2px solid var(--border);
      text-align: left; font-size: 1rem;
    }
    .choice-btn:hover:not(:disabled) { border-color: var(--primary); background: #f9fafb; }
    .choice-btn.selected {
      border-color: var(--primary); background: #eef2ff;
      box-shadow: 0 0 0 3px rgba(99,102,241,0.2);
    }
    .letter {
      width: 32px; height: 32px; border-radius: 50%;
      background: var(--primary); color: white;
      display: flex; align-items: center; justify-content: center;
      font-weight: 600; flex-shrink: 0;
    }

    .actions { display: flex; justify-content: space-between; gap: 12px; }
    .actions button { flex: 1; padding: 12px; }
    .err {
      background: #fee2e2; color: #991b1b; padding: 16px;
      border-radius: 8px; margin-bottom: 16px;
    }
  `],
})
export class ChatComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private chat = inject(ChatService);

  sessionId = '';
  questions = signal<Question[]>([]);
  index = signal(0);
  selectedChoice = signal<string | null>(null);
  answers = signal<Record<number, string>>({});

  loading = signal(true);
  submitting = signal(false);
  error = signal<string | null>(null);

  currentQuestion = computed(() => this.questions()[this.index()] ?? null);
  total = computed(() => this.questions().length);
  progress = computed(() => {
    const t = this.total();
    return t ? ((this.index() + 1) / t) * 100 : 0;
  });

  ngOnInit() {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    const cached = sessionStorage.getItem(`questions_${this.sessionId}`);
    if (cached) {
      this.questions.set(JSON.parse(cached));
      this.loading.set(false);
    } else {
      // no cache — go home
      this.router.navigate(['/']);
    }
  }

  selectChoice(choiceId: string) {
    this.selectedChoice.set(choiceId);
  }

  async next() {
    const q = this.currentQuestion();
    const choice = this.selectedChoice();
    if (!q || !choice) return;

    this.submitting.set(true);
    this.chat.answer(this.sessionId, q.id, choice).subscribe({
      next: () => {
        const all = { ...this.answers(), [q.id]: choice };
        this.answers.set(all);
        this.submitting.set(false);

        if (this.index() === this.total() - 1) {
          // last question → go to result
          this.router.navigate(['/result', this.sessionId]);
        } else {
          this.index.update((i) => i + 1);
          const prevAns = all[this.questions()[this.index()].id];
          this.selectedChoice.set(prevAns ?? null);
        }
      },
      error: (err) => {
        this.submitting.set(false);
        this.error.set('บันทึกคำตอบไม่สำเร็จ กรุณาลองใหม่');
        console.error(err);
      },
    });
  }

  prev() {
    if (this.index() === 0) return;
    this.index.update((i) => i - 1);
    const prevAns = this.answers()[this.questions()[this.index()].id];
    this.selectedChoice.set(prevAns ?? null);
  }

  goHome() {
    this.router.navigate(['/']);
  }
}
