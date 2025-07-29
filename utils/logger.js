import { createLogger, format, transports } from 'winston';

const logger = createLogger({
  level: 'info', // Nivel por defecto: info, warn, error, etc.
  format: format.combine(
    format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    format.errors({ stack: true }), // Incluye stack traces en errors
    format.splat(),
    format.json() // Output en JSON para fácil parsing
  ),
  transports: [
    new transports.Console({ // Logs en consola
      format: format.combine(
        format.colorize(), // Colores para consola
        format.simple() // Formato simple para lectura humana
      )
    }),
    new transports.File({ filename: 'logs/app.log', level: 'info' }), // Log a archivo en logs/
    new transports.File({ filename: 'logs/errors.log', level: 'error' }) // Separado para errors
  ]
});

export default logger;
