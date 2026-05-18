import { useEffect, useRef, useCallback } from 'react';

/**
 * NeuralBackground — Full-screen reactive neural particle canvas.
 *
 * Idle:     particles drift slowly with faint connections, subtle orbital motion.
 * Thinking: nodes glow randomly, signal pulses travel along edges,
 *           connections brighten, speed increases.
 */
const NeuralBackground = ({ isThinking }) => {
  const canvasRef = useRef(null);
  const isThinkingRef = useRef(isThinking);
  const activePairsRef = useRef([]);
  const pairTimerRef = useRef(0);
  const pulsesRef = useRef([]);
  const rotationRef = useRef(0);

  useEffect(() => {
    isThinkingRef.current = isThinking;
    if (!isThinking) {
      pulsesRef.current = [];
      activePairsRef.current = [];
    }
  }, [isThinking]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animFrame;
    let w = 0, h = 0;
    let particles = [];
    let lastTime = performance.now();

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    // ── Build particle pool ──────────────────────
    const COUNT = 160;
    for (let i = 0; i < COUNT; i++) {
      const hue = Math.random() < 0.55 ? 190 : 268;
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 0.25 + 0.08;
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        r: Math.random() * 1.6 + 0.5,
        hue,
        glow: 0,
        pulsePhase: Math.random() * Math.PI * 2,
        orbitSpeed: (Math.random() - 0.5) * 0.00015,
      });
    }

    // ── Pick active glowing pairs ────────────────
    const pickActivePairs = () => {
      if (!isThinkingRef.current) {
        activePairsRef.current = [];
        return;
      }
      const count = 12 + Math.floor(Math.random() * 10);
      const pairs = [];
      for (let k = 0; k < count; k++) {
        const i = Math.floor(Math.random() * particles.length);
        let j = Math.floor(Math.random() * particles.length);
        while (j === i) j = Math.floor(Math.random() * particles.length);
        pairs.push([i, j]);
        particles[i].glow = 1.0;
        particles[j].glow = 1.0;

        // spawn signal pulse
        const pi = particles[i], pj = particles[j];
        const dist = Math.hypot(pi.x - pj.x, pi.y - pj.y);
        if (dist < 200) {
          pulsesRef.current.push({
            fromIdx: i, toIdx: j,
            progress: 0,
            speed: 0.008 + Math.random() * 0.006,
            hue: Math.random() < 0.5 ? 190 : 268,
          });
        }
      }
      activePairsRef.current = pairs;
    };

    // ── Main draw loop ───────────────────────────
    const draw = (now) => {
      const dt = Math.min(now - lastTime, 32);
      lastTime = now;
      const thinking = isThinkingRef.current;

      // Pair refresh timer
      pairTimerRef.current += dt;
      if (pairTimerRef.current > 200) {
        pickActivePairs();
        pairTimerRef.current = 0;
      }

      // Orbital rotation
      rotationRef.current += dt * 0.000025;

      const speed = thinking ? 1.8 : 1.0;
      const maxDist = thinking ? 175 : 135;

      ctx.fillStyle = 'rgba(2, 6, 23, 1)';
      ctx.fillRect(0, 0, w, h);

      // Update particles
      const cx = w / 2, cy = h / 2;
      particles.forEach(p => {
        p.pulsePhase += dt * 0.002;
        if (!thinking) {
          p.glow = Math.max(p.glow - dt * 0.012, 0);
        }

        // Subtle orbital drift
        const dx = p.x - cx, dy = p.y - cy;
        const angle = p.orbitSpeed * dt;
        const cos = Math.cos(angle), sin = Math.sin(angle);
        p.x = cx + dx * cos - dy * sin;
        p.y = cy + dx * sin + dy * cos;

        // Linear movement
        p.x += p.vx * speed;
        p.y += p.vy * speed;

        // Bounce
        if (p.x < -20) { p.x = -20; p.vx *= -1; }
        if (p.x > w + 20) { p.x = w + 20; p.vx *= -1; }
        if (p.y < -20) { p.y = -20; p.vy *= -1; }
        if (p.y > h + 20) { p.y = h + 20; p.vy *= -1; }
      });

      const activePairs = activePairsRef.current;
      const activeSet = new Set();
      activePairs.forEach(([a, b]) => { activeSet.add(a); activeSet.add(b); });

      // ── Draw connections ─────────────────────────
      for (let i = 0; i < particles.length; i++) {
        const pi = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const pj = particles[j];
          const ddx = pi.x - pj.x;
          const ddy = pi.y - pj.y;
          const dist = Math.sqrt(ddx * ddx + ddy * ddy);
          if (dist >= maxDist) continue;

          const alpha = 1 - dist / maxDist;
          const isActive = thinking && activePairs.some(
            ([a, b]) => (a === i && b === j) || (a === j && b === i)
          );
          const combinedGlow = (pi.glow + pj.glow) * 0.5;

          if (isActive) {
            const grad = ctx.createLinearGradient(pi.x, pi.y, pj.x, pj.y);
            grad.addColorStop(0, `hsla(${pi.hue}, 100%, 75%, ${alpha * 0.9})`);
            grad.addColorStop(1, `hsla(${pj.hue}, 100%, 75%, ${alpha * 0.9})`);

            // Soft halo
            ctx.save();
            ctx.lineWidth = 6;
            ctx.strokeStyle = grad;
            ctx.globalAlpha = 0.08;
            ctx.beginPath();
            ctx.moveTo(pi.x, pi.y);
            ctx.lineTo(pj.x, pj.y);
            ctx.stroke();

            // Core line
            ctx.lineWidth = 1.5;
            ctx.globalAlpha = 1;
            ctx.strokeStyle = grad;
            ctx.beginPath();
            ctx.moveTo(pi.x, pi.y);
            ctx.lineTo(pj.x, pj.y);
            ctx.stroke();
            ctx.restore();

          } else if (combinedGlow > 0.05) {
            ctx.lineWidth = 0.8;
            ctx.strokeStyle = `rgba(34, 211, 238, ${alpha * combinedGlow * 0.4})`;
            ctx.beginPath();
            ctx.moveTo(pi.x, pi.y);
            ctx.lineTo(pj.x, pj.y);
            ctx.stroke();
          } else {
            ctx.lineWidth = 0.4;
            ctx.strokeStyle = `rgba(34, 211, 238, ${alpha * 0.06})`;
            ctx.beginPath();
            ctx.moveTo(pi.x, pi.y);
            ctx.lineTo(pj.x, pj.y);
            ctx.stroke();
          }
        }
      }

      // ── Draw signal pulses ───────────────────────
      const pulses = pulsesRef.current;
      for (let p = pulses.length - 1; p >= 0; p--) {
        const pulse = pulses[p];
        pulse.progress += pulse.speed * dt * 0.06;
        if (pulse.progress >= 1) {
          pulses.splice(p, 1);
          continue;
        }
        const from = particles[pulse.fromIdx];
        const to = particles[pulse.toIdx];
        const px = from.x + (to.x - from.x) * pulse.progress;
        const py = from.y + (to.y - from.y) * pulse.progress;
        const intensity = Math.sin(pulse.progress * Math.PI);

        // Outer glow
        const grad = ctx.createRadialGradient(px, py, 0, px, py, 12);
        grad.addColorStop(0, `hsla(${pulse.hue}, 100%, 75%, ${intensity * 0.6})`);
        grad.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.arc(px, py, 12, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${pulse.hue}, 100%, 85%, ${intensity * 0.9})`;
        ctx.fill();
      }

      // ── Draw particles ───────────────────────────
      particles.forEach((p, i) => {
        const isActive = activeSet.has(i);
        const pulse = Math.sin(p.pulsePhase) * 0.5 + 0.5;
        const displayGlow = isActive ? Math.max(p.glow, 0.8) : p.glow;
        const glowR = p.r + displayGlow * 4 + (isActive ? pulse * 3 : 0);

        if (displayGlow > 0.05 || isActive) {
          const halo = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowR * 5);
          halo.addColorStop(0, `hsla(${p.hue}, 100%, 75%, ${displayGlow * 0.3})`);
          halo.addColorStop(1, 'transparent');
          ctx.beginPath();
          ctx.arc(p.x, p.y, glowR * 5, 0, Math.PI * 2);
          ctx.fillStyle = halo;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, glowR, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue}, 100%, ${55 + displayGlow * 30}%, ${0.5 + displayGlow * 0.5})`;
        ctx.fill();
      });

      animFrame = requestAnimationFrame(draw);
    };

    animFrame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animFrame);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        display: 'block',
      }}
    />
  );
};

export default NeuralBackground;
