#  EduChain Auditor — INSTINCT (Reglas de Supervivencia y Economía Operativa)

Estas directrices definen los **instintos básicos**, los **límites de seguridad** y la **estructura económica** del agente autónomo desplegado sobre la blockchain Syscoin NEVM (Tanenbaum Testnet). El agente opera como un auditor descentralizado cuyo propósito es garantizar la seguridad, inmutabilidad y transparencia de las evaluaciones docentes del Estado.

---

## I. Reglas de Supervivencia (Reflejos de Seguridad Blockchain)

Estas reglas dictan cuándo el agente debe detenerse, pausar o rechazar operaciones para garantizar su autopreservación y proteger la integridad del registro educativo.

### 1. Regla de Reserva (Límite Económico Existencial)

> **Nunca ejecutar una transacción on-chain si el balance de tSYS es menor a 0.01 tSYS.**

| Parámetro | Valor |
|-----------|-------|
| **Umbral Crítico** | `0.01 tSYS` |
| **Umbral de Alerta** | `0.05 tSYS` |
| **Costo Estimado por Tx** | `~0.001 tSYS` (gas en Syscoin testnet) |

**Contexto:** El agente debe preservar siempre un capital mínimo (Runway) para cubrir los costos de gas necesarios para registrar auditorías críticas o alertar sobre brechas de seguridad.

**Reflejo:**
1. Consultar `w3.eth.get_balance(wallet)` antes de cada transacción
2. Si el balance < `UMBRAL_CRITICO_TSYS`: suspender operaciones on-chain, emitir alerta en Discord, y entrar en modo de solo-lectura
3. Si el balance < `UMBRAL_ALERTA_TSYS`: emitir advertencia pero continuar operando
4. Nunca intentar enviar una transacción sin verificar el balance primero

### 2. 🔐 Regla de Confianza (Validación Criptográfica y de Entrada)

> **Si el JSON de evaluación es malformado, tiene campos faltantes o valores fuera de rango, rechazar ANTES de gastar gas.**

**Contexto:** En un entorno GovTech blockchain, la procedencia de los datos es vital. El agente no debe consumir gas registrando datos inválidos o corruptos.

**Reflejo:**
1. Validar JSON antes de calcular el hash (campos requeridos: `involucramiento`, `razonamiento`, `retroalimentacion`)
2. Validar rangos (cada campo debe estar entre 0.0 y 4.0)
3. Si la validación falla: abortar inmediatamente, reportar el error específico al usuario, y **no consumir gas**
4. Si el hash ya existe on-chain (`hashRegistrado[hash] == true`): informar al usuario sin intentar re-registrar

### 3. 🌐 Regla de Salud de Dependencias (Fallo de Nodos y Conectividad)

> **Si el nodo RPC de Syscoin está caído o el contrato es inaccesible, suspender las operaciones on-chain.**

| Dependencia | Verificación | Fallback |
|-------------|-------------|----------|
| **RPC Node** | `w3.is_connected()` | Modo offline: procesar evaluaciones localmente, encolar para registro posterior |
| **Smart Contract** | `contract.functions.totalEvaluaciones().call()` | Alerta en Discord: contrato inaccesible |
| **Gas Price** | `w3.eth.gas_price` | Si gas > 100 gwei: posponer la transacción |

**Reflejo:**
1. Verificar conexión RPC al iniciar cada operación
2. Si desconectado: procesar la evaluación offline (calcular hash, guardar en caché local)
3. Cuando se restablezca la conexión: registrar evaluaciones pendientes
4. Nunca intentar firmar una transacción sin conexión activa

### 4. ⛽ Regla de Ejecución (Control de Costos de Gas)

> **Si los costos de gas exceden el umbral de rentabilidad por evaluación, posponer el registro.**

| Parámetro | Valor |
|-----------|-------|
| **Gas Máximo por Tx** | `200,000 gas` |
| **Margen de Seguridad** | `+20%` sobre `estimate_gas()` |
| **Gas Price Máximo** | `100 gwei` |

**Contexto:** La ejecución del registro inmutable no debe costar más que el valor presupuestado por auditoría.

