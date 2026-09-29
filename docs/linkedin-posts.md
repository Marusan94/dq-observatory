# LinkedIn drafts — dq-observatory

> Borradores listos para publicar. Reemplaza `[TU_NOMBRE]` y los links de Render cuando el deploy esté vivo.
> Los números citados salen de ejecuciones reales (ver `README.md` → Caso de estudio y `notebooks/customer_segmentation.ipynb`).

---

## Post 1 — Anuncio del proyecto

Limpiar datos es el 80% del trabajo en datos. Así que construí la herramienta que siempre quise tener. 🔭

**DQ Observatory** — plataforma open source para perfilar, validar, limpiar y auditar datasets tabulares antes de que lleguen a producción:

- Score de calidad transparente en 5 dimensiones (completeness, validity, consistency, uniqueness, integrity)
- 24 issues detectados automáticamente en un dataset demo de 5200 filas (2 HIGH)
- Workspace de limpieza con preview antes/después, linaje de versiones y undo
- Exports en 7 formatos, detección de drift, jobs programados, data contracts

Stack: FastAPI + React + Pandas + scikit-learn. CI verde, 27 tests backend, E2E con Playwright.

🔗 Repo: https://github.com/Marusan94/dq-observatory
▶️ Demo en vivo: [LINK_RENDER_FRONTEND]

¿[TU_NOMBRE] | #DataQuality #DataAnalytics #OpenSource #Python

---

## Post 2 — Un hallazgo del caso de estudio

Esta semana audité un dataset de ventas (5200 filas) con mi observatorio de calidad. El resultado me sorprendió. 📊

Score inicial: **65.7/100**. Pero lo interesante está en el desglose:

- **Consistencia: 0/20.** La ciudad "Bogotá" aparecía en 5 variantes (Bogota, bogota, BOGOTA…). Más daño que todos los nulos juntos.
- Normalicé 78 emails… y el score **no se movió**. Normalizar formato ≠ corregir validez. Lección honesta.
- Eliminar 197 duplicados exactos: **65.7 → 67.9**. La única limpieza que movió la aguja.

Y el cierre del círculo: entrené un RandomForest para predecir el segmento de cliente con los datos limpios → accuracy 0.36, **por debajo** del baseline mayoría (0.42). Conclusión de analista: el segmento no se explica con estas features; la señal está en las categóricas sin explotar. Publicar un modelo malo con la lectura correcta también es hacer data science.

Metodología completa + números reproducibles en el repo 👇
🔗 https://github.com/Marusan94/dq-observatory

#DataScience #MachineLearning #DataCleaning #Portfolio
