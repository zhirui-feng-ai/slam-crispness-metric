import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built site is portable (served from any sub-path via preview).
export default defineConfig({ base: './', plugins: [react()] })
