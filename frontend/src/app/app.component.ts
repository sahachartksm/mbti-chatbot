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
        <p class="tagline">AI นักจิตวิทยา · วิเคราะห์บุคลิกภาพจากคำตอบของคุณเอง</p>
      </header>
      <router-outlet></router-outlet>
      <footer class="foot">
        Made with Angular · Go · Python · Ollama · MongoDB
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
      transition: background 0.6s ease;
    }
    .top { text-align: center; color: white; margin-bottom: 32px; }
    .brand {
      font-size: 2.2rem; font-weight: 700; letter-spacing: 0.5px;
      text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .tagline { opacity: 0.92; margin-top: 4px; font-size: 0.98rem; }
    .foot {
      margin-top: auto; padding-top: 32px;
      color: rgba(255,255,255,0.75);
      font-size: 0.82rem;
      letter-spacing: 0.3px;
    }
  `],
})
export class AppComponent {}
