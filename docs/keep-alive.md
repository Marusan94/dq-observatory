# Keep-alive dq-backend (interruptor)

El backend en Render (plan gratis) se duerme tras ~15 min sin tráfico.
Este workflow lo mantiene despierto solo cuando lo necesitas.

## Interruptor

Archivo `.keep-alive` en la raíz del repo:

| Valor | Efecto |
|-------|--------|
| `on`  | ping a `/health` cada 5 min |
| `off` | no hace nada (ahorra horas gratis) |

Cambiar: edita `.keep-alive`, commit, push. El siguiente ciclo (máx 5 min) lo aplica.

## Despertar ya (antes de un demo)

Actions → Keep alive dq-backend → Run workflow,
o pide en el chat "despierta el backend de dq".

## Notas

- Solo el backend necesita keep-alive; el frontend static va por CDN y no duerme.
- Plan gratis: 750 h/mes por servicio. Con ping cada 5 min se consume casi
  todo el mes: apágalo (`off`) las semanas sin uso.
- GitHub desactiva los schedules tras 60 días sin actividad en el repo.
- Backend: https://dq-backend-vz1v.onrender.com/health
- App: https://dq-observatory.onrender.com
