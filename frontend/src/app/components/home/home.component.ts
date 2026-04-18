import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ChatService } from '../../services/chat.service';

@Component({
  selector: 'app-home',
  standalone: true,
  template: `
    <section class="card home">
      <h2>ทำแบบทดสอบ MBTI</h2>
      <p class="sub">
        ตอบคำถามสั้น ๆ <strong>20 ข้อ</strong> แล้วเราจะวิเคราะห์บุคลิกภาพของคุณจาก 16 types<br>
        ใช้เวลาประมาณ 3-5 นาที
      </p>

      <div class="dims">
        <div class="dim"><b>E</b> / I — พลังงาน</div>
        <div class="dim"><b>S</b> / N — ข้อมูล</div>
        <div class="dim"><b>T</b> / F — ตัดสินใจ</div>
        <div class="dim"><b>J</b> / P — ไลฟ์สไตล์</div>
      </div>

      @if (error()) {
        <div class="err">{{ error() }}</div>
      }

      <button class="btn" (click)="start()" [disabled]="loading()">
        @if (loading()) { กำลังเริ่ม... } @else { 🚀 เริ่มทำแบบทดสอบ }
      </button>

      <small class="hint">ไม่เก็บข้อมูลส่วนตัว · ใช้เพื่อเรียนรู้เท่านั้น</small>
    </section>
  `,
  styles: [`
    .home { max-width: 560px; width: 100%; text-align: center; }
    h2 { font-size: 1.6rem; margin-bottom: 12px; }
    .sub { color: var(--text-muted); margin-bottom: 24px; }
    .dims {
      display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;
      margin: 0 0 28px 0;
    }
    .dim {
      padding: 10px; background: #f3f4f6; border-radius: 8px;
      font-size: 0.9rem; color: var(--text-muted);
    }
    .dim b { color: var(--primary); }
    .btn { width: 100%; padding: 16px; font-size: 1.1rem; }
    .hint { display: block; margin-top: 16px; color: var(--text-muted); font-size: 0.8rem; }
    .err { background: #fee2e2; color: #991b1b; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
  `],
})
export class HomeComponent {
  private chat = inject(ChatService);
  private router = inject(Router);

  loading = signal(false);
  error = signal<string | null>(null);

  start() {
    this.loading.set(true);
    this.error.set(null);
    this.chat.start('th').subscribe({
      next: (res) => {
        // cache questions in sessionStorage to avoid re-fetch
        sessionStorage.setItem(`questions_${res.session_id}`, JSON.stringify(res.questions));
        this.router.navigate(['/chat', res.session_id]);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set('ไม่สามารถเชื่อมต่อ backend ได้ กรุณาตรวจสอบว่าเปิด server แล้ว (ดู README)');
        console.error(err);
      },
    });
  }
}
