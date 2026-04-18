import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'chat/:sessionId',
    loadComponent: () => import('./components/chat/chat.component').then((m) => m.ChatComponent),
  },
  {
    path: 'result/:sessionId',
    loadComponent: () => import('./components/result/result.component').then((m) => m.ResultComponent),
  },
  { path: '**', redirectTo: '' },
];