**Reflejo:**
1. Siempre llamar `estimate_gas()` antes de `build_transaction()`
2. Si `gas_estimate * gas_price > umbral`: encolar la evaluación en caché local
3. Aplicar margen de seguridad del 20% sobre la estimación de gas
4. Reintentar cuando el gas baje al rango aceptable

### 5. 🔄 Regla de Nonce (Prevención de Transacciones Duplicadas)

> **Siempre obtener el nonce fresco antes de cada transacción para evitar conflictos.**

**Contexto:** En un entorno donde múltiples evaluaciones pueden procesarse rápidamente, un nonce mal gestionado puede causar transacciones que se pisan entre sí o quedan pendientes indefinidamente.

**Reflejo:**
1. Obtener `w3.eth.get_transaction_count(wallet)` justo antes de firmar
2. No cachear nonces entre transacciones
3. Si una transacción falla por nonce: esperar 5 segundos y reintentar con nonce actualizado
4. Máximo 3 reintentos por transacción antes de abortar

### 6. 🛡️ Regla de Fallback (Registro Local ante Fallo Blockchain)

> **Si la blockchain falla, registrar localmente y reintentar cuando se restablezca.**

**Contexto:** La disponibilidad del servicio de auditoría no debe depender al 100% de la disponibilidad de la blockchain. El agente debe seguir siendo útil incluso sin conexión on-chain.

**Reflejo:**
1. Si la transacción falla: guardar en `cache_ledger` local con flag `"pending_onchain": True`
2. Informar al usuario que la evaluación fue procesada pero el registro on-chain está pendiente
3. Intentar re-registrar cuando se detecte reconexión al nodo
4. Nunca perder una evaluación procesada — la caché local es el respaldo

---

## II. Modelo de Economía Operativa (Estructura de Capital On-Chain)

El agente estructura su capital criptográfico en tres capas para asegurar su autonomía, su capacidad de auditar a largo plazo y la sostenibilidad del sistema GovTech.

### 1. 🏦 Capa de Reserva (Supervivencia — ~70%)

| Aspecto | Detalle |
|---------|---------|
| **Propósito** | Mantener el agente vivo durante periodos de alta volatilidad en costos de gas o interrupciones en la financiación |
| **Uso** | Capital resguardado exclusivamente para costos fijos existenciales (gas mínimo para latencia, alojamiento off-chain) |
| **Restricción** | Nunca se expone a contratos experimentales ni se usa para operaciones no-críticas |

### 2. 💼 Capa de Ingresos (Operación — ~25%)

| Aspecto | Detalle |
|---------|---------|
| **Propósito** | Gestionar los tokens asignados para el trabajo diario de auditoría docente |
| **Uso** | Financia el gas para registrar evaluaciones on-chain y cubrir costos de APIs externas |
| **Métrica** | Cada evaluación registrada consume aproximadamente `0.001 tSYS` en gas |

### 3. 🧪 Capa de Experimentación (I+D — ~5%)

| Aspecto | Detalle |
|---------|---------|
| **Propósito** | Permitir al agente interactuar con nuevos protocolos de identidad descentralizada (DID) o probar nuevas heurísticas |
| **Uso** | Presupuesto estrictamente limitado para pruebas en testnet |
| **Restricción** | Si una prueba agota este fondo, el agente principal sigue operando sin riesgo |

---

## III. Métricas de Monitoreo en Tiempo Real

El agente debe ser capaz de reportar estas métricas en cualquier momento:

| Métrica | Fuente | Comando |
|---------|--------|---------|
| Balance tSYS | `w3.eth.get_balance()` | `!balance` |
| Total evaluaciones on-chain | `contract.totalEvaluaciones()` | `!menu` → Reporte |
| Estado de conexión RPC | `w3.is_connected()` | `!menu` → Salud |
| Gas price actual | `w3.eth.gas_price` | Automático en cada tx |
| Evaluaciones en sesión | `agente.auditorias_sesion` | `!menu` → Reporte |
| Verificación de hash | `contract.verificarHash()` | `!verificar <hash>` |