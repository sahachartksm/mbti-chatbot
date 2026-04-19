/**
 * MBTI group colors (16personalities-inspired palette).
 *
 * Groups:
 *   Analysts (NT)   → purple
 *   Diplomats (NF)  → emerald green
 *   Sentinels (SJ)  → blue (ISFJ/ISTJ/ESFJ/ESTJ)
 *   Explorers (SP)  → amber / warm yellow
 */

export type MbtiGroup = 'analyst' | 'diplomat' | 'sentinel' | 'explorer';

export interface MbtiTheme {
  group: MbtiGroup;
  name: string;       // Thai label
  primary: string;    // main solid color
  primaryDark: string;
  accent: string;
  bgFrom: string;     // page background gradient start
  bgTo: string;       // page background gradient end
  cardTint: string;   // subtle tint for info blocks
  badgeText: string;  // readable text color on primary
}

const ANALYST: MbtiTheme = {
  group: 'analyst',
  name: 'Analysts (นักวิเคราะห์)',
  primary: '#88619a',
  primaryDark: '#6a4880',
  accent: '#b48ecb',
  bgFrom: '#4a2d5f',
  bgTo: '#8b5fa8',
  cardTint: 'rgba(180,142,203,0.12)',
  badgeText: '#ffffff',
};

const DIPLOMAT: MbtiTheme = {
  group: 'diplomat',
  name: 'Diplomats (นักการทูต)',
  primary: '#33a474',
  primaryDark: '#218057',
  accent: '#6bc99a',
  bgFrom: '#1a5f48',
  bgTo: '#4ab489',
  cardTint: 'rgba(107,201,154,0.14)',
  badgeText: '#ffffff',
};

const SENTINEL: MbtiTheme = {
  group: 'sentinel',
  name: 'Sentinels (ผู้พิทักษ์)',
  primary: '#4298b5',
  primaryDark: '#2d7796',
  accent: '#72b9d0',
  bgFrom: '#1f5b79',
  bgTo: '#5ea8c4',
  cardTint: 'rgba(114,185,208,0.14)',
  badgeText: '#ffffff',
};

const EXPLORER: MbtiTheme = {
  group: 'explorer',
  name: 'Explorers (นักสำรวจ)',
  primary: '#e4ae3a',
  primaryDark: '#b8881d',
  accent: '#f2c869',
  bgFrom: '#a7741a',
  bgTo: '#e8b947',
  cardTint: 'rgba(242,200,105,0.18)',
  badgeText: '#3b2a00',
};

const GROUP_MAP: Record<string, MbtiTheme> = {
  // Analysts (__NT_)
  INTJ: ANALYST, INTP: ANALYST, ENTJ: ANALYST, ENTP: ANALYST,
  // Diplomats (__NF_)
  INFJ: DIPLOMAT, INFP: DIPLOMAT, ENFJ: DIPLOMAT, ENFP: DIPLOMAT,
  // Sentinels (__S_J)
  ISTJ: SENTINEL, ISFJ: SENTINEL, ESTJ: SENTINEL, ESFJ: SENTINEL,
  // Explorers (__S_P)
  ISTP: EXPLORER, ISFP: EXPLORER, ESTP: EXPLORER, ESFP: EXPLORER,
};

export function getMbtiTheme(type: string): MbtiTheme {
  return GROUP_MAP[(type || '').toUpperCase()] ?? ANALYST;
}

/**
 * Apply theme as CSS variables on the <html> element.
 * Call from a component's ngOnInit/ngOnChanges once the MBTI type is known.
 */
export function applyMbtiTheme(type: string): MbtiTheme {
  const theme = getMbtiTheme(type);
  const root = document.documentElement;
  root.style.setProperty('--mbti-primary', theme.primary);
  root.style.setProperty('--mbti-primary-dark', theme.primaryDark);
  root.style.setProperty('--mbti-accent', theme.accent);
  root.style.setProperty('--mbti-bg-from', theme.bgFrom);
  root.style.setProperty('--mbti-bg-to', theme.bgTo);
  root.style.setProperty('--mbti-card-tint', theme.cardTint);
  root.style.setProperty('--mbti-badge-text', theme.badgeText);
  root.setAttribute('data-mbti-group', theme.group);
  return theme;
}

export function resetMbtiTheme() {
  const root = document.documentElement;
  for (const prop of [
    '--mbti-primary',
    '--mbti-primary-dark',
    '--mbti-accent',
    '--mbti-bg-from',
    '--mbti-bg-to',
    '--mbti-card-tint',
    '--mbti-badge-text',
  ]) {
    root.style.removeProperty(prop);
  }
  root.removeAttribute('data-mbti-group');
}
