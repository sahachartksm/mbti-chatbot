import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ChatService } from '../../services/chat.service';
import { resetMbtiTheme } from '../../services/mbti-colors';

@Component({
  selector: 'app-home',
  standalone: true,
  template: `
    <section class="card home">
      <div class="hero">
        <div class="emoji">🧠✨</div>
        <h2>ค้นพบ MBTI ของคุณ<br>ด้วยการสัมภาษณ์เชิงลึก</h2>
        <p class="sub">
          AI จะสวมบท <strong>นักจิตวิทยาขั้นสูง</strong> อ่านคำตอบของคุณ
          แล้ววิเคราะห์ทั้ง 4 มิติของบุคลิกภาพอย่างตรงไปตรงมา
        </p>
      </div>

      <div class="flow-steps">
        <div class="step">
          <div class="step-num">1</div>
          <div>
            <div class="step-title">ตอบคำถามปลายเปิด 10 ข้อ</div>
            <div class="step-sub">ภาษาไทยหรืออังกฤษก็ได้ ยิ่งละเอียดยิ่งดี</div>
          </div>
        </div>
        <div class="step">
          <div class="step-num">2</div>
          <div>
            <div class="step-title">บันทึกอัตโนมัติในเบราว์เซอร์</div>
            <div class="step-sub">คำตอบจะไม่หาย จนกว่าจะส่งหรือล้าง</div>
          </div>
        </div>
        <div class="step">
          <div class="step-num">3</div>
          <div>
            <div class="step-title">AI วิเคราะห์อย่างละเอียด</div>
            <div class="step-sub">ใช้เวลา 30-90 วินาที พร้อมเหตุผลเชิงลึก</div>
          </div>
        </div>
      </div>

      <div class="dims">
        <div class="dim"><b>E</b>/<b>I</b><span>พลังงาน</span></div>
        <div class="dim"><b>S</b>/<b>N</b><span>การรับข้อมูล</span></div>
        <div class="dim"><b>T</b>/<b>F</b><span>การตัดสินใจ</span></div>
        <div class="dim"><b>J</b>/<b>P</b><span>ไลฟ์สไตล์</span></div>
      </div>

      @if (error()) {
        <div class="err">⚠️ {{ error() }}</div>
      }

      <button class="btn-cta" (click)="start()" [disabled]="loading()">
        @if (loading()) {
          <span class="dot-pulse"></span> กำลังเริ่ม...
        } @else {
          🚀 เริ่มทำแบบทดสอบ
        }
      </button>

      <small class="hint">
        🔒 ข้อมูลเก็บในเบราว์เซอร์เท่านั้น · ใช้เพื่อเรียนรู้ตัวเอง
      </small>
    </section>
  `,
  styles: [`
    .home { max-width: 620px; width: 100%; text-align: center; padding: 40px 32px 36px; }

    .hero { margin-bottom: 28px; }
    .emoji { font-size: 2.6rem; margin-bottom: 10px; }
    h2 {
      font-size: 1.7rem;
      line-height: 1.35;
      margin-bottom: 12px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      -webkit-background-clip: text; background-clip: text;
      color: transparent;
      font-weight: 700;
    }
    .sub {
      color: var(--text-muted);
      line-height: 1.65;
      font-size: 1rem;
      max-width: 500px;
      margin: 0 auto;
    }
    .sub strong { color: var(--primary); font-weight: 600; }

    .flow-steps {
      display: flex; flex-direction: column; gap: 12px;
      margin: 28px 0;
      text-align: left;
    }
    .step {
      display: flex; align-items: center; gap: 14px;
      padding: 12px 16px;
      background: #fafbff;
      border-radius: 12px;
      border: 1px solid #eef2ff;
    }
    .step-num {
      width: 32px; height: 32px; flex-shrink: 0;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-weight: 700;
    }
    .step-title { font-size: 0.97rem; font-weight: 500; color: var(--text); }
    .step-sub { font-size: 0.82rem; color: var(--text-muted); margin-top: 2px; }

    .dims {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
      margin-bottom: 24px;
    }
    .dim {
      padding: 12px 8px;
      background: linear-gradient(135deg, #fef3f2, #f0f9ff);
      border-radius: 10px;
      font-size: 0.78rem;
      color: var(--text-muted);
      text-align: center;
    }
    .dim b { color: var(--primary); font-size: 1.05rem; margin: 0 2px; }
    .dim span { display: block; margin-top: 2px; }

    .btn-cta {
      width: 100%;
      padding: 16px 28px;
      border-radius: 14px;
      font-size: 1.08rem;
      font-weight: 600;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      border: none;
      cursor: pointer;
      box-shadow: 0 10px 28px rgba(99,102,241,0.38);
      transition: all 0.2s ease;
      display: inline-flex; align-items: center; justify-content: center; gap: 10px;
    }
    .btn-cta:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 14px 34px rgba(99,102,241,0.48);
    }
    .btn-cta:disabled { opacity: 0.6; cursor: not-allowed; }

    .dot-pulse {
      width: 14px; height: 14px;
      border: 2.5px solid rgba(255,255,255,0.4);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .hint {
      display: block;
      margin-top: 18px;
      color: var(--text-muted);
      font-size: 0.8rem;
    }
    .err {
      background: #fee2e2; color: #991b1b;
      padding: 12px 16px; border-radius: 10px;
      margin-bottom: 18px;
      font-size: 0.9rem;
      border-left: 3px solid #ef4444;
    }

    @media (max-width: 480px) {
      .dims { grid-template-columns: repeat(2, 1fr); }
    }
  `],
})
export class HomeComponent implements OnInit {
  private chat = inject(ChatService);
  private router = inject(Router);

  loading = signal(false);
  error = signal<string | null>(null);

  ngOnInit() {
    // Clear any MBTI theme left over from a previous result page.
    resetMbtiTheme();
  }

  start() {
    this.loading.set(true);
    this.error.set(null);
    this.chat.start('th').subscribe({
      next: (res) => {
        // cache questions so the questionnaire page can render without re-fetching
        sessionStorage.setItem(`mbti_questions_${res.session_id}`, JSON.stringify(res.questions));
        this.router.navigate(['/questionnaire', res.session_id]);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set('ไม่สามารถเชื่อมต่อ backend ได้ — โปรดตรวจสอบว่าเปิด server แล้ว (ดู docs/10-llm-ollama-setup.md)');
        console.error(err);
      },
    });
  }
}
