import * as THREE from 'https://unpkg.com/three@0.160.0/build/three.module.js';

export function initMatrixRain(canvasEl) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x000000, 200, 800);

  const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.1, 1500);
  camera.position.set(0, 0, 420);

  const renderer = new THREE.WebGLRenderer({ canvas: canvasEl, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.setClearColor(0x000000, 0);

  // Build glyph atlas via Canvas2D
  const GLYPHS = [
    '0','1','0','1','0','1',
    'A','B','C','D','E','F',
    'restore','lockdown','✓','sentinel','sync','EXTEKK','x_','0xA4','0xF1','0xC2'
  ];
  const ATLAS_SIZE = 256;
  const atlasCanvas = document.createElement('canvas');
  atlasCanvas.width = atlasCanvas.height = ATLAS_SIZE * 8;
  const actx = atlasCanvas.getContext('2d');
  actx.fillStyle = 'transparent';
  actx.font = "600 96px 'JetBrains Mono', monospace";
  actx.textAlign = 'center';
  actx.textBaseline = 'middle';
  actx.fillStyle = '#00ff94';
  actx.shadowColor = '#00ff94';
  actx.shadowBlur = 12;

  const cellsX = 8, cellsY = 8;
  const cellSize = ATLAS_SIZE;
  const glyphTiles = [];
  for (let i = 0; i < GLYPHS.length && i < cellsX * cellsY; i++) {
    const cx = (i % cellsX) * cellSize + cellSize / 2;
    const cy = Math.floor(i / cellsX) * cellSize + cellSize / 2;
    const text = GLYPHS[i];
    if (text.length > 2) {
      actx.font = "600 56px 'JetBrains Mono', monospace";
    } else {
      actx.font = "600 120px 'JetBrains Mono', monospace";
    }
    actx.fillText(text, cx, cy);
    glyphTiles.push({
      u: (i % cellsX) / cellsX,
      v: 1 - (Math.floor(i / cellsX) + 1) / cellsY,
      w: 1 / cellsX,
      h: 1 / cellsY
    });
  }

  const atlasTex = new THREE.CanvasTexture(atlasCanvas);
  atlasTex.minFilter = THREE.LinearFilter;
  atlasTex.magFilter = THREE.LinearFilter;
  atlasTex.needsUpdate = true;

  // ~120 columns of falling glyphs
  const COLS = Math.min(140, Math.max(80, Math.floor(innerWidth / 14)));
  const GLYPHS_PER_COL = 22;
  const TOTAL = COLS * GLYPHS_PER_COL;

  const geom = new THREE.PlaneGeometry(14, 18);
  const positions = new Float32Array(TOTAL * 3);
  const offsets = new Float32Array(TOTAL * 4); // u,v,w,h
  const alphas = new Float32Array(TOTAL);
  const speeds = new Float32Array(COLS);
  const xs = new Float32Array(COLS);
  const heads = new Float32Array(COLS); // y pos of head
  const zs = new Float32Array(COLS);

  const W = 900, H = 600;
  for (let c = 0; c < COLS; c++) {
    xs[c] = (c / (COLS - 1) - 0.5) * W + (Math.random() - 0.5) * 8;
    zs[c] = (Math.random() - 0.5) * 600 - 200;
    heads[c] = Math.random() * H;
    speeds[c] = 30 + Math.random() * 60;
  }

  const inst = new THREE.InstancedBufferGeometry().copy(geom);
  inst.instanceCount = TOTAL;
  inst.setAttribute('iPosition', new THREE.InstancedBufferAttribute(positions, 3));
  inst.setAttribute('iOffset', new THREE.InstancedBufferAttribute(offsets, 4));
  inst.setAttribute('iAlpha', new THREE.InstancedBufferAttribute(alphas, 1));

  const mat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      uAtlas: { value: atlasTex },
      uHead:  { value: new THREE.Color(0xffffff) },
      uTail:  { value: new THREE.Color(0x00ff94) },
      uFogNear: { value: 200 },
      uFogFar:  { value: 800 },
      uFogColor:{ value: new THREE.Color(0x000000) }
    },
    vertexShader: `
      attribute vec3 iPosition;
      attribute vec4 iOffset;
      attribute float iAlpha;
      varying vec2 vUv;
      varying float vAlpha;
      varying float vFog;
      void main() {
        vec3 pos = position + iPosition;
        vec4 mv = modelViewMatrix * vec4(pos, 1.0);
        vUv = vec2(uv.x * iOffset.z + iOffset.x, uv.y * iOffset.w + iOffset.y);
        vAlpha = iAlpha;
        vFog = -mv.z;
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      uniform sampler2D uAtlas;
      uniform vec3 uHead;
      uniform vec3 uTail;
      uniform float uFogNear;
      uniform float uFogFar;
      uniform vec3 uFogColor;
      varying vec2 vUv;
      varying float vAlpha;
      varying float vFog;
      void main() {
        vec4 t = texture2D(uAtlas, vUv);
        float a = t.a * vAlpha;
        if (a < 0.01) discard;
        vec3 col = mix(uTail, uHead, smoothstep(0.6, 1.0, vAlpha));
        float fog = smoothstep(uFogNear, uFogFar, vFog);
        col = mix(col, uFogColor, fog);
        gl_FragColor = vec4(col, a * (1.0 - fog));
      }
    `
  });

  const mesh = new THREE.Mesh(inst, mat);
  scene.add(mesh);

  // Pre-fill instance positions/uvs
  function rebuild() {
    let i = 0;
    for (let c = 0; c < COLS; c++) {
      for (let g = 0; g < GLYPHS_PER_COL; g++) {
        positions[i*3+0] = xs[c];
        positions[i*3+1] = heads[c] - g * 20;
        positions[i*3+2] = zs[c];
        const tile = glyphTiles[(c + g * 3) % glyphTiles.length];
        offsets[i*4+0] = tile.u;
        offsets[i*4+1] = tile.v;
        offsets[i*4+2] = tile.w;
        offsets[i*4+3] = tile.h;
        const alpha = Math.max(0, 1 - g / GLYPHS_PER_COL);
        alphas[i] = alpha * (g === 0 ? 1.4 : 1) * 0.85;
        i++;
      }
    }
    inst.attributes.iPosition.needsUpdate = true;
    inst.attributes.iOffset.needsUpdate = true;
    inst.attributes.iAlpha.needsUpdate = true;
  }
  rebuild();

  // Cursor parallax
  let tx = 0, ty = 0, cx = 0, cy = 0;
  function onMove(e) {
    const nx = (e.clientX / innerWidth) * 2 - 1;
    const ny = (e.clientY / innerHeight) * 2 - 1;
    tx = ny * 0.052; // ±3°
    ty = nx * 0.052;
  }
  addEventListener('mousemove', onMove, { passive: true });

  // Animation loop
  let running = true;
  let last = performance.now();
  let glyphTickCounter = 0;
  function frame(now) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;

    cx += (tx - cx) * 0.05;
    cy += (ty - cy) * 0.05;
    camera.rotation.x = cx;
    camera.rotation.y = cy;

    // Advance heads
    for (let c = 0; c < COLS; c++) {
      heads[c] -= speeds[c] * dt;
      if (heads[c] < -H) {
        heads[c] = H + Math.random() * 200;
        zs[c] = (Math.random() - 0.5) * 600 - 200;
        speeds[c] = 30 + Math.random() * 60;
      }
    }

    // Update positions every frame, glyph tile shuffle every ~5 frames
    glyphTickCounter++;
    const shuffle = (glyphTickCounter % 5) === 0;
    let i = 0;
    for (let c = 0; c < COLS; c++) {
      for (let g = 0; g < GLYPHS_PER_COL; g++) {
        positions[i*3+1] = heads[c] - g * 20;
        if (shuffle && Math.random() < 0.06) {
          const tile = glyphTiles[Math.floor(Math.random() * glyphTiles.length)];
          offsets[i*4+0] = tile.u;
          offsets[i*4+1] = tile.v;
          offsets[i*4+2] = tile.w;
          offsets[i*4+3] = tile.h;
        }
        i++;
      }
    }
    inst.attributes.iPosition.needsUpdate = true;
    if (shuffle) inst.attributes.iOffset.needsUpdate = true;

    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  function resize() {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight, false);
  }

  function pause()  { running = false; }
  function resume() {
    if (running) return;
    running = true;
    last = performance.now();
    requestAnimationFrame(frame);
  }
  function stop() {
    running = false;
    removeEventListener('mousemove', onMove);
    mesh.geometry.dispose();
    mat.dispose();
    atlasTex.dispose();
    renderer.dispose();
  }

  return { stop, pause, resume, resize };
}
