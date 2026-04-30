'use client';
import { create } from 'zustand';

export const useAppStore = create((set) => ({
  theme: 'light',
  token: '',
  user: null,
  repos: [],
  selectedRepo: null,
  history: [],
  settings: {
    length: 'Medium',
    style: 'Technical',
    includeSections: { features: true, architecture: true, bestPractices: true, competitive: true },
    tone: 20,
  },
  setTheme: (theme) => set({ theme }),
  setToken: (token) => set({ token }),
  setUser: (user) => set({ user }),
  setRepos: (repos) => set({ repos }),
  setSelectedRepo: (repo) => set({ selectedRepo: repo }),
  setSettings: (settings) => set((s) => ({ settings: { ...s.settings, ...settings } })),
  addHistory: (entry) => set((s) => ({ history: [entry, ...s.history].slice(0, 20) })),
}));
