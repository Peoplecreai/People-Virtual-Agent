import { app, startApp } from './src/app.js';
import { registerHandlers } from './src/handlers.js';

// Registra los handlers de eventos
registerHandlers();

// Inicia la app
startApp();
