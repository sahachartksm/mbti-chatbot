import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  template: `
    <div class="overlay" (click)="onCancel()" [@.disabled]="false">
      <div class="dialog" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <div class="icon" [class.danger]="variant === 'danger'">
          {{ variant === 'danger' ? '⚠️' : '❓' }}
        </div>
        <h3>{{ title }}</h3>
        <p>{{ message }}</p>
        <div class="actions">
          <button class="btn-cancel" (click)="onCancel()">{{ cancelLabel }}</button>
          <button
            class="btn-confirm"
            [class.danger]="variant === 'danger'"
            (click)="onConfirm()"
            [disabled]="busy"
          >
            @if (busy) {
              <span class="dots">กำลังดำเนินการ</span>
            } @else {
              {{ confirmLabel }}
            }
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .overlay {
      position: fixed; inset: 0;
      background: rgba(15, 23, 42, 0.55);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
      display: flex; align-items: center; justify-content: center;
      z-index: 1000;
      padding: 20px;
      animation: fadeIn 0.18s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .dialog {
      background: white;
      border-radius: 20px;
      max-width: 420px; width: 100%;
      padding: 28px 28px 24px;
      box-shadow: 0 25px 60px rgba(0,0,0,0.35);
      text-align: center;
      animation: pop 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    @keyframes pop {
      from { opacity: 0; transform: translateY(20px) scale(0.95); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .icon {
      font-size: 2.6rem;
      line-height: 1;
      margin-bottom: 12px;
    }
    .icon.danger { filter: drop-shadow(0 4px 10px rgba(239,68,68,0.35)); }
    h3 {
      font-size: 1.25rem;
      margin-bottom: 8px;
      color: var(--text);
    }
    p {
      color: var(--text-muted);
      font-size: 0.95rem;
      line-height: 1.6;
      margin-bottom: 22px;
      white-space: pre-line;
    }
    .actions {
      display: flex; gap: 10px; justify-content: center;
    }
    .actions button {
      flex: 1; min-width: 110px;
      padding: 12px 18px;
      border-radius: 12px;
      font-size: 0.98rem;
      font-weight: 500;
      border: none;
      cursor: pointer;
      transition: all 0.18s ease;
    }
    .btn-cancel {
      background: #f1f5f9; color: var(--text);
    }
    .btn-cancel:hover { background: #e2e8f0; }
    .btn-confirm {
      background: var(--primary); color: white;
      box-shadow: 0 4px 12px rgba(99,102,241,0.35);
    }
    .btn-confirm:hover:not(:disabled) {
      background: var(--primary-dark);
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(99,102,241,0.45);
    }
    .btn-confirm.danger {
      background: #ef4444;
      box-shadow: 0 4px 12px rgba(239,68,68,0.35);
    }
    .btn-confirm.danger:hover:not(:disabled) {
      background: #dc2626;
      box-shadow: 0 6px 18px rgba(239,68,68,0.45);
    }
    .btn-confirm:disabled { opacity: 0.7; cursor: wait; }
    .dots::after {
      content: "…";
      animation: dots 1.2s infinite steps(4, end);
      display: inline-block;
      width: 1.2em; text-align: left;
    }
    @keyframes dots {
      0%, 20% { content: "…"; }
      40% { content: "."; }
      60% { content: ".."; }
      80%, 100% { content: "..."; }
    }
  `],
})
export class ConfirmDialogComponent {
  @Input() title = 'ยืนยันการทำรายการ';
  @Input() message = '';
  @Input() confirmLabel = 'ยืนยัน';
  @Input() cancelLabel = 'ยกเลิก';
  @Input() variant: 'default' | 'danger' = 'default';
  @Input() busy = false;

  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  onConfirm() {
    if (this.busy) return;
    this.confirm.emit();
  }
  onCancel() {
    if (this.busy) return;
    this.cancel.emit();
  }
}
