import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    include: ['tests/**/*.test.js'],
    coverage: {
      reporter: ['text', 'html'],
      include: ['static/js/modules/**/*.js'],
      exclude: ['tests/**', 'node_modules/**']
    }
  },
  resolve: {
    alias: {
      '@': './static/js'
    }
  }
});