import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./components/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'questionnaire/:sessionId',
    loadComponent: () =>
      import('./components/questionnaire/questionnaire.component').then(
        (m) => m.QuestionnaireComponent,
      ),
  },
  {
    path: 'result/:sessionId',
    loadComponent: () =>
      import('./components/result/result.component').then((m) => m.ResultComponent),
  },
  { path: '**', redirectTo: '' },
];
