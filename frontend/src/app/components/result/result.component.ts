import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ChatService, Result } from '../../services/chat.service';
import { MbtiTheme, applyMbtiTheme, getMbtiTheme, resetMbtiTheme } from '../../services/mbti-colors';

@Component({
  selector: 'app-result',
  standalone: true,
  template: `
    @if (loading()) {
      <section class="card center">
        <div class="spinner"></div>
        <p>กำลังโหลดผลวิเคราะห์...</p>
      </section>
    } @else if (error()) {
      <section class="card center">
        <div class="err-icon">😕</div>
        <h3>ไม่สามารถโหลดผลได้</h3>
        <p class="err">{{ error() }}</p>
        <div class="err-actions">
          <button class="btn" (click)="retry()">ลองอีกครั้ง</button>
          <button class="btn-secondary" (click)="goHome()">กลับหน้าแรก</button>
        </div>
      </section>
    } @else if (result(); as r) {
      <section class="card result" [attr.data-mbti-group]="theme()?.group">
        <!-- Hero -->
        <div class="type-hero">
          <div class="hero-top">
            <span class="group-pill">{{ theme()?.name }}</span>
          </div>
          <div class="type-letter">{{ r.mbti_type }}</div>
          <h2>{{ r.nickname }}</h2>
          <p class="conf">
            🎯 ความมั่นใจในการวิเคราะห์: <strong>{{ (r.confidence * 100).toFixed(0) }}%</strong>
          </p>
        </div>

        <!-- Short description -->
        <p class="desc">{{ r.description }}</p>

        <!-- Dimension bars -->
        <div class="section-title">📊 สัดส่วนทั้ง 4 มิติ</div>
        <div class="dims">
          @for (d of dimRows(); track d.left) {
            <div class="dim-row">
              <span class="label" [class.strong]="d.leftVal >= d.rightVal">{{ d.left }}</span>
              <div class="bar">
                <div class="fill left" [style.width.%]="d.leftVal"></div>
                <div class="fill right" [style.width.%]="d.rightVal"></div>
              </div>
              <span class="label right" [class.strong]="d.rightVal > d.leftVal">{{ d.right }}</span>
              <span class="pct">
                <b>{{ d.leftVal }}%</b> · {{ d.rightVal }}%
              </span>
            </div>
          }
        </div>

        <!-- LLM deep analysis -->
        @if (r.analysis) {
          <div class="analysis">
            <div class="section-title">🧠 บทวิเคราะห์จากนักจิตวิทยา AI</div>
            <div class="analysis-body">
              @for (para of analysisParagraphs(); track $index) {
                <p>{{ para }}</p>
              }
            </div>
          </div>
        }

        <!-- Stat grid -->
        <div class="grid">
          <div class="block">
            <h4>💪 จุดแข็ง</h4>
            <ul>@for (s of r.strengths; track s) {<li>{{ s }}</li>}</ul>
          </div>
          <div class="block">
            <h4>⚠️ สิ่งที่ควรระวัง</h4>
            <ul>@for (w of r.weaknesses; track w) {<li>{{ w }}</li>}</ul>
          </div>
          <div class="block">
            <h4>💼 อาชีพที่เหมาะ</h4>
            <ul>@for (c of r.careers; track c) {<li>{{ c }}</li>}</ul>
          </div>
          <div class="block">
            <h4>🤝 เข้ากันได้ดีกับ</h4>
            <ul>
              @for (t of r.compatible_types; track t) {
                <li><span class="type-badge">{{ t }}</span></li>
              }
            </ul>
          </div>
        </div>

        @if (r.famous_people.length) {
          <div class="famous">
            <h4>⭐ คนดังที่ถูกจัดว่าเป็น {{ r.mbti_type }}</h4>
            <p>{{ r.famous_people.join(' · ') }}</p>
          </div>
        }

        <!-- Actions -->
        <div class="actions">
          <button class="btn-primary" (click)="goHome()">🔄 ทำใหม่อีกครั้ง</button>
        </div>

        <p class="footnote">
          ผลนี้ได้จาก AI LLM ในบทบาทนักจิตวิทยา · MBTI เป็นเครื่องมือช่วยทำความเข้าใจตัวเอง
          ไม่ใช่การวินิจฉัยทางจิตวิทยาทางการ
        </p>
      </section>
    }
  `,
  styles: [`
    :host {
      display: flex; justify-content: center; width: 100%;
    }

    .center { text-align: center; padding: 80px 32px; max-width: 520px; width: 100%; }
    .spinner {
      width: 52px; height: 52px; border-radius: 50%;
      border: 4px solid #e5e7eb;
      border-top-color: var(--mbti-primary, var(--primary));
      margin: 0 auto 20px;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .err-icon { font-size: 2.4rem; margin-bottom: 8px; }
    .err-actions { display: flex; justify-content: center; gap: 10px; margin-top: 18px; }
    .err { color: #991b1b; margin: 12px 0 0; padding: 12px 14px; background: #fee2e2; border-radius: 10px; }

    .result { max-width: 820px; width: 100%; }

    /* ---------- Hero ---------- */
    .type-hero {
      text-align: center;
      padding: 24px 0 28px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 28px;
      position: relative;
    }
    .hero-top {
      display: flex; justify-content: center;
      margin-bottom: 12px;
    }
    .group-pill {
      font-size: 0.78rem; letter-spacing: 0.5px; font-weight: 600;
      padding: 5px 14px;
      border-radius: 999px;
      background: var(--mbti-primary);
      color: var(--mbti-badge-text);
      box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .type-letter {
      font-size: 5rem;
      font-weight: 800;
      line-height: 1;
      margin-bottom: 6px;
      background: linear-gradient(135deg, var(--mbti-primary), var(--mbti-accent));
      -webkit-background-clip: text; background-clip: text; color: transparent;
      letter-spacing: 4px;
      filter: drop-shadow(0 6px 18px rgba(0,0,0,0.12));
    }
    .type-hero h2 { margin-top: 4px; font-size: 1.55rem; color: var(--text); }
    .conf { color: var(--text-muted); margin-top: 10px; font-size: 0.92rem; }
    .conf strong { color: var(--mbti-primary); }

    /* ---------- Short description ---------- */
    .desc {
      font-size: 1.05rem;
      line-height: 1.75;
      margin-bottom: 32px;
      padding: 0 8px;
      color: var(--text);
    }

    .section-title {
      font-size: 0.88rem;
      font-weight: 700;
      letter-spacing: 0.3px;
      color: var(--text);
      margin-bottom: 12px;
      display: flex; align-items: center; gap: 8px;
    }

    /* ---------- Dimensions ---------- */
    .dims {
      display: flex; flex-direction: column; gap: 14px;
      margin-bottom: 36px;
      background: var(--mbti-card-tint);
      padding: 18px;
      border-radius: 14px;
    }
    .dim-row {
      display: grid;
      grid-template-columns: 30px 1fr 30px auto;
      gap: 10px;
      align-items: center;
    }
    .label {
      font-weight: 600;
      font-size: 0.98rem;
      text-align: center;
      color: var(--text-muted);
      transition: color 0.25s ease, transform 0.25s ease;
    }
    .label.right { text-align: center; }
    .label.strong {
      color: var(--mbti-primary);
      transform: scale(1.15);
      font-weight: 800;
    }
    .bar {
      height: 12px;
      background: rgba(0,0,0,0.06);
      border-radius: 999px;
      overflow: hidden;
      display: flex;
    }
    .fill {
      height: 100%;
      transition: width 0.9s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .fill.left { background: linear-gradient(90deg, var(--mbti-primary), var(--mbti-accent)); }
    .fill.right { background: rgba(0,0,0,0.1); }
    .pct {
      font-size: 0.82rem;
      color: var(--text-muted);
      min-width: 90px;
      text-align: right;
    }
    .pct b { color: var(--mbti-primary); font-weight: 700; }

    /* ---------- Analysis ---------- */
    .analysis {
      margin-bottom: 32px;
      padding: 22px 24px;
      background: linear-gradient(135deg, var(--mbti-card-tint), rgba(255,255,255,0.6));
      border-left: 4px solid var(--mbti-primary);
      border-radius: 14px;
    }
    .analysis-body p {
      font-size: 0.97rem;
      line-height: 1.8;
      margin-bottom: 12px;
      color: var(--text);
    }
    .analysis-body p:last-child { margin-bottom: 0; }

    /* ---------- Grid blocks ---------- */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .block {
      background: #fafbfc;
      padding: 18px;
      border-radius: 14px;
      border: 1px solid #eef0f4;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .block:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 22px rgba(0,0,0,0.06);
    }
    .block h4 { margin-bottom: 12px; font-size: 1rem; color: var(--text); }
    .block ul { list-style: none; padding: 0; }
    .block li {
      padding: 5px 0;
      color: var(--text);
      font-size: 0.94rem;
      line-height: 1.55;
    }
    .block li::before { content: "· "; color: var(--mbti-primary); font-weight: 700; }
    .block li:has(.type-badge)::before { content: none; }

    .type-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 8px;
      background: var(--mbti-primary);
      color: var(--mbti-badge-text);
      font-weight: 600;
      font-size: 0.88rem;
      letter-spacing: 0.5px;
    }

    /* ---------- Famous ---------- */
    .famous {
      background: linear-gradient(135deg, #fef3c7, #fde68a);
      padding: 18px 20px;
      border-radius: 14px;
      margin-bottom: 26px;
    }
    .famous h4 { margin-bottom: 6px; color: #7c2d12; }
    .famous p { font-size: 0.95rem; color: #78350f; line-height: 1.6; }

    /* ---------- Actions ---------- */
    .actions { text-align: center; margin-bottom: 20px; }
    .btn-primary {
      min-width: 220px;
      padding: 14px 32px;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--mbti-primary), var(--mbti-accent));
      color: var(--mbti-badge-text);
      font-size: 1.02rem;
      font-weight: 600;
      border: none;
      cursor: pointer;
      box-shadow: 0 10px 26px rgba(0,0,0,0.2);
      transition: all 0.2s ease;
    }
    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 32px rgba(0,0,0,0.28);
    }

    .footnote {
      text-align: center;
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.6;
      padding: 0 12px;
    }
  `],
})
export class ResultComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private chat = inject(ChatService);

  sessionId = '';
  result = signal<Result | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  theme = computed<MbtiTheme | null>(() => {
    const r = this.result();
    return r ? getMbtiTheme(r.mbti_type) : null;
  });

  analysisParagraphs = computed<string[]>(() => {
    const raw = (this.result()?.analysis ?? '').trim();
    if (!raw) return [];
    // split on blank line OR fall back to sentence grouping
    const parts = raw.split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
    return parts.length > 0 ? parts : [raw];
  });

  dimRows = computed(() => {
    const r = this.result();
    if (!r) return [];
    const d = r.dimensions;
    return [
      { left: 'E', right: 'I', leftVal: d.E, rightVal: d.I },
      { left: 'S', right: 'N', leftVal: d.S, rightVal: d.N },
      { left: 'T', right: 'F', leftVal: d.T, rightVal: d.F },
      { left: 'J', right: 'P', leftVal: d.J, rightVal: d.P },
    ];
  });

  ngOnInit() {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    this.fetch();
  }

  ngOnDestroy() {
    resetMbtiTheme();
  }

  /**
   * Load previously-saved result. Analysis was triggered on the questionnaire page,
   * so here we just fetch what's stored in Mongo.
   */
  fetch() {
    this.loading.set(true);
    this.error.set(null);
    this.chat.getResult(this.sessionId).subscribe({
      next: (r) => {
        this.result.set(r);
        applyMbtiTheme(r.mbti_type);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        const msg = err?.error?.error || 'ไม่พบผลวิเคราะห์ — อาจถูกลบหรือ session หมดอายุ';
        this.error.set(msg);
        console.error(err);
      },
    });
  }

  retry() {
    this.fetch();
  }

  goHome() {
    resetMbtiTheme();
    this.router.navigate(['/']);
  }
}
