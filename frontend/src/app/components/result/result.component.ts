import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ChatService, Result } from '../../services/chat.service';

@Component({
  selector: 'app-result',
  standalone: true,
  imports: [FormsModule],
  template: `
    @if (loading()) {
      <section class="card center">
        <div class="spinner"></div>
        <p>กำลังวิเคราะห์บุคลิกภาพ...</p>
      </section>
    } @else if (error()) {
      <section class="card">
        <h3>เกิดข้อผิดพลาด</h3>
        <p class="err">{{ error() }}</p>
        <button class="btn" (click)="retry()">ลองอีกครั้ง</button>
        <button class="btn-secondary" (click)="goHome()" style="margin-left:8px">กลับหน้าแรก</button>
      </section>
    } @else {
      @if (result(); as r) {
      <section class="card result">
        <div class="type-hero">
          <div class="type-letter">{{ r.mbti_type }}</div>
          <h2>{{ r.nickname }}</h2>
          <p class="conf">ความมั่นใจ: {{ (r.confidence * 100).toFixed(0) }}%</p>
        </div>

        <p class="desc">{{ r.description }}</p>

        <!-- Dimension bars -->
        <div class="dims">
          <div class="dim-row">
            <span class="label">E</span>
            <div class="bar"><div class="fill e-side" [style.width.%]="r.dimensions.E"></div></div>
            <span class="label right">I</span>
            <span class="pct">{{ r.dimensions.E }}% / {{ r.dimensions.I }}%</span>
          </div>
          <div class="dim-row">
            <span class="label">S</span>
            <div class="bar"><div class="fill s-side" [style.width.%]="r.dimensions.S"></div></div>
            <span class="label right">N</span>
            <span class="pct">{{ r.dimensions.S }}% / {{ r.dimensions.N }}%</span>
          </div>
          <div class="dim-row">
            <span class="label">T</span>
            <div class="bar"><div class="fill t-side" [style.width.%]="r.dimensions.T"></div></div>
            <span class="label right">F</span>
            <span class="pct">{{ r.dimensions.T }}% / {{ r.dimensions.F }}%</span>
          </div>
          <div class="dim-row">
            <span class="label">J</span>
            <div class="bar"><div class="fill j-side" [style.width.%]="r.dimensions.J"></div></div>
            <span class="label right">P</span>
            <span class="pct">{{ r.dimensions.J }}% / {{ r.dimensions.P }}%</span>
          </div>
        </div>

        <div class="grid">
          <div class="block">
            <h4>💪 จุดแข็ง</h4>
            <ul>@for (s of r.strengths; track s) {<li>{{ s }}</li>}</ul>
          </div>
          <div class="block">
            <h4>⚠️ สิ่งที่ควรพัฒนา</h4>
            <ul>@for (w of r.weaknesses; track w) {<li>{{ w }}</li>}</ul>
          </div>
          <div class="block">
            <h4>💼 อาชีพที่เหมาะ</h4>
            <ul>@for (c of r.careers; track c) {<li>{{ c }}</li>}</ul>
          </div>
          <div class="block">
            <h4>🤝 เข้ากันได้ดีกับ</h4>
            <ul>@for (t of r.compatible_types; track t) {<li>{{ t }}</li>}</ul>
          </div>
        </div>

        @if (r.famous_people?.length) {
          <div class="famous">
            <h4>⭐ คนดังที่ถูกจัดว่าเป็น {{ r.mbti_type }}</h4>
            <p>{{ r.famous_people.join(' · ') }}</p>
          </div>
        }

        <div class="actions">
          <button class="btn" (click)="goHome()">ทำใหม่อีกครั้ง</button>
        </div>
      </section>
      }
    }
  `,
  styles: [`
    .center { text-align: center; padding: 80px 32px; }
    .spinner {
      width: 48px; height: 48px; border-radius: 50%;
      border: 4px solid #e5e7eb; border-top-color: var(--primary);
      margin: 0 auto 16px; animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .result { max-width: 780px; width: 100%; }
    .type-hero { text-align: center; padding: 24px 0; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
    .type-letter {
      font-size: 4rem; font-weight: 700;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      -webkit-background-clip: text; background-clip: text; color: transparent;
      letter-spacing: 2px;
    }
    .type-hero h2 { margin-top: 4px; font-size: 1.6rem; }
    .conf { color: var(--text-muted); margin-top: 4px; font-size: 0.9rem; }

    .desc { font-size: 1.1rem; line-height: 1.7; margin-bottom: 28px; padding: 0 8px; }

    .dims { display: flex; flex-direction: column; gap: 10px; margin-bottom: 28px; }
    .dim-row {
      display: grid; grid-template-columns: 28px 1fr 28px auto; gap: 10px;
      align-items: center;
    }
    .label { font-weight: 700; text-align: center; color: var(--primary); }
    .label.right { color: var(--accent); }
    .bar { height: 10px; background: #fce7f3; border-radius: 6px; overflow: hidden; }
    .fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
    .e-side, .s-side, .t-side, .j-side { background: var(--primary); }
    .pct { font-size: 0.8rem; color: var(--text-muted); min-width: 90px; text-align: right; }

    .grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }
    .block { background: #f9fafb; padding: 16px; border-radius: 12px; }
    .block h4 { margin-bottom: 10px; font-size: 1rem; }
    .block ul { list-style: none; padding: 0; }
    .block li { padding: 4px 0; color: var(--text); font-size: 0.95rem; }
    .block li::before { content: "· "; color: var(--primary); }

    .famous {
      background: linear-gradient(135deg, #fef3c7, #fde68a);
      padding: 16px; border-radius: 12px; margin-bottom: 24px;
    }
    .famous h4 { margin-bottom: 6px; }
    .famous p { font-size: 0.95rem; }

    .actions { text-align: center; }
    .actions .btn { min-width: 200px; padding: 14px; }
    .err { color: #991b1b; margin-bottom: 16px; }
  `],
})
export class ResultComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private chat = inject(ChatService);

  sessionId = '';
  result = signal<Result | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  ngOnInit() {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    this.analyze();
  }

  analyze() {
    this.loading.set(true);
    this.error.set(null);
    this.chat.analyze(this.sessionId).subscribe({
      next: (r) => {
        this.result.set(r);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        const msg = err?.error?.error || 'ไม่สามารถวิเคราะห์ได้';
        this.error.set(msg);
        console.error(err);
      },
    });
  }

  retry() {
    this.analyze();
  }

  goHome() {
    this.router.navigate(['/']);
  }
}
