import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <main class="shell">
      <header class="top">
        <h1 class="brand">🧠 MBTI Chatbot</h1>
        <p class="tagline">ค้นหาตัวตนของคุณใน 20 คำถาม</p>
      </header>
      <router-outlet></router-outlet>
      <footer class="foot">
        Made with Angular · Go · Python · MongoDB
      </footer>
    </main>
  `,
  styles: [`
    .shell {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px 16px;
    }
    .top { text-align: center; color: white; margin-bottom: 32px; }
    .brand { font-size: 2.2rem; font-weight: 700; letter-spacing: 0.5px; }
    .tagline { opacity: 0.9; margin-top: 4px; }
    .foot { margin-top: auto; padding-top: 32px; color: rgba(255,255,255,0.7); font-size: 0.85rem; }
  `],
})
export class AppComponent {}
