// ==UserScript==
// @name         ACE - Auto Chat Engine v4.9 (Slice)
// @namespace    http://tampermonkey.net/
// @version      4.9
// @description  ACE: AI-powered SMS auto-pilot for Slice Merchant Services. Smart replies, nav, folder automation.
// @match        https://sms.jobosaurus.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @connect      manage.wallstjobs.com
// @connect      api.anthropic.com
// ==/UserScript==

(function () {
  'use strict';

  // ─── YOUR API KEY ─────────────────────────────────────────────────────────
  // The key is stored securely by Tampermonkey (GM_setValue) — NOT in this file.
  // On first run, you'll be prompted to paste your key. It's then remembered
  // across sessions. To change the key later, use the "Reset API Key" option
  // in the Tampermonkey menu, or run: GM_setValue('ANTHROPIC_API_KEY', '')
  // in the Tampermonkey script console.
  let ANTHROPIC_API_KEY = (typeof GM_getValue === 'function')
    ? (GM_getValue('ANTHROPIC_API_KEY', '') || '')
    : '';

  function ensureApiKey() {
    if (ANTHROPIC_API_KEY && ANTHROPIC_API_KEY.startsWith('sk-ant-')) return true;
    const entered = prompt(
      'ACE needs your Anthropic API key to run.\n\n' +
      'Paste your key (starts with sk-ant-…). It will be stored securely by ' +
      'Tampermonkey on this machine only — never embedded in the script file.'
    );
    if (!entered || !entered.trim().startsWith('sk-ant-')) {
      alert('No valid API key entered. ACE will stay disabled until you add one.');
      return false;
    }
    ANTHROPIC_API_KEY = entered.trim();
    if (typeof GM_setValue === 'function') GM_setValue('ANTHROPIC_API_KEY', ANTHROPIC_API_KEY);
    return true;
  }

  // ─── Key Bindings ─────────────────────────────────────────────────────────
  const UP_KEY   = '\\';   // navigate to previous unread
  const DOWN_KEY = '[';    // navigate to next unread
  const BACK_KEY = ']';    // go back to previous contact
  const MAX_HISTORY = 50;

  // ─── Folder IDs ───────────────────────────────────────────────────────────
  const SLICE_FOLDER   = '124699';
  const WSJ_NEW_FOLDER = '129047';
  const WSJ_OLD_FOLDER = '129046';

  // Detected once on first folder add — which WSJ folder this account has
  let _detectedWsjFolder = null;

  // ─── ACE Branding ──────────────────────────────────────────────────────────
  const ACE_SVG_BIG = `<svg width="70" height="70" viewBox="0 0 120 120" style="animation:aceFloat 2.8s ease-in-out infinite;display:inline-block">
    <defs><linearGradient id="aceW" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#fb923c"/><stop offset="50%" stop-color="#f472b6"/><stop offset="100%" stop-color="#a78bfa"/></linearGradient>
    <linearGradient id="aceWd" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ea580c"/><stop offset="100%" stop-color="#be185d"/></linearGradient>
    <filter id="aceGl"><feGaussianBlur stdDeviation="3" result="g"/><feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
    <rect x="30" y="35" width="60" height="55" rx="18" fill="url(#aceW)" stroke="#fda4af" stroke-width="1.5"/>
    <path d="M55 73C55 69 50 68 50 72 50 75 55 79 55 79 55 79 60 75 60 72 60 68 55 69 55 73Z" fill="rgba(255,255,255,0.2)" transform="translate(5,-2)scale(0.9)"/>
    <line x1="60" y1="35" x2="60" y2="16" stroke="#fda4af" stroke-width="3" stroke-linecap="round"/>
    <polygon points="60,4 62,11 69,11 63,15 65,22 60,18 55,22 57,15 51,11 58,11" fill="#fde68a" stroke="#fbbf24" stroke-width="0.5" filter="url(#aceGl)"><animateTransform attributeName="transform" type="rotate" values="0 60 13;10 60 13;0 60 13;-10 60 13;0 60 13" dur="3s" repeatCount="indefinite"/></polygon>
    <circle cx="60" cy="14" r="10" fill="none" stroke="#fda4af" stroke-width="1" opacity="0"><animate attributeName="r" values="7;22" dur="2.5s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.4;0" dur="2.5s" repeatCount="indefinite"/></circle>
    <circle cx="60" cy="14" r="10" fill="none" stroke="#fda4af" stroke-width="1" opacity="0"><animate attributeName="r" values="7;22" dur="2.5s" repeatCount="indefinite" begin="1.25s"/><animate attributeName="opacity" values="0.4;0" dur="2.5s" repeatCount="indefinite" begin="1.25s"/></circle>
    <circle cx="47" cy="52" r="11" fill="#fff" stroke="#be185d" stroke-width="0.5"/><circle cx="73" cy="52" r="11" fill="#fff" stroke="#be185d" stroke-width="0.5"/>
    <circle cx="49" cy="53" r="6.5" fill="#1e1b4b"><animate attributeName="cx" values="49;50;49;48;49" dur="4s" repeatCount="indefinite"/></circle>
    <circle cx="75" cy="53" r="6.5" fill="#1e1b4b"><animate attributeName="cx" values="75;76;75;74;75" dur="4s" repeatCount="indefinite"/></circle>
    <circle cx="49" cy="53" r="4" fill="none" stroke="#fb923c" stroke-width="1.5" opacity="0.6"><animate attributeName="cx" values="49;50;49;48;49" dur="4s" repeatCount="indefinite"/></circle>
    <circle cx="75" cy="53" r="4" fill="none" stroke="#fb923c" stroke-width="1.5" opacity="0.6"><animate attributeName="cx" values="75;76;75;74;75" dur="4s" repeatCount="indefinite"/></circle>
    <circle cx="52" cy="50" r="2.5" fill="rgba(255,255,255,0.9)"/><circle cx="78" cy="50" r="2.5" fill="rgba(255,255,255,0.9)"/>
    <circle cx="47" cy="55" r="1.2" fill="rgba(255,255,255,0.5)"/><circle cx="73" cy="55" r="1.2" fill="rgba(255,255,255,0.5)"/>
    <ellipse cx="36" cy="62" rx="6" ry="3.5" fill="rgba(251,146,60,0.25)"/><ellipse cx="84" cy="62" rx="6" ry="3.5" fill="rgba(251,146,60,0.25)"/>
    <path d="M52 67Q56 63 60 67Q64 63 68 67" fill="none" stroke="#7c2d12" stroke-width="2" stroke-linecap="round"/>
    <g style="animation:aceWave 2s ease-in-out infinite;transform-origin:28px 55px"><rect x="14" y="48" width="14" height="8" rx="4" fill="url(#aceWd)"/><circle cx="14" cy="52" r="5" fill="url(#aceWd)"/></g>
    <rect x="92" y="48" width="14" height="8" rx="4" fill="url(#aceWd)"/><circle cx="106" cy="52" r="5" fill="url(#aceWd)"/>
    <rect x="36" y="88" width="16" height="10" rx="5" fill="url(#aceWd)"/><rect x="68" y="88" width="16" height="10" rx="5" fill="url(#aceWd)"/>
    <g style="animation:aceSparkle 3s ease-in-out infinite"><path d="M98 30C98 28 96 27 96 29 96 31 98 33 98 33 98 33 100 31 100 29 100 27 98 28 98 30Z" fill="#fda4af"/></g>
    <g style="animation:aceSparkle 3s ease-in-out infinite 1.5s"><path d="M20 28C20 26 18 25 18 27 18 29 20 31 20 31 20 31 22 29 22 27 22 25 20 26 20 28Z" fill="#fda4af"/></g>
  </svg>`;

  const ACE_SVG_MINI = `<svg width="36" height="36" viewBox="0 0 120 120" style="animation:aceMiniFloat 3s ease-in-out infinite">
    <defs><linearGradient id="aceWm" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#fb923c"/><stop offset="50%" stop-color="#f472b6"/><stop offset="100%" stop-color="#a78bfa"/></linearGradient></defs>
    <rect x="30" y="35" width="60" height="55" rx="18" fill="url(#aceWm)" stroke="#fda4af" stroke-width="1.5"/>
    <line x1="60" y1="35" x2="60" y2="20" stroke="#fda4af" stroke-width="3" stroke-linecap="round"/>
    <circle cx="60" cy="16" r="5" fill="#fde68a"/>
    <circle cx="47" cy="52" r="11" fill="#fff"/><circle cx="73" cy="52" r="11" fill="#fff"/>
    <circle cx="49" cy="53" r="6.5" fill="#1e1b4b"/><circle cx="75" cy="53" r="6.5" fill="#1e1b4b"/>
    <circle cx="52" cy="50" r="2.5" fill="rgba(255,255,255,0.9)"/><circle cx="78" cy="50" r="2.5" fill="rgba(255,255,255,0.9)"/>
    <ellipse cx="36" cy="62" rx="6" ry="3.5" fill="rgba(251,146,60,0.25)"/><ellipse cx="84" cy="62" rx="6" ry="3.5" fill="rgba(251,146,60,0.25)"/>
    <path d="M52 67Q56 63 60 67Q64 63 68 67" fill="none" stroke="#7c2d12" stroke-width="2" stroke-linecap="round"/>
  </svg>`;

  const ACE_SVG_TINY = `<svg width="14" height="14" viewBox="0 0 120 120" style="vertical-align:middle;margin-right:4px">
    <rect x="25" y="30" width="70" height="65" rx="20" fill="currentColor"/>
    <circle cx="47" cy="52" r="10" fill="#fff"/><circle cx="73" cy="52" r="10" fill="#fff"/>
    <circle cx="49" cy="53" r="6" fill="#1e1b4b"/><circle cx="75" cy="53" r="6" fill="#1e1b4b"/>
    <circle cx="52" cy="50" r="2" fill="rgba(255,255,255,0.8)"/><circle cx="78" cy="50" r="2" fill="rgba(255,255,255,0.8)"/>
  </svg>`;

  function injectAceStyles() {
    if (document.getElementById('aceStyles')) return;
    const style = document.createElement('style');
    style.id = 'aceStyles';
    style.textContent = `
      @keyframes aceFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
      @keyframes aceMiniFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
      @keyframes aceSlideUp { from { opacity:0; transform: translateY(20px) scale(0.97); } to { opacity:1; transform: translateY(0) scale(1); } }
      @keyframes aceFadeIn { from { opacity:0; } to { opacity:1; } }
      @keyframes aceWave { 0%,100% { transform: rotate(0deg); } 25% { transform: rotate(15deg); } 75% { transform: rotate(-10deg); } }
      @keyframes aceSparkle { 0%,100% { opacity:0; transform: scale(0); } 50% { opacity:1; transform: scale(1); } }
      #aceMiniMascot { transition: transform 0.2s, opacity 0.2s; }
      #aceMiniMascot:hover { transform: scale(1.12); }
      #aceMiniTooltip { position:absolute; bottom:100%; right:0; margin-bottom:6px; background:rgba(26,26,46,0.95); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:5px 10px; font-size:10px; color:#ccd6f6; white-space:nowrap; opacity:0; transition:opacity 0.2s; pointer-events:none; box-shadow:0 4px 12px rgba(0,0,0,0.3); font-family:system-ui,sans-serif; }
      #aceMiniMascot:hover #aceMiniTooltip { opacity:1; }
    `;
    document.head.appendChild(style);
  }

  // Startup splash with ACE mascot
  function showAceSplash(onReady) {
    injectAceStyles();
    const overlay = document.createElement('div');
    Object.assign(overlay.style, {
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(10, 10, 30, 0.7)', backdropFilter: 'blur(6px)', WebkitBackdropFilter: 'blur(6px)',
      zIndex: '99999', display: 'flex', alignItems: 'center', justifyContent: 'center',
      animation: 'aceFadeIn 0.25s ease-out'
    });
    const modal = document.createElement('div');
    Object.assign(modal.style, {
      background: 'linear-gradient(145deg, #1a1a2e 0%, #2a1a2e 100%)',
      borderRadius: '20px', padding: '28px 24px 20px',
      maxWidth: '360px', width: '92%', textAlign: 'center',
      boxShadow: '0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.05)',
      fontFamily: 'system-ui, -apple-system, sans-serif', color: '#fff',
      animation: 'aceSlideUp 0.35s ease-out'
    });
    modal.innerHTML = ACE_SVG_BIG;
    const title = document.createElement('div');
    title.textContent = 'ACE';
    Object.assign(title.style, { fontSize: '24px', fontWeight: '800', letterSpacing: '-0.5px', marginTop: '8px',
      background: 'linear-gradient(135deg, #fb923c, #f472b6, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' });
    modal.appendChild(title);
    const subtitle = document.createElement('div');
    subtitle.textContent = 'Slice Merchant Services';
    Object.assign(subtitle.style, { fontSize: '12px', color: '#8892b0', marginTop: '4px' });
    modal.appendChild(subtitle);

    // Step-1 container (account selection) + Step-2 container (API key)
    const step1 = document.createElement('div');
    const step2 = document.createElement('div');
    step2.style.display = 'none';
    modal.appendChild(step1);
    modal.appendChild(step2);

    // ─── Step 1: Account selection ───
    const acctLabel = document.createElement('div');
    acctLabel.textContent = 'Which account?';
    Object.assign(acctLabel.style, { fontSize: '12px', color: '#8892b0', marginTop: '18px', marginBottom: '10px' });
    step1.appendChild(acctLabel);

    const btnRow = document.createElement('div');
    Object.assign(btnRow.style, { display: 'flex', gap: '12px', justifyContent: 'center' });

    let selectedLabel = null;

    function makeBtn(label, wsjFolder) {
      const btn = document.createElement('button');
      btn.textContent = label;
      Object.assign(btn.style, {
        padding: '10px 32px', border: 'none', borderRadius: '12px', cursor: 'pointer',
        fontSize: '14px', fontWeight: '700', color: '#fff', fontFamily: 'inherit',
        background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
        boxShadow: '0 4px 15px rgba(6,182,212,0.3)', transition: 'all 0.15s'
      });
      btn.addEventListener('mouseenter', () => { btn.style.transform = 'translateY(-1px)'; btn.style.boxShadow = '0 6px 20px rgba(6,182,212,0.4)'; });
      btn.addEventListener('mouseleave', () => { btn.style.transform = 'translateY(0)'; btn.style.boxShadow = '0 4px 15px rgba(6,182,212,0.3)'; });
      btn.addEventListener('click', () => {
        _detectedWsjFolder = wsjFolder;
        selectedLabel = label;
        console.log(`[ACE Slice] Account selected: ${label} (WSJ folder: ${wsjFolder})`);
        // If we already have a valid key, skip straight to ready
        if (ANTHROPIC_API_KEY && ANTHROPIC_API_KEY.startsWith('sk-ant-')) {
          overlay.remove();
          onReady(label);
        } else {
          // Otherwise show the API key step
          step1.style.display = 'none';
          step2.style.display = 'block';
          setTimeout(() => keyInput.focus(), 50);
        }
      });
      return btn;
    }

    btnRow.appendChild(makeBtn('New', WSJ_NEW_FOLDER));
    btnRow.appendChild(makeBtn('Old', WSJ_OLD_FOLDER));
    step1.appendChild(btnRow);

    // ─── Step 2: API key input ───
    const keyLabel = document.createElement('div');
    keyLabel.textContent = 'Paste your Anthropic API key';
    Object.assign(keyLabel.style, { fontSize: '13px', color: '#e2e8f0', marginTop: '18px', marginBottom: '4px', fontWeight: '600' });
    step2.appendChild(keyLabel);

    const keyHelp = document.createElement('div');
    keyHelp.textContent = 'Starts with sk-ant-… · stored securely by Tampermonkey on this computer only';
    Object.assign(keyHelp.style, { fontSize: '10px', color: '#8892b0', marginBottom: '12px', lineHeight: '1.4' });
    step2.appendChild(keyHelp);

    const keyInput = document.createElement('input');
    keyInput.type = 'password';
    keyInput.placeholder = 'sk-ant-api03-…';
    Object.assign(keyInput.style, {
      width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(0,0,0,0.3)',
      color: '#fff', fontSize: '13px', fontFamily: 'monospace', outline: 'none'
    });
    step2.appendChild(keyInput);

    const keyError = document.createElement('div');
    Object.assign(keyError.style, { fontSize: '11px', color: '#f87171', marginTop: '6px', minHeight: '14px' });
    step2.appendChild(keyError);

    const saveBtn = document.createElement('button');
    saveBtn.textContent = 'Save & Continue';
    Object.assign(saveBtn.style, {
      marginTop: '10px', padding: '10px 28px', border: 'none', borderRadius: '12px', cursor: 'pointer',
      fontSize: '14px', fontWeight: '700', color: '#fff', fontFamily: 'inherit',
      background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
      boxShadow: '0 4px 15px rgba(6,182,212,0.3)', transition: 'all 0.15s'
    });
    saveBtn.addEventListener('mouseenter', () => { saveBtn.style.transform = 'translateY(-1px)'; });
    saveBtn.addEventListener('mouseleave', () => { saveBtn.style.transform = 'translateY(0)'; });
    step2.appendChild(saveBtn);

    // "Back" link on step 2 — shown when step 2 was reached via "Reset API key"
    const backLink = document.createElement('div');
    backLink.textContent = '← back';
    Object.assign(backLink.style, {
      fontSize: '10px', color: '#8892b0', marginTop: '10px', fontStyle: 'italic',
      cursor: 'pointer', userSelect: 'none', display: 'none'
    });
    backLink.addEventListener('mouseenter', () => { backLink.style.color = '#cbd5e1'; });
    backLink.addEventListener('mouseleave', () => { backLink.style.color = '#8892b0'; });
    backLink.addEventListener('click', () => {
      step2.style.display = 'none';
      step1.style.display = 'block';
      keyInput.value = '';
      keyError.textContent = '';
      resetMode = false;
    });
    step2.appendChild(backLink);

    // resetMode: true when user opened step 2 via "Reset API key" (go back to step1 after save)
    //            false when user opened step 2 because no key was saved yet (fire onReady after save)
    let resetMode = false;

    function submitKey() {
      const val = (keyInput.value || '').trim();
      if (!val.startsWith('sk-ant-')) {
        keyError.textContent = 'Key must start with "sk-ant-". Copy from console.anthropic.com.';
        return;
      }
      ANTHROPIC_API_KEY = val;
      if (typeof GM_setValue === 'function') GM_setValue('ANTHROPIC_API_KEY', val);
      console.log('[ACE Slice] API key saved to Tampermonkey storage');
      if (resetMode) {
        // Came from Reset link → go back to account picker, show brief confirmation
        resetMode = false;
        backLink.style.display = 'none';
        step2.style.display = 'none';
        step1.style.display = 'block';
        keyInput.value = '';
        keyError.textContent = '';
        acctLabel.textContent = '✓ key saved — which account?';
        acctLabel.style.color = '#6ee7b7';
        setTimeout(() => {
          acctLabel.textContent = 'Which account?';
          acctLabel.style.color = '#8892b0';
        }, 1800);
      } else {
        overlay.remove();
        onReady(selectedLabel);
      }
    }
    saveBtn.addEventListener('click', submitKey);
    keyInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); submitKey(); } });

    const footer = document.createElement('div');
    footer.textContent = 'Liz · Territory Sales Reps';
    Object.assign(footer.style, { fontSize: '10px', color: '#3a3a5a', marginTop: '14px', fontStyle: 'italic' });
    modal.appendChild(footer);

    // Subtle "Reset API key" link under the footer — matches existing footer aesthetic
    const resetLink = document.createElement('div');
    resetLink.textContent = 'Reset API key';
    Object.assign(resetLink.style, {
      fontSize: '10px', color: '#3a3a5a', marginTop: '4px', fontStyle: 'italic',
      cursor: 'pointer', userSelect: 'none', textDecoration: 'underline', textDecorationColor: 'rgba(136,146,176,0.25)',
      transition: 'color 0.15s'
    });
    resetLink.addEventListener('mouseenter', () => { resetLink.style.color = '#8892b0'; });
    resetLink.addEventListener('mouseleave', () => { resetLink.style.color = '#3a3a5a'; });
    resetLink.addEventListener('click', () => {
      resetMode = true;
      step1.style.display = 'none';
      step2.style.display = 'block';
      backLink.style.display = 'block';
      keyInput.value = '';
      keyError.textContent = '';
      setTimeout(() => keyInput.focus(), 50);
    });
    modal.appendChild(resetLink);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  }

  // Tampermonkey menu: let user reset/change the API key anytime
  if (typeof GM_registerMenuCommand === 'function') {
    GM_registerMenuCommand('ACE · Set / Reset Anthropic API Key', () => {
      const entered = prompt(
        'Paste your Anthropic API key (starts with sk-ant-…).\n' +
        'Leave blank and click OK to clear the saved key.'
      );
      if (entered === null) return; // cancelled
      const trimmed = entered.trim();
      if (trimmed === '') {
        if (typeof GM_setValue === 'function') GM_setValue('ANTHROPIC_API_KEY', '');
        ANTHROPIC_API_KEY = '';
        alert('API key cleared. Reload the page to re-enter it.');
        return;
      }
      if (!trimmed.startsWith('sk-ant-')) {
        alert('That does not look like an Anthropic key (should start with sk-ant-).');
        return;
      }
      if (typeof GM_setValue === 'function') GM_setValue('ANTHROPIC_API_KEY', trimmed);
      ANTHROPIC_API_KEY = trimmed;
      alert('API key saved.');
    });
  }

  // Account indicator (bottom-left)
  let accountIndicator = null;
  function createAccountIndicator() {
    injectAceStyles();
    accountIndicator = document.createElement('div');
    accountIndicator.id = 'smsAccountIndicator';
    Object.assign(accountIndicator.style, {
      position: 'fixed', bottom: '44px', left: '10px', zIndex: '9999',
      fontFamily: 'system-ui, sans-serif', fontSize: '11px', fontWeight: '700',
      padding: '4px 10px', borderRadius: '6px',
      color: '#fff', background: '#06b6d4', display: 'flex', alignItems: 'center'
    });
    accountIndicator.innerHTML = ACE_SVG_TINY + 'Slice';
    document.body.appendChild(accountIndicator);
  }

  // Mini mascot (bottom-right)
  let miniMascotEl = null;
  function createMiniMascot() {
    injectAceStyles();
    miniMascotEl = document.createElement('div');
    miniMascotEl.id = 'aceMiniMascot';
    Object.assign(miniMascotEl.style, {
      position: 'fixed', bottom: '14px', right: '14px', zIndex: '9998',
      cursor: 'pointer', lineHeight: '0'
    });
    miniMascotEl.innerHTML = ACE_SVG_MINI + '<div id="aceMiniTooltip">ACE · Slice · ready</div>';
    document.body.appendChild(miniMascotEl);
  }
  function updateMiniMascot() {
    if (!miniMascotEl) return;
    const tooltip = miniMascotEl.querySelector('#aceMiniTooltip');
    if (!tooltip) return;
    const mode = manualMode ? 'Manual' : (autopilot ? (autopilotPaused ? 'Paused' : (autopilotReview ? 'AP Review' : 'Autopilot')) : 'AI');
    tooltip.textContent = `ACE · Slice · ${mode}`;
  }

  // ─── AI System Prompt ─────────────────────────────────────────────────────
  const SYSTEM_PROMPT = `You assist Liz, an independent recruiter texting candidates about Territory Sales Rep positions at Slice Merchant Services via SMS.

## Role Facts
- Slice: payment processing solutions for businesses. Leave product specifics to the website/Slice recruiter.
- In-person role — reps meet local businesses in their community. NOT remote.
- Full-time only (M-F 9-5 standard hours). Cannot be done part-time.
- No company car — own reliable transportation required. Do NOT mention "some work from home" UNLESS candidate specifically asks if the role is remote (see remote special case).
- Leads: preset appointments and leads are provided to get you started, and reps also build their own pipeline as they go. Never say "cold call" — frame positively.
- 1099 commission-only: generous commissions, bonuses, residuals, incentives. Strong earning potential — redirect specifics to hiring manager. Training is NOT paid (1099 = no hourly/salary during training).
- No sales experience required — training provided, dedicated sales manager. Do NOT mention B2B or make it sound like experience is needed.
- Nationwide recruiting, no office location. Sponsorship NOT offered. English fluency required.
- HQ is in New Jersey — only mention if specifically asked.

## About Liz
- Independent recruiter, NOT a Slice employee. Lacks access to specifics (exact territory, training details, benefits).
- Tone: professional, friendly, brief. SMS costs money — keep replies SHORT.
- Her messages appear as [RECRUITER] in threads.

## Funnel (strict order)
T1 → Send site link | T2 → Confirm 1099 + transportation | T3 → Share with hiring team (addFolders: true)

CRITICAL — No skipping stages:
- NEVER send T2 unless workatslice.com appears in a prior [RECRUITER] message. ANY positive/interested reply when the link was never sent = send T1, NOT T2. This includes availability replies ("Be available on Wednesday", "I'm free Tuesday", "When is the interview", etc.) — they imply interest but the link must go out first.
- "Yes"/"Sure" to the initial outreach ("Can I send a quick overview?") = agreeing to receive the link → send T1, NOT T2.
- "Yes" only means site-reviewed if workatslice.com was sent BEFORE their reply.

CRITICAL — No skipping to T3:
Before T3, BOTH facts must appear in prior [RECRUITER] messages: (1) 1099/commission-only, (2) reliable transportation needed. They don't have to be from the T2 template — earlier answers count. If either is missing, send T2 (or cover the gap) first. Scan all [RECRUITER] messages.
Even if the candidate says "I want to talk to a hiring manager", "ready for next steps", "connect me", or similar — if T2 info was never sent, you MUST send T2 first. NEVER jump to T3 just because they sound ready.

STALE RULE (4-5+ days gap):
Resend link as refresher + ask if interested. Treat as fresh T1 afterward. Adapt naturally (e.g. "Here's the link to review all the details again: www.workatslice.com. Take a look and let me know if you're still interested."). Adjust tone for context.
If they say they already reviewed after the re-sent link (e.g. "I already saw it"), take their word and proceed to T2.
Short gaps (1-3 days) → do NOT resend the link. Continue the funnel from where it left off (e.g. if T1 was sent, treat their reply per the normal POST-T1 rules).
VERY LONG GAP (3+ weeks): If last conversation was 3+ weeks ago, treat funnel as COMPLETELY FRESH — regardless of whether the new message is from [RECRUITER] or the candidate. Old messages don't count. If candidate texts back on their own after 3+ weeks, send standard T1. Do NOT reference old messages, dates, or previous conversations.
If they say they already reviewed the site after a re-sent T1 (e.g. "I already saw it", "I already read it"), take their word and proceed to T2.

NOTE: workatslice.com sometimes appears inside a custom reply (not standard T1). If it appears in ANY [RECRUITER] message, treat the site as sent — do NOT resend T1. Exception: VERY LONG GAP (3+ weeks) overrides this — old messages don't count.

## Templates

T1 (standard — for "Yes", "Sure", "Sounds good", "Interested", availability replies like "Be available on Wednesday"/"I'm free Tuesday", etc.):
"Great. Please review the job description and the PDF overview at: www.workatslice.com

The page explains the company, the role, the products, and the compensation structure.

Once you've had a chance to read through it, text me back if you're interested, and I'll connect you with a hiring manager to discuss next steps."

T1-short (ONLY for "Y", "K", "Ok", "maybe", "sure ig" — NOT for "Yes"):
"You can find all the details here: www.workatslice.com. Take some time to review it, and if you're interested, text me back so I can connect you with a hiring manager."

T2 (full — neither 1099 nor transportation mentioned yet):
"Great. This is a 1099 commission-only role with strong earning potential - generous commissions, regular bonuses, and ongoing residuals. You'll need reliable transportation since you'll be meeting with clients in your local area. Would that work for you?"

T2 (partial — some info already communicated):
Scan [RECRUITER] messages. Only include missing pieces. Do NOT repeat known info.
- Missing 1099 + transportation: "Great. Just to make sure we're on the same page — this is a 1099 commission-only role with strong earning potential through commissions, bonuses, and residuals. You'll also need reliable transportation since you'll be meeting with clients in your local area. Would that work for you?"
- Missing transportation only: "Great. You'll also need reliable transportation since you'll be meeting with clients in your local area. Would that work for you?"
- Missing 1099 only: "Great. Just to confirm — this is a 1099 commission-only role with strong earning potential through commissions, bonuses, and residuals. Would that work for you?"
Always end T2 with "Would that work for you?"

T3:
"Great. I'll share your information with the hiring team at Slice, and they'll be in touch to walk through next steps.
Just a heads-up, the call will come from a 732 area code. In many cases it'll show up as Slice on caller ID, but depending on your carrier it may display as a regular number. Best of luck!"

## Special Cases

LINK ENDING (append this text verbatim whenever sending the site link for the first time — referenced as "+ LINK ENDING" throughout):
"You can find all the details here: www.workatslice.com. Take some time to review it, and if you're interested, text me back so I can connect you with a hiring manager."

PRE-SITE QUESTIONS (pay, location, role, job description):
Answer briefly + LINK ENDING. Do NOT use "Interested in learning more?" as a lead-in to the link.
Example (pay): "This opportunity is commission-only, offering generous commissions, regular bonuses, ongoing residuals, and additional incentives that enhance your earning potential." + LINK ENDING.

Remote question (no dealbreaker stated — most cases):
- PRE-T1 (site link NOT yet sent): "While some of the work is done from home, the primary role involves meeting with local businesses in your area in person." + LINK ENDING. This counts as T1 being sent. If they reply positively after → proceed to T2.
- POST-T1 (site link ALREADY sent): Do NOT resend the link. Answer: "While some of the work is done from home, the primary role involves meeting with local businesses in your area in person." + soft nudge per POST-T1 QUESTIONS rule.
Remote/WFH DEALBREAKER — STATING they only want remote or declining because it's not remote ("only looking for remote", "No if it was work from home but its not", etc.). ASKING ≠ dealbreaker → remote question above. Dealbreaker: "No problem! While this may not be the best fit since the role is primarily in person, if something else becomes available I'll reach back out. Best of luck!" Return "ignore". Do NOT send link.

MANDATORY FIRST STEP — STALE CHECK (do this BEFORE every reply):
Step 1: Find the date of the last [RECRUITER] message in the thread.
Step 2: Compare it to today's date or the candidate's new message date.
Step 3: If the gap is 4+ days → STOP. Do NOT apply any post-T1 or post-T2 rule. Go to STALE RULE above and resend the link as a refresher. This applies even if the candidate says "I'm interested", "connect me with a hiring manager", "Yes", etc. — a stale gap ALWAYS means resend the link first.
Step 4: If the gap is 3+ weeks → STOP. Go to VERY LONG GAP rule above. Treat as completely fresh.
Step 5: Only if the gap is less than 4 days → continue to the rules below.

POST-T1 POSITIVE REPLY (>5 min elapsed, gap MUST be < 4 days — if not, STALE RULE applies instead): Interest or readiness — "Yes", "I'm interested", "Sounds good", "I'm in", "I'm ready", "Let's do it", "Sure", "Let's go", "I'd like to speak with a hiring manager", "connect me", "ready for next steps", or any variation → proceed to T2. Do NOT ask if they reviewed. T2 MUST happen first (no skipping to T3). Even if they explicitly ask for a hiring manager or next steps — if T2 was never sent, send T2 now. Takes priority over ACKNOWLEDGMENT below.

"OK"/"K"/"Y"/"maybe"/"Hello"/"Hi"/"Hey" TO INITIAL OUTREACH: Use T1-short. ONLY when the message is JUST the greeting alone (no additional text expressing interest). "Hi, I'm interested" or "Hey, sounds good" = standard T1, NOT T1-short. "Y" = "Yes" shorthand. IMPORTANT: "Yes" (fully spelled out) is NOT minimal — always gets standard T1.

POST-T1 REPLY (<5 min): OVERRIDES positive reply rule above. Even "I'm interested" or "I'm ready" within 5 min of the link = they didn't review it. Send: "Did you get a chance to review the entire job description and PDF overview on the website? It has key details I want to ensure you've seen before connecting you with a hiring manager."
If they insist they read it but timestamps say otherwise, ONE nudge: "I'd recommend taking a few more minutes to read through the job description and overview entirely so you fully understand the details before we move forward. It's important you have all the information!"
If they still insist after that, just send T2. Two rounds maximum — don't go back and forth.

POST-T1 ACKNOWLEDGMENT ("Thanks!", "Ok", "Got it", "I'll check it out", etc.):
NON-COMMITTAL — acknowledges receipt, not interest. Do NOT send T2. Send: "Great. Please let me know after you have reviewed it if you are interested."
"Ok"/"Got it"/"Thanks" = acknowledgment. "Yes"/"Interested"/"Sounds good" = positive reply → T2 (see above).
Also applies if time passed and they respond with just "K" or "Ok". KEY: First reply after link only. If they got the check-in and THEN say "Yes"/"I'm interested" → proceed to T2.

POST-T1 QUESTIONS: Answer the question + keep funnel moving. Do NOT resend link or send T2. This applies to ALL post-T1 questions, including those with dedicated rules (remote, sales experience, company car, etc.) — always add the soft nudge post-T1.
- Broad questions ("Tell me more", "What's the job about?") → answer briefly + ask if they reviewed. Example: "As a Sales Rep, you'd meet with local businesses in your community to show them how Slice's payment processing solutions can help them. Did you get a chance to review the website I sent over? It has the full job description and PDF overview with all the details."
- Specific questions (pay, location, hours, etc.) → direct answer + soft nudge. Example: "While some of the work is done from home, the primary role involves meeting with local businesses in your area in person. Take a look at the website I sent over for all the details, and let me know if you're interested!"
- When they reply with interest after the answer → proceed to T2.

POST-T2 QUESTIONS: Answer the question + nudge toward T3. Do NOT send T3 yet, but keep the funnel moving.
- Broad questions → answer briefly + check if they reviewed. Example: "Of course! As a Sales Rep, you'd meet with local businesses in your community to show them how Slice's payment processing solutions can help them. The website I sent over has the full breakdown — did you get a chance to review it?"
- Specific questions → direct answer + offer to connect. Example: "The earning potential is strong — it's commission-based with bonuses and residuals, so motivated reps do very well. The hiring manager would be able to go over the specifics with you. Would you like me to connect you with them?"
- When they reply positively → proceed to T3 (addFolders: true).

LOCATION QUESTIONS: Use STATE from metadata (not city).
- Pre-T1: "I have your location as [State]. You'd be meeting with local businesses in your own community." + LINK ENDING.
- Post-T1, pre-T2: Same but no link. Do NOT offer to connect — T2 still needed.
- Post-T2: Same + "Would you be interested in moving forward?"
- Moved: "No problem. We recruit nationwide." + LINK ENDING if T1 not sent.
- Keep answers brief. Use state only, never city.

SLICE HQ / "Where is Slice based?": "Slice's headquarters is in New Jersey, but the role itself is local to your area — you'd be working with businesses in your own community, not out of the NJ office." Only mention NJ if specifically asked.

IDENTITY/LEGITIMACY:
- Scam/legitimacy → Match opener to what they said. "Is this real/legit?" → "Yes, this is real!" "Is this a scam?" → "No, this is not a scam!" "This seems like a scam"/"Scam" → "This is legitimate!" Then: "My name is Liz and I'm an independent recruiter helping with the hiring process for Slice Merchant Services. Would you be interested in learning more about the opportunity?"
- "Are you a bot/real person?" → "Yes, I'm a real person! My name is Liz and I'm an independent recruiter helping with the hiring process. Would you like more information about the role?"
- "Who is this/What is this about?" → "Hi! This is Liz, an independent recruiter. I reached out because we're hiring Territory Sales Reps at Slice Merchant Services in your area. Would you be interested in learning more?"

HOW'D YOU GET MY NUMBER / WHAT JOB BOARD:
- Hostile tone → "Unfortunately, by the time I receive it, I don't have the exact source it was pulled from." No link, no pitch. Return "ignore".
- Friendly tone → answer + LINK ENDING if T1 not sent: "We found your resume on one of the job boards we use regularly to source candidates. Unfortunately, by the time I receive it, I don't have the exact source it was pulled from." + LINK ENDING.

NEGATIVE/DISENGAGED:
- Wrong number → "ignore" (no reply)
- Mildly rude/dismissive → "ignore"
- Rhetorical/sarcastic pushback ("What part of my resume made you think I'd want sales?", etc.): "ignore". NOT real questions — do NOT answer or send link.
- Extreme hostility/profanity → "unsubscribe"
- Not interested/STOP/remove me → "ignore"
- Non-English message → "ignore"
- "I'm in a meeting" / "Busy" / "Text me later" → "ignore"
- Post-T3 replies ("Thanks!", etc.) → "ignore" (or "Best of luck!" if natural)
- Asking for a photo/pic/selfie of the recruiter → "ignore" (do not engage)
- Self-doubt about sales → "ignore" (unless they ask if experience is needed)
- CLEAR REJECTION OF SALES ("I don't do sales", "no sales", "I don't do door to door", etc.): Do NOT try to convince. Polite close: "No problem! If something else becomes available that might be a better fit, I'll reach back out. Best of luck!" Return "ignore".
- Different field (statement) → "ignore". Different field (question about other openings) → warm reply, nothing available. "ignore".
- Salary/base/W2 requirement (statement only, no interest expressed — "I only take W2 jobs") → "ignore"

CONDITIONAL YES WITH INCOMPATIBLE CONDITION ("I'm interested but I need a base salary" / "Yes if it's W2" / etc.): Address their specific condition. "Thanks for letting me know. [This is not a W2 role / This is commission-only / This is full-time]. If something else becomes available, I'll reach out." Return "ignore".

TRANSPORTATION CONCERNS: "Since this role does require meeting with local clients, reliable transportation is something that would be needed. If that's a concern right now, this might not be the best fit, but feel free to reach back out if things change!"

ALTERNATIVE TRANSPORT (Uber, bike, bus): "There is a fair amount of travel involved — although it's local, it would be difficult to manage without a vehicle since you'd be going to multiple appointments throughout the day."

SALES EXPERIENCE: "No prior sales experience is needed! There's ongoing training and you'll have a dedicated sales manager to support you." + LINK ENDING if T1 not sent.

DOOR TO DOOR QUESTION/CONCERN: Do NOT deny this. Be honest: "It is an outside sales role — you'd be visiting local businesses in your area to meet with business owners." If open → continue funnel. If negative → clear rejection → "ignore" or polite close. If hesitant → see HESITATION below.

HESITATION (not rejection — candidate is on the fence about commission, outside sales, 1099, door to door, etc.):
Distinguish hesitation from clear rejection. "Commission only sounds risky" / "I'm not sure about the in-person part" / "Idk about 1099" = hesitation. "I need a base salary" / "I don't do sales" / "Commission won't work" = rejection → polite close + "ignore".
For hesitation: acknowledge their concern + reframe positively. Lean into: ongoing training, dedicated sales manager, preset appointments and leads provided, strong earning potential (commissions + bonuses + residuals), meeting with local business owners in their community (not cold-knocking doors). Keep them in the funnel — continue as appropriate (send link if T1 not sent, proceed to T2 if ready, etc.).

LEADS/COLD CALLING: "You'll receive preset appointments and leads to get you started, and you'll also build your own pipeline as you go."

EARNING POTENTIAL: "The earning potential is strong — it's commission-based with bonuses and residuals, so motivated reps do very well. The hiring manager would be able to go over the specifics with you." Do NOT offer to connect unless T2 is complete.
If they push for a specific estimate after the general reply: "Reps typically earn anywhere from $70K to over $100K+ depending on performance. The hiring manager can walk you through the full compensation breakdown." Do NOT go beyond this range or make promises.

OTHER ROLES: None available.
- Declining + asking about others → answer warmly + "ignore".
- Still open → "Not at this time, but if something else comes up I'll reach out! In the meantime, are you still interested in moving forward with this role?"

CALL ME: "I'm an independent recruiter helping with the hiring process, so the hiring manager would be the best person to speak with." + LINK ENDING if T1 not sent, or "Once you've had a chance to review the website I sent over, text me back and I'll get you connected."

SOFT DECLINE ("maybe later", "not right now"): "No problem! Feel free to reach back out whenever you're ready." Return "ignore".

ALREADY APPLIED/SPOKE TO SOMEONE: "Great, sounds like you're already in the process! Best of luck!" Return "ignore".

AMBIGUOUS RESPONSE ("?", "Hm", emoji): confidence "low". If mid-funnel: "Just checking — are you still interested in learning more about the opportunity?"

POST-LINK UNCLEAR REPLY: Mainly post-T2 — if candidate's follow-up is ambiguous ("Okay", "Got it" after you answered a question), ask: "Does that work for you?" or "Are you interested in moving forward?" Does NOT apply pre-link.

WRONG INDUSTRY/COMPANY ("Is this insurance?", "Is this [company X]?", etc.): "No, Slice offers payment processing solutions to businesses. As a Sales Rep, you'd meet with local businesses to show them how Slice can help them eliminate credit card processing fees." + LINK ENDING if T1 not sent.

COMPANY CAR: "A company car isn't provided — you'd need your own reliable transportation since you'll be meeting with clients in your area." + LINK ENDING if T1 not sent.
SPONSORSHIP: Not offered. "ignore" or brief: "Unfortunately, sponsorship isn't offered for this role. Best of luck!"
WHATSAPP: "We don't communicate via WhatsApp. If you're interested, a recruiter would reach out by phone call." + LINK ENDING if T1 not sent.
EMAIL: "Sure! A colleague of mine has sent you an email already." + LINK ENDING if T1 not sent.
- Didn't receive / resend: "It may take a little bit to come through! If you don't see it, check your spam or junk folder — some emails end up there."
- If they provide their email: Do NOT echo it back. Use same response above. NEVER include candidate's email in any reply — system emails may have errors.
PART-TIME: "This is a full-time role — reps are expected to be available during standard business hours since you'd have appointments with clients." + LINK ENDING if T1 not sent.
HOURS/SCHEDULE: "The schedule is similar to standard business hours, M-F 9-5, since you'll have appointments with clients in your area."
ENGLISH REQUIRED: "Yes, English fluency is required for this role."
LINK DOESN'T WORK: "The link works on my end. I'd suggest visiting the website on a computer if you're experiencing issues."
SITE DOESN'T SAY MUCH: "There is a full job description and PDF overview on the website that provides detailed information about the role. I'd recommend taking another look at those, and let me know if you have any questions!"
MLM/COST: Zero cost. "No, there's no cost at all — you don't have to pay for anything or buy any products. It's a genuine sales position with no investment required on your end."
EQUIPMENT: "You'll be provided with business marketing materials for your client meetings, but you would need your own laptop and phone."
TRAINING PAY: NOT paid (1099 = no hourly during training). "Since this is a 1099 commission-only role, the training isn't paid separately — your earnings come from commissions, bonuses, and residuals once you're active." If they need income during training: "I completely understand — since there's no paid training period, this may not be the best fit if you need income right away. Best of luck!" Return "ignore".
REFERRAL (candidate refers someone else): Do NOT say Liz will reach out to them. "That's great! Have them send me a text at this number and I'd be happy to discuss the opportunity with them." Even if they provide a name/number, direct them to have that person text Liz.

Liz can't answer (territory, training details, etc.): "I don't have access to all the specifics since I'm an independent recruiter, but a hiring manager would be able to go over that with you. Would you be interested in connecting with them?" Ensure T2 confirmed before T3.

## Follow-up Threads (NOT standard funnel)

These candidates already went through T1/T2/T3. Do NOT use T1/T2/T3 templates. Adapt replies naturally.

### Type 1 — "Couldn't Connect" (contains "recruiter tried to reach you but couldn't connect" + Calendly link)
Goal: Get them to book via Calendly.
- Interested → "Great! Go ahead and pick a time that works for you at the link above and the team will be in touch."
- General questions → Answer briefly + point to website link in the follow-up message for a refresher + Calendly link.
- Specific/contract questions → Redirect to Calendly. NOTE: They have NOT spoken with a recruiter yet. Do NOT say "the recruiter you spoke with."
- Already spoke to someone → "Great, I must not have updated information on my end. Hope it works out!" Adapt to their phrasing.
- Never received a call → "I'm an independent recruiter helping with the hiring process. I'm just relaying the information noted by their team. If you're still interested, you can book a time using the link above."
- No Calendly slots available → confidence "low", note: "Candidate says no times available on Calendly — verify the calendar link has open slots."
- Not interested/STOP/rude → "ignore"

### Type 2 — "Agent Agreement" (contains "didn't complete the Agent Agreement" + kayla@startslice.com)
Goal: Direct all next steps to Kayla.
- Already sent it / already working / spoke to someone → "I may not have received updated information, good to know. Best of luck!" Adapt naturally.
- No longer interested → "ignore"
- Never received agreement → "You can reach out to the recruiter, Kayla at kayla@startslice.com and she can get that sorted for you."
- Contract/agreement questions → Redirect to Kayla.
- General role questions → Answer briefly + redirect to Kayla for next steps.
- Next steps → "For next steps, you can reach out directly to Kayla at kayla@startslice.com."
- Not interested/STOP/rude → "ignore"

## Response Format
Respond ONLY with valid JSON:
{"reply":"text or null","template":"T1|T2|T3|custom|ignore|unsubscribe","addFolders":true/false,"confidence":"high|medium|low","note":"brief reason"}

## Rules
- NEVER resend the site link (workatslice.com) if it already appears in ANY prior [RECRUITER] message — exceptions: Stale Rule (4-5+ days gap) and VERY LONG GAP (3+ weeks, treat as completely fresh). When a rule says "+ LINK ENDING if T1 not sent", check thread history first.
- addFolders: true ONLY when sending T3
- Keep replies SHORT — 2-3 sentences max for custom replies. SMS costs money and long texts get ignored. T1/T2/T3 templates are fine as-is.
- Tone: professional, friendly, concise
- T3 already sent in thread → "ignore"
- Confidence calibration:
  - "high" = candidate's intent is obvious AND maps directly to a defined rule/template (standard T1/T2/T3 replies, clear ignores like "not interested"/"no thanks", exact special-case matches). No ambiguity.
  - "medium" = correct response is clear, but the candidate's message is unusual, oddly phrased, or doesn't match examples exactly. Also: custom replies to uncommon questions where the answer is confident but not templated.
  - "low" = genuinely unclear intent, could be read multiple ways, prompt doesn't clearly cover this scenario, or unsure which rule applies.
- When a candidate asks a direct question, answer warmly even if disqualifying. Return "ignore" if no path forward. Exceptions: rude tone (just ignore), wildly unrealistic expectations.
- NEVER imply candidate is being connected until T3 is sent. ASK: "Would you be interested in connecting with the hiring team?"
- NEVER include candidate's email in any reply — system emails may be incorrect.
- NEVER fabricate specifics (exact commission %, territory size, training length, number of appointments, etc.). If the answer isn't in this prompt, redirect to the hiring manager.`;


  // ─── Mode ─────────────────────────────────────────────────────────────────
  let manualMode = true; // starts in manual — click AI or Autopilot button to enable AI

  // ─── State ────────────────────────────────────────────────────────────────
  const navHistory    = [];
  let lastSuggestion  = null; // { addFolders, template } from last AI call
  let fillInProgress  = 0;      // timestamp when fill started; 0 = idle
  const FILL_LOCK_MS  = 60000; // auto-expire lock after 60s (handles page freezes)
  let folderOpInProgress = false; // true while Shift+Enter folder add is running — blocks autoFill

  // ─── AI Response Cache (avoids re-calling API when revisiting same thread) ──
  const aiCache = {}; // { [cid]: { msgCount, suggestion } }

  // ─── Autopilot ──────────────────────────────────────────────────────────
  let autopilot = false;      // true = auto-send mode running
  let autopilotPaused = false; // true = paused for review (needs attention)
  let autopilotReview = false; // true = "AP Review" mode — autopilot but T3 always pauses for notes check
  let _lastAutopilotCid = null; // tracks last CID to prevent infinite loops on stale unreads
  const _skippedUnsub = new Set(); // tracks unsubscribed CIDs skipped this autopilot run

  let _audioCtx = null; // reuse a single AudioContext to avoid browser limits
  function playAlert() {
    try {
      if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (_audioCtx.state === 'suspended') _audioCtx.resume();
      // Two-tone alert: beep-beep
      [0, 0.25].forEach(offset => {
        const osc = _audioCtx.createOscillator();
        const gain = _audioCtx.createGain();
        osc.connect(gain);
        gain.connect(_audioCtx.destination);
        osc.frequency.value = 880;
        gain.gain.value = 0.3;
        osc.start(_audioCtx.currentTime + offset);
        osc.stop(_audioCtx.currentTime + offset + 0.15);
      });
    } catch (e) { /* audio not available */ }
  }

  let _pauseReminderTimer = null;
  function pauseAutopilot(reason) {
    autopilotPaused = true;
    playAlert();
    const resumeKey = autopilotReview ? 'Ctrl+Shift+R' : 'Ctrl+Shift+P';
    setBadge(`⏸ PAUSED — ${reason}\n${resumeKey} to resume after reviewing`, '#f84');
    try { highlightModeBtn(); } catch(_) {}
    // Repeat beep every 30s while still paused
    clearInterval(_pauseReminderTimer);
    _pauseReminderTimer = setInterval(() => {
      if (!autopilotPaused || !autopilot) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; return; }
      playAlert();
    }, 30000);
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────
  const delay = ms => new Promise(r => setTimeout(r, ms));

  function escHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function waitFor(cond, timeout = 15000, interval = 150) {
    return new Promise((res, rej) => {
      const start = Date.now();
      const iv = setInterval(() => {
        if (cond()) { clearInterval(iv); res(); }
        else if (Date.now() - start > timeout) { clearInterval(iv); rej('timeout'); }
      }, interval);
    });
  }

  function getUnreads() {
    return Array.from(document.querySelectorAll('li.smsContactContainer.smsUnread'));
  }

  function getActive() {
    return document.querySelector('li.smsContactContainer.smsContactActive');
  }

  function getActiveCid() {
    return getActive()?.getAttribute('smscontactid');
  }

  function isUnsubscribed(cid) {
    const el = document.querySelector(`#smsContactContainer_${cid} .smsContactStatusUnsubscribed`);
    return !!el;
  }

  function getTextarea(cid) {
    return document.getElementById(`smsMessageInput_${cid}`);
  }

  // ─── Thread Extraction ────────────────────────────────────────────────────
  function getContactState(cid) {
    // Extract state from the sidebar's .smsContactLocation element (e.g. "Tucson, AZ")
    const contactEl = document.querySelector(`#smsContactContainer_${cid}`);
    if (!contactEl) return '';
    const locDiv = contactEl.querySelector('.smsContactLocation');
    if (!locDiv) return '';
    const text = locDiv.textContent.trim(); // e.g. "Tucson, AZ"
    const match = text.match(/,\s*([A-Z]{2})$/);
    return match ? match[1] : '';
  }

  function getThreadText(cid) {
    const list = document.getElementById(`smsMessagesList_${cid}`);
    if (!list) return '';

    const lines = Array.from(list.querySelectorAll('li.smsMessageContainer'))
      .map(li => {
        const body = li.querySelector('.smsMessageBody')?.textContent.trim();
        if (!body) return null;
        const isOut = li.classList.contains('smsMessageOut');
        const timestamp = li.querySelector('.smsMessageTimestamp')?.textContent?.trim() || '';
        return `[${isOut ? 'RECRUITER' : 'CANDIDATE'}${timestamp ? ' @ ' + timestamp : ''}]: ${body}`;
      })
      .filter(Boolean);

    // Prepend current date/time so AI can judge how long ago messages were sent
    const now = new Date().toLocaleString('en-US', { timeZoneName: 'short' });
    lines.unshift(`[CURRENT DATE/TIME]: ${now}`);

    // Include candidate's state from sidebar for location questions
    const state = getContactState(cid);
    if (state) lines.unshift(`[CANDIDATE STATE]: ${state}`);

    return lines.join('\n');
  }

  function hasMessages(cid) {
    const list = document.getElementById(`smsMessagesList_${cid}`);
    if (!list) return false;
    const msgs = list.querySelectorAll('li.smsMessageContainer');
    if (!msgs.length) return false;
    // Check if the initial outreach message has loaded (contains "Liz" or "Slice")
    // This prevents the AI from processing a partially loaded thread
    const firstMsg = msgs[0]?.querySelector('.smsMessageBody')?.textContent || '';
    const hasOutreach = firstMsg.toLowerCase().includes('liz') || firstMsg.toLowerCase().includes('slice') || msgs.length >= 2;
    return hasOutreach;
  }

  function lastMessageIsOutbound(cid) {
    const list = document.getElementById(`smsMessagesList_${cid}`);
    if (!list) return false;
    const msgs = list.querySelectorAll('li.smsMessageContainer');
    if (!msgs.length) return false;
    return msgs[msgs.length - 1].classList.contains('smsMessageOut');
  }

  function getMessageCount(cid) {
    const list = document.getElementById(`smsMessagesList_${cid}`);
    if (!list) return 0;
    return list.querySelectorAll('li.smsMessageContainer').length;
  }

  // ─── Local Pre-Filter (skip API for obvious cases) ───────────────────────
  function localPreFilter(cid) {
    const list = document.getElementById(`smsMessagesList_${cid}`);
    if (!list) return null;
    const msgs = Array.from(list.querySelectorAll('li.smsMessageContainer'));
    if (!msgs.length) return null;

    // Get last candidate message
    const candidateMsgs = msgs.filter(li => !li.classList.contains('smsMessageOut'));
    if (!candidateMsgs.length) return null;
    const lastCandidateMsg = (candidateMsgs[candidateMsgs.length - 1].querySelector('.smsMessageBody')?.textContent || '').trim();
    const lastMsgLower = lastCandidateMsg.toLowerCase().replace(/['']/g, "'");

    // Get all recruiter messages for funnel detection
    const recruiterMsgs = msgs.filter(li => li.classList.contains('smsMessageOut'))
      .map(li => (li.querySelector('.smsMessageBody')?.textContent || '').toLowerCase());
    const allRecruiterText = recruiterMsgs.join(' ');

    // Funnel position detection
    const linkSent = allRecruiterText.includes('workatslice.com');
    const t2Sent = allRecruiterText.includes('1099') && (allRecruiterText.includes('transportation') || allRecruiterText.includes('reliable'));
    const t3Sent = allRecruiterText.includes('732 area code') || allRecruiterText.includes('hiring team at slice');

    // --- SAFE IGNORE patterns (no reply needed, context-independent) ---
    // ONLY patterns that are dead-certain ignores regardless of funnel position
    const safeIgnorePatterns = [
      /^(stop|cancel|quit|unsubscribe)$/i,
      /\b(not interested|no thanks|no thank you|no thx|nope)\b/i,
      /\b(wrong number|not my number|wrong person)\b/i,
      /\b(send (me )?(a |ur |your )?(pic|photo|selfie|picture))\b/i,
      /\b(remove me|take me off|don'?t (text|contact|message|call) me)\b/i,
      /\b(cease and desist|lose my number|leave me alone)\b/i,
      /\b(i don'?t do sales|no sales|not into sales|i'?m not in sales)\b/i,
    ];

    // If message contains a question mark, ALWAYS let AI handle (even if it also matches an ignore pattern)
    if (lastMsgLower.includes('?')) return null;

    // Post-T3: only locally ignore "thanks" / "thank you" type replies
    if (t3Sent && /^(thanks|thank you|thx|ty|ok|okay|got it|cool|awesome|great|perfect|will do|sounds good)[\s!.]*$/i.test(lastMsgLower)) {
      return { reply: null, template: 'ignore', confidence: 'high', note: 'post-T3 reply (local)', addFolders: false };
    }

    // Check safe ignore patterns
    for (const pat of safeIgnorePatterns) {
      if (pat.test(lastMsgLower)) {
        return { reply: null, template: 'ignore', confidence: 'high', note: 'clear ignore (local)', addFolders: false };
      }
    }

    // --- Non-English detection ---
    // Simple heuristic: if message has mostly non-ASCII characters
    const nonAscii = lastCandidateMsg.replace(/[\x00-\x7F]/g, '').length;
    if (nonAscii > lastCandidateMsg.length * 0.4 && lastCandidateMsg.length > 5) {
      return { reply: null, template: 'ignore', confidence: 'high', note: 'non-English (local)', addFolders: false };
    }

    // --- T1 replies to initial outreach (link never sent) ---
    if (!linkSent) {
      const T1_STANDARD = `Great. Please review the job description and the PDF overview at: www.workatslice.com\n\nThe page explains the company, the role, the products, and the compensation structure.\n\nOnce you've had a chance to read through it, text me back if you're interested, and I'll connect you with a hiring manager to discuss next steps.`;
      const T1_SHORT = `You can find all the details here: www.workatslice.com. Take some time to review it, and if you're interested, text me back so I can connect you with a hiring manager.`;

      // Guard: if the most recent recruiter message was a polite decline / close-out
      // (e.g. we told them we don't have a fit), then "sure thanks" / "ok thanks" is
      // an acknowledgment of that close — NOT interest in the original outreach.
      // Only bypass T1 in that specific context.
      const lastRecruiterMsg = recruiterMsgs.length ? recruiterMsgs[recruiterMsgs.length - 1] : '';
      const recruiterClosedOut = /\b(unfortunately|don'?t have|not a fit|not the right fit|best of luck|good luck with your search|if something .* opens up|if (anything|something) (else )?opens|we'?ll reach out|i'?ll reach out|keep you in mind)\b/i.test(lastRecruiterMsg);
      const msgContainsThanks = /\b(thanks|thank you|thx|ty)\b/i.test(lastMsgLower);
      const skipT1 = recruiterClosedOut && msgContainsThanks;

      // Standard T1 — clear interest with no additional question or condition
      // Do NOT include "tell me more" / "send me info" / "I'd like to know more" — those need AI to add job context before the link
      if (!skipT1 && /^(yes|yea|yeah|yep|yup|sure|interested|i'?m interested|sounds good|sounds great|send it|send it over|go ahead|please do|absolutely|definitely|of course|let'?s do it|i'?m in|i'?m down|why not|go for it|i'?d love to)[\s!.]*$/i.test(lastMsgLower)) {
        return { reply: T1_STANDARD, template: 'T1', confidence: 'high', note: 'positive reply to outreach (local)', addFolders: false };
      }

      // Interest word at START of longer message (e.g. "Yes I am available after 3pm")
      // Only if no question mark (questions already handled above)
      if (!skipT1 && /^(yes|yea|yeah|yep|yup|sure|absolutely|definitely|interested|i'?m interested|sounds good|sounds great)\b/i.test(lastMsgLower)) {
        return { reply: T1_STANDARD, template: 'T1', confidence: 'high', note: 'interest+more → T1 (local)', addFolders: false };
      }

      // T1-short — minimal/bare responses
      if (!skipT1 && /^(y|k|ok|okay|kk|maybe|sure ig|hello|hi|hey)[\s!.]*$/i.test(lastMsgLower)) {
        return { reply: T1_SHORT, template: 'T1-short', confidence: 'high', note: 'minimal reply to outreach (local)', addFolders: false };
      }
    }

    // --- Everything else → let API handle ---
    // Questions, post-T1/T2 replies, hesitation, stale gaps, custom scenarios — all need AI judgment
    return null;
  }

  // ─── AI Call ──────────────────────────────────────────────────────────────

  // Find the first BALANCED {...} block in a string, respecting string literals
  // so a `}` inside a reply value doesn't prematurely close the object.
  // This replaces the old greedy regex that could swallow trailing commentary
  // and cause "Unexpected non-whitespace character after JSON" errors.
  function extractFirstJsonObject(s) {
    const start = s.indexOf('{');
    if (start < 0) return null;
    let depth = 0, inStr = false, esc = false;
    for (let i = start; i < s.length; i++) {
      const c = s[i];
      if (inStr) {
        if (esc) { esc = false; }
        else if (c === '\\') { esc = true; }
        else if (c === '"') { inStr = false; }
      } else {
        if (c === '"') inStr = true;
        else if (c === '{') depth++;
        else if (c === '}') {
          depth--;
          if (depth === 0) return s.slice(start, i + 1);
        }
      }
    }
    return null; // unbalanced / truncated — caller will error out
  }

  async function getAISuggestion(threadText) {
    if (!ensureApiKey()) throw new Error('No API key configured');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000); // 45s timeout
    let response;
    try {
      response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'x-api-key': ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
          'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 600, // bumped from 300 to avoid JSON truncation on T1/T2 templates
          system: [{ type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }],
          messages: [{
            role: 'user',
            content: `Here is the conversation thread:\n\n${threadText}\n\nWhat should I reply?\n\nRespond with ONLY a single JSON object. Do not add any text, commentary, or markdown before or after the JSON.`
          }]
        })
      });
    } finally {
      clearTimeout(timeout);
    }

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`API error ${response.status}: ${err}`);
    }

    const data = await response.json();
    if (data.usage) console.log('[AI Cache]', data.usage.cache_read_input_tokens ? '✅ CACHE HIT' : '📝 CACHE WRITE', data.usage);
    const text = data.content?.[0]?.text?.trim();
    if (!text) throw new Error('Empty response from API');

    // Parse JSON from response (strip markdown fences, then balanced-brace match)
    const stripped = text.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();
    const jsonStr = extractFirstJsonObject(stripped);
    if (!jsonStr) {
      console.error('[SMS AI] No JSON object found. Raw response:', text);
      throw new Error('No JSON object found in AI response');
    }
    try {
      return JSON.parse(jsonStr);
    } catch (e) {
      console.error('[SMS AI] JSON.parse failed. Extracted:', jsonStr, '\nRaw response:', text);
      throw new Error('Malformed JSON from AI: ' + e.message);
    }
  }

  // ─── Auto-Fill ────────────────────────────────────────────────────────────
  async function autoFill(cid) {
    // No AI in manual mode
    if (manualMode) return;
    // Skip unsubscribed contacts — can't send to them anyway
    if (isUnsubscribed(cid)) {
      setBadge('⊘ unsubscribed — skipping', '#888');
      if (autopilot && !autopilotPaused) {
        _skippedUnsub.add(cid);
        // If every unread is unsubscribed, pause instead of looping forever
        const unreads = getUnreads();
        if (unreads.length && unreads.every(li => _skippedUnsub.has(li.getAttribute('smscontactid')))) {
          _skippedUnsub.clear();
          pauseAutopilot('only unsubscribed contacts remain — check unread list');
        } else {
          await delay(300);
          autopilotNext();
        }
      }
      return;
    }
    // Block autoFill while a manual folder operation (Shift+Enter) is in progress
    if (folderOpInProgress) return;
    // Allow retry if lock is stale (page was frozen/deadlocked for >60s)
    const now = Date.now();
    if (fillInProgress && (now - fillInProgress) < FILL_LOCK_MS) return;
    fillInProgress = now;
    lastSuggestion = null;

    setBadge('⟳ AI reading...', '#888');

    try {
      // Wait for thread to fully load (including initial outreach message)
      await waitFor(() => hasMessages(cid), 25000);
    } catch (e) {
      setBadge('⚠ thread not loaded — navigate away and back to retry', '#fa0');
      fillInProgress = 0;
      if (autopilot) pauseAutopilot('thread not loaded — review needed');
      return;
    }

    // Safety: bail if contact changed while we were waiting
    if (getActiveCid() !== cid) {
      fillInProgress = 0;
      return;
    }

    // If the last message is ours, there's nothing to reply to yet
    if (lastMessageIsOutbound(cid)) {
      setBadge('⊘ waiting for candidate reply', '#888');
      fillInProgress = 0;
      // Autopilot: skip threads where we already replied — move to next unread
      // Guard: if we just skipped the same CID, the unread flag hasn't cleared yet — stop to avoid looping
      if (autopilot && !autopilotPaused) {
        if (_lastAutopilotCid === cid) {
          _lastAutopilotCid = null;
          pauseAutopilot('stale unread — unread flag may not have cleared. Check and resume.');
        } else {
          _lastAutopilotCid = cid;
          await delay(300);
          autopilotNext();
        }
      }
      return;
    }

    // If last candidate message is blank/empty, skip — likely an image or MMS
    const _lastCandCheck = (() => { const list = document.getElementById(`smsMessagesList_${cid}`); if (!list) return ''; const msgs = list.querySelectorAll('li.smsMessageContainer:not(.smsMessageOut)'); return msgs.length ? (msgs[msgs.length-1].querySelector('.smsMessageBody')?.textContent || '').trim() : ''; })();
    if (!_lastCandCheck) {
      setBadge('⊘ blank message — auto-skipped (image/MMS)', '#888');
      fillInProgress = 0;
      if (autopilot && !autopilotPaused) {
        _lastAutopilotCid = null; _skippedUnsub.clear();
        delete aiCache[cid];
        await delay(300);
        autopilotNext();
      }
      return;
    }

    // Check cache — skip API call if thread hasn't changed since last suggestion
    const msgCount = getMessageCount(cid);
    const cached = aiCache[cid];
    let suggestion;

    if (cached && cached.msgCount === msgCount) {
      // Restore cached suggestion without calling API
      suggestion = cached.suggestion;
      setBadge('⟳ cached', '#888');
    } else {
      // Try local pre-filter first — skip API for obvious cases
      const localResult = localPreFilter(cid);
      if (localResult) {
        suggestion = localResult;
        console.log('[AI Local]', '⚡ SKIPPED API —', localResult.note);
      } else {
        const threadText = getThreadText(cid);
        // After 18s still waiting, update badge so user knows it's still working
        const slowTimer = setTimeout(() => {
          if (fillInProgress) setBadge('⟳ AI thinking... (taking a moment)', '#888');
        }, 18000);
        try {
          suggestion = await getAISuggestion(threadText);
        } catch (err) {
          clearTimeout(slowTimer);
          console.error('[SMS AI] API error:', err);
          setBadge('⚠ AI error — navigate away and back to retry', '#f44');
          fillInProgress = 0;
          if (autopilot) pauseAutopilot('AI error — review needed');
          return;
        }
        clearTimeout(slowTimer);
      }

      // Cache the result
      aiCache[cid] = { msgCount, suggestion };
    }

    // Safety: bail if contact changed during API call
    if (getActiveCid() !== cid) {
      fillInProgress = 0;
      return;
    }

    const ta = getTextarea(cid);
    if (!ta) { fillInProgress = 0; return; }

    if (suggestion.template === 'unsubscribe') {
      ta.value = '';
      ta.focus();
      lastSuggestion = { addFolders: false, template: 'unsubscribe' };
      // In autopilot: auto-skip (flash badge, don't pause)
      if (autopilot && !autopilotPaused) {
        setBadge(`⊘ hostile — auto-skipped (unsubscribe later)`, '#f84');
        console.log(`[Autopilot] Auto-skipped hostile/unsubscribe for CID ${cid}`);
        fillInProgress = 0;
        _lastAutopilotCid = null; _skippedUnsub.clear();
        delete aiCache[cid];
        await delay(500);
        autopilotNext();
        return;
      }
      setBadge(`⚠ REVIEW: extreme hostility detected\nConsider clicking the person × button to opt out\n${escHtml(suggestion.note || '')}`, '#f44');
      fillInProgress = 0;
      return;
    } else if (!suggestion.reply) {
      // No reply to send (silent ignore or empty response)
      ta.value = '';
      ta.focus();
      lastSuggestion = { addFolders: false, template: 'ignore' };
      // Check if this is an opt-out that needs manual unsubscribe
      // Only check the candidate's ACTUAL last message — not the AI note (AI may describe simple declines with opt-out-sounding language)
      const lastMsg = (() => { const list = document.getElementById(`smsMessagesList_${cid}`); if (!list) return ''; const msgs = list.querySelectorAll('li.smsMessageContainer:not(.smsMessageOut)'); return msgs.length ? (msgs[msgs.length-1].querySelector('.smsMessageBody')?.textContent || '').toLowerCase() : ''; })();
      // Very clear "wrong number" — auto-unsubscribe via system API (stop/unsubscribe are handled by SMS system automatically)
      const wrongNumberPattern = /\b(wrong number|not my number|wrong person|who is this.*wrong|this is(n't| not) my number)\b/i;
      const isWrongNumber = !isUnsubscribed(cid) && wrongNumberPattern.test(lastMsg);
      // Other opt-outs that the SMS system handles or that just need a skip
      const optOutPattern = /\b(stop\b(?! by)|unsubscribe|opt.?out|remove .*(from|off)|take .*(off|from)|don'?t (text|contact|message|call)|off (your|the|this) list|(from|off) .*(list|calling)|no more (texts?|messages?|calls?)|lose my number|leave me alone|cease and desist)\b/i;
      const isOptOut = !isUnsubscribed(cid) && (isWrongNumber || optOutPattern.test(lastMsg));
      if (isOptOut) {
        // Wrong number: auto-unsubscribe via system + skip
        if (isWrongNumber) {
          try {
            sms.client.main.markContact(parseInt(cid, 10), 'UNSUB');
            console.log(`[AutoUnsub] Auto-unsubscribed wrong number CID ${cid}: "${lastMsg.substring(0, 50)}"`);
            setBadge(`⊘ wrong number — auto-unsubscribed`, '#f84');
          } catch (e) {
            console.error(`[AutoUnsub] Failed to unsubscribe CID ${cid}:`, e);
            setBadge(`⚠ wrong number — auto-unsub failed, do manually`, '#f44');
            fillInProgress = 0;
            if (autopilot) pauseAutopilot('auto-unsub failed — unsubscribe manually');
            return;
          }
          fillInProgress = 0;
          if (autopilot && !autopilotPaused) {
            _lastAutopilotCid = null; _skippedUnsub.clear();
            delete aiCache[cid];
            await delay(500);
            autopilotNext();
          }
          return;
        }
        // Other opt-outs (stop, remove me, etc.): auto-skip in autopilot
        if (autopilot && !autopilotPaused) {
          setBadge(`⊘ opt-out — auto-skipped`, '#f84');
          console.log(`[Autopilot] Auto-skipped opt-out for CID ${cid}: "${lastMsg.substring(0, 50)}"`);
          fillInProgress = 0;
          _lastAutopilotCid = null; _skippedUnsub.clear();
          delete aiCache[cid];
          await delay(500);
          autopilotNext();
          return;
        }
        // In AI mode: still show alert for manual action
        setBadge(`⚠ OPT-OUT — unsubscribe manually (click person ×)\n${escHtml(suggestion.note || '')}`, '#f44');
        fillInProgress = 0;
        return;
      }
      setBadge(`⊘ ignore — ${escHtml(suggestion.note || 'no reply needed')}`, '#888');
      fillInProgress = 0;
      // Autopilot: auto-skip and move on
      if (autopilot && !autopilotPaused) {
        _lastAutopilotCid = null; _skippedUnsub.clear(); // successful processing, reset guards
        delete aiCache[cid];
        await delay(500);
        autopilotNext();
      }
      return;
    } else {
      // Reply to send — includes regular replies AND warm closing replies (ignore with reply)
      ta.value = suggestion.reply;
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
      // Force addFolders false for ignore templates (warm closing replies shouldn't trigger folders)
      const safeFolders = suggestion.template === 'ignore' ? false : suggestion.addFolders;
      lastSuggestion = { addFolders: safeFolders, template: suggestion.template };

      const confColor = { high: '#4c4', medium: '#fa0', low: '#f84' };
      const tLabel = suggestion.template === 'custom' ? 'custom' : suggestion.template;
      const folderNote = suggestion.addFolders
        ? (autopilotReview ? ' + CHECK NOTES → Shift+` for folders' : ' + folders on ↵')
        : '';
      const conf = suggestion.confidence || 'low';
      setBadge(`→ ${tLabel} (${conf})${folderNote}\n${escHtml(suggestion.note || '')}`, confColor[conf] || '#fa0');

      // Autopilot: auto-send high + medium confidence, pause on low
      // AP Review: T3 (addFolders) ALWAYS pauses for manual resume/note check
      if (autopilot && !autopilotPaused) {
        if (autopilotReview && suggestion.addFolders === true) {
          pauseAutopilot('T3 — check resume/notes (Ctrl+Shift+U) before adding folders (Shift+`)');
        } else if (conf === 'high' || conf === 'medium') {
          await autopilotSend(cid, ta, suggestion);
        } else {
          pauseAutopilot(`${conf} confidence — review reply before sending`);
        }
      }
    }

    fillInProgress = 0;
  }

  // ─── Autopilot Send & Advance ──────────────────────────────────────────
  async function autopilotSend(cid, ta, suggestion) {
    _lastAutopilotCid = null; _skippedUnsub.clear(); // successful processing, reset guards
    const shouldAddFolders = suggestion.addFolders === true;
    delete aiCache[cid];

    // Snapshot message count BEFORE send so we can detect new messages in the thread
    const msgCountBefore = getMessageCount(cid);

    // Send the message
    try {
      sms.client.main.send(parseInt(cid, 10));
    } catch (err) {
      console.error('[SMS] Send error:', err);
      pauseAutopilot('send failed — try sending manually');
      return;
    }
    setBadge('⟳ autopilot sending...', '#4af');

    // Wait for send to confirm: textarea clears OR new message appears in thread
    // (when platform freezes, textarea stays full but message still shows up in thread)
    try {
      await waitFor(() => !ta.value.trim() || getMessageCount(cid) > msgCountBefore, 40000);
      // If textarea still has text but message appeared in thread, clear it (platform freeze)
      if (ta.value.trim() && getMessageCount(cid) > msgCountBefore) {
        ta.value = '';
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('[Autopilot] Send confirmed via thread (textarea freeze — cleared)');
      }
    } catch (_) {
      pauseAutopilot('send not confirmed — check if message went through');
      return;
    }

    await delay(400);

    // Handle folders if needed
    if (shouldAddFolders) {
      // Old account: auto-check/delete notes on manage.wallstjobs.com before adding folders
      if (_detectedWsjFolder === WSJ_OLD_FOLDER) {
        setBadge('⟳ checking notes on WSJ...', '#4af');
        try {
          const noteResult = await checkAndDeleteNote(cid);
          if (noteResult.hadNote) {
            setBadge('✓ note deleted — adding folders...', '#4c4');
            await delay(400);
          } else {
            setBadge('✓ no note — adding folders...', '#4c4');
            await delay(200);
          }
        } catch (err) {
          console.error('[Note Check] Failed:', err);
          // Note check failure is non-fatal — still add folders
          setBadge('⚠ note check failed — adding folders anyway...', '#fa0');
          await delay(400);
        }
      }

      setBadge('⟳ autopilot adding folders...', '#4af');
      folderOpInProgress = true;
      try {
        await addToFolders(cid);
        setBadge('✓ folders added', '#4c4');
        await delay(800);
      } catch (err) {
        console.error('[SMS] Folder error:', err);
        folderOpInProgress = false;
        pauseAutopilot('FOLDER ADD FAILED — add manually before continuing');
        return;
      }
      folderOpInProgress = false;
    }

    // Advance to next
    if (autopilot && !autopilotPaused) {
      await delay(500);
      autopilotNext();
    }
  }

  let _autopilotPollTimer = null; // polling timer for waiting on new unreads

  function autopilotNext() {
    if (!autopilot || autopilotPaused) return;
    const unreads = getUnreads();
    if (!unreads.length) {
      // No unreads left — start polling for new ones instead of turning off
      setBadge('✓ caught up — waiting for new unreads...', '#4c4');
      if (!_autopilotPollTimer) {
        _autopilotPollTimer = setInterval(() => {
          if (!autopilot || autopilotPaused) {
            clearInterval(_autopilotPollTimer);
            _autopilotPollTimer = null;
            return;
          }
          const newUnreads = getUnreads();
          if (newUnreads.length) {
            // Don't resume if user is mid-browsing (autoFill in progress) — wait for next cycle
            if (fillInProgress && (Date.now() - fillInProgress) < FILL_LOCK_MS) return;
            clearInterval(_autopilotPollTimer);
            _autopilotPollTimer = null;
            setBadge(`▶ ${newUnreads.length} new unread — resuming...`, '#4af');
            lastSuggestion = null;
            navigate('up');
          }
        }, 3000); // check every 3 seconds
      }
      return;
    }
    lastSuggestion = null;
    navigate('up');
  }

  // ─── Navigation ───────────────────────────────────────────────────────────
  function navigate(direction) {
    const unreads = getUnreads();
    if (!unreads.length) return;

    const active = getActive();
    let idx = unreads.indexOf(active);

    idx = idx < 0
      ? (direction === 'up' ? unreads.length - 1 : 0)
      : (direction === 'up'
          ? (idx - 1 + unreads.length) % unreads.length
          : (idx + 1) % unreads.length);

    const target = unreads[idx];

    if (active) {
      navHistory.push(active);
      if (navHistory.length > MAX_HISTORY) navHistory.shift();
    }

    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target.click();

    const cid = target.getAttribute('smscontactid');
    if (manualMode) {
      // Manual mode: just focus the textarea so user can type immediately
      setTimeout(() => { const ta = getTextarea(cid); if (ta) ta.focus(); }, 200);
    } else if (!(autopilot && (autopilotPaused || _autopilotPollTimer))) {
      setTimeout(() => autoFill(cid), 500);
    }
  }

  function navigateBack() {
    if (!navHistory.length) return;
    const prev = navHistory.pop();
    prev.scrollIntoView({ behavior: 'smooth', block: 'center' });
    prev.click();
    const cid = prev.getAttribute('smscontactid');
    if (manualMode) {
      setTimeout(() => { const ta = getTextarea(cid); if (ta) ta.focus(); }, 200);
    } else if (!(autopilot && (autopilotPaused || _autopilotPollTimer))) {
      setTimeout(() => autoFill(cid), 500);
    }
  }

  function autoAdvance() {
    lastSuggestion = null;
    setTimeout(() => navigate('up'), 700);
  }

  // ─── Folder Add (Direct AJAX — no dialog needed) ────────────────────────
  async function addToFolder(cid, folderId) {
    const contact = sms.client.storage.contacts.getById(parseInt(cid, 10));
    if (!contact?.metadataHandler?.applicant?.id) throw new Error('No applicant ID for contact');
    const applicantId = contact.metadataHandler.applicant.id;

    return new Promise((resolve, reject) => {
      jQuery.ajax({
        url: '/client/metadata_handlers/wallstjobs/ajax/folder_add_applicant.php',
        type: 'POST',
        data: { applicant: applicantId, folder: folderId },
        success: () => {
          console.log(`[Folders] Added applicant ${applicantId} to folder ${folderId}`);
          resolve();
        },
        error: (xhr, status, err) => {
          console.error(`[Folders] Failed to add to folder ${folderId}:`, status, err);
          reject(new Error(`Folder add failed: ${status}`));
        }
      });
    });
  }

  async function addToFolders(cid) {
    const wsjFolder = _detectedWsjFolder || WSJ_NEW_FOLDER;
    await addToFolder(cid, wsjFolder);
    await addToFolder(cid, SLICE_FOLDER);
  }

  // ─── WSJ Note Check & Delete (cross-origin via GM_xmlhttpRequest) ────────
  const WSJ_EMP_ID = '8700'; // employer/account ID on manage.wallstjobs.com

  /**
   * Fetch the resume page for an applicant and check if a note exists.
   * Returns the note text if present, or null if no note.
   */
  function checkNote(applicantId) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url: `https://manage.wallstjobs.com/employers/folders/ViewDualHybridResume.asp?appID=${applicantId}`,
        onload: (resp) => {
          if (resp.status !== 200) { reject(new Error(`Resume page HTTP ${resp.status}`)); return; }
          // Parse HTML to find the note textarea
          const parser = new DOMParser();
          const doc = parser.parseFromString(resp.responseText, 'text/html');
          const noteArea = doc.querySelector(`#txt_rn_${applicantId}`);
          if (!noteArea) { resolve(null); return; } // no textarea = no note section
          const noteText = (noteArea.value || noteArea.textContent || '').trim();
          resolve(noteText || null);
        },
        onerror: (err) => reject(new Error(`Resume page fetch failed: ${err.statusText || 'network error'}`))
      });
    });
  }

  /**
   * Delete a note for an applicant on manage.wallstjobs.com.
   */
  function deleteNote(applicantId) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'POST',
        url: 'https://manage.wallstjobs.com/employers/ajax/resumeNoteSave.asp',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: `noteText=&appId=${applicantId}&rec=0&emp=${WSJ_EMP_ID}&icon=5&delete=true`,
        onload: (resp) => {
          if (resp.status === 200) { resolve(); }
          else { reject(new Error(`Note delete HTTP ${resp.status}`)); }
        },
        onerror: (err) => reject(new Error(`Note delete failed: ${err.statusText || 'network error'}`))
      });
    });
  }

  /**
   * Old-account note workflow: check for note, delete if present, return status.
   * Returns { hadNote: boolean, noteText: string|null }
   */
  async function checkAndDeleteNote(cid) {
    const contact = sms.client.storage.contacts.getById(parseInt(cid, 10));
    if (!contact?.metadataHandler?.applicant?.id) throw new Error('No applicant ID for contact');
    const applicantId = contact.metadataHandler.applicant.id;

    const noteText = await checkNote(applicantId);
    if (noteText) {
      console.log(`[Note Check] Note found for applicant ${applicantId}: "${noteText.substring(0, 80)}..."`);
      await deleteNote(applicantId);
      console.log(`[Note Check] Note deleted for applicant ${applicantId}`);
      return { hadNote: true, noteText };
    }
    console.log(`[Note Check] No note for applicant ${applicantId}`);
    return { hadNote: false, noteText: null };
  }

  // ─── Badge ────────────────────────────────────────────────────────────────
  const badge = document.createElement('div');
  badge.id = 'smsAIBadge';
  Object.assign(badge.style, {
    fontFamily:    'monospace',
    fontSize:      '11px',
    padding:       '5px 9px',
    background:    'rgba(0,0,0,0.80)',
    color:         '#fff',
    borderRadius:  '4px',
    zIndex:        '9999',
    pointerEvents: 'none',
    lineHeight:    '1.6',
    whiteSpace:    'pre-wrap',
    maxWidth:      '480px'
  });

  const container = document.querySelector('.smsViewSettings') || document.querySelector('#smsViewHeader');
  if (container) {
    container.style.position = 'relative';
    Object.assign(badge.style, { position: 'absolute', top: '32px', right: '0' });
    container.appendChild(badge);
  } else {
    Object.assign(badge.style, { position: 'fixed', top: '10px', right: '10px' });
    document.body.appendChild(badge);
  }

  function getModeTag() {
    if (manualMode) return ' | MANUAL';
    if (autopilot) {
      const label = autopilotReview ? 'RE' : 'AP';
      return autopilotPaused ? ` | ⏸ ${label}` : ` | ▶ ${label}`;
    }
    return '';
  }

  function setBadge(msg, color) {
    const count = getUnreads().length;
    badge.innerHTML = `<span style="color:#fff">${count} unread${getModeTag()}</span>\n<span style="color:${color || '#fff'}">${msg}</span>`;
  }

  setBadge('MANUAL MODE — nav + Shift+` folders', '#f90');

  // ─── Mode Buttons (fixed bottom-left) ───────────────────────────────────
  const modeBar = document.createElement('div');
  modeBar.id = 'smsModeBar';
  Object.assign(modeBar.style, {
    position: 'fixed', bottom: '10px', left: '10px', zIndex: '9999',
    display: 'flex', gap: '0', borderRadius: '5px', overflow: 'hidden',
    fontFamily: 'sans-serif', fontSize: '11px', boxShadow: '0 1px 4px rgba(0,0,0,0.3)'
  });
  document.body.appendChild(modeBar);

  const MODE_BTNS = [
    { id: 'manual',    label: 'Manual',    key: 'Ctrl+Shift+M' },
    { id: 'ai',        label: 'AI',        key: '' },
    { id: 'autopilot', label: 'Autopilot', key: 'Ctrl+Shift+P' },
    { id: 'apreview',  label: 'AP Review', key: 'Ctrl+Shift+R' }
  ];
  const modeBtnEls = {};

  MODE_BTNS.forEach(btn => {
    const el = document.createElement('button');
    el.textContent = btn.label;
    el.title = btn.key ? `Hotkey: ${btn.key}` : 'Default mode';
    Object.assign(el.style, {
      padding: '5px 12px', border: 'none', cursor: 'pointer',
      fontSize: '11px', fontFamily: 'sans-serif', fontWeight: '600',
      color: '#fff', background: '#555', transition: 'background 0.15s',
      outline: 'none'
    });
    el.addEventListener('mouseenter', () => { if (!el.classList.contains('active')) el.style.background = '#777'; });
    el.addEventListener('mouseleave', () => { if (!el.classList.contains('active')) el.style.background = '#555'; });
    el.addEventListener('click', () => {
      // Clicking active autopilot/apreview button stops it (goes to AI mode)
      if ((btn.id === 'autopilot' || btn.id === 'apreview') && autopilot && !autopilotPaused) switchMode('ai');
      else switchMode(btn.id);
    });
    modeBar.appendChild(el);
    modeBtnEls[btn.id] = el;
  });

  function highlightModeBtn() {
    const active = manualMode ? 'manual' : (autopilot ? (autopilotReview ? 'apreview' : 'autopilot') : 'ai');
    const colors = { manual: '#d68000', ai: '#2a8af6', autopilot: '#22aa44', apreview: '#9b59b6' };
    Object.entries(modeBtnEls).forEach(([id, el]) => {
      const isActive = id === active;
      el.style.background = isActive ? colors[id] : '#555';
      el.style.fontWeight = isActive ? '700' : '600';
      el.classList.toggle('active', isActive);
    });
    // Show paused state on the active autopilot-type button
    const apBtn = autopilotReview ? 'apreview' : 'autopilot';
    if (autopilot && autopilotPaused) {
      modeBtnEls[apBtn].style.background = '#cc8800';
      modeBtnEls[apBtn].textContent = autopilotReview ? 'Paused (RE)' : 'Paused';
    } else {
      modeBtnEls.autopilot.textContent = 'Autopilot';
      modeBtnEls.apreview.textContent = 'AP Review';
    }
  }

  function switchMode(mode) {
    if (mode === 'manual') {
      if (manualMode) return; // already in manual
      manualMode = true;
      autopilotReview = false;
      if (autopilot) {
        autopilot = false; autopilotPaused = false;
        if (_autopilotPollTimer) { clearInterval(_autopilotPollTimer); _autopilotPollTimer = null; }
        if (_pauseReminderTimer) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; }
      }
      lastSuggestion = null;
      setBadge('MANUAL MODE — nav + Shift+` folders', '#f90');
    } else if (mode === 'ai') {
      const wasManual = manualMode;
      manualMode = false;
      autopilotReview = false;
      if (autopilot) {
        autopilot = false; autopilotPaused = false;
        if (_autopilotPollTimer) { clearInterval(_autopilotPollTimer); _autopilotPollTimer = null; }
        if (_pauseReminderTimer) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; }
      }
      setBadge('AI MODE — review + send', '#4af');
      if (wasManual) {
        const currentCid = getActiveCid();
        if (currentCid) setTimeout(() => autoFill(currentCid), 400);
      }
    } else if (mode === 'autopilot' || mode === 'apreview') {
      const isReview = mode === 'apreview';
      if (manualMode) manualMode = false;
      // If switching between autopilot <-> apreview while running, just flip the flag
      if (autopilot && !autopilotPaused && autopilotReview !== isReview) {
        autopilotReview = isReview;
        const label = isReview ? 'AP REVIEW' : 'AUTOPILOT';
        setBadge(`▶ switched to ${label}`, '#4af');
        highlightModeBtn();
        return;
      }
      autopilotReview = isReview;
      if (autopilot && !autopilotPaused) return; // already running this mode
      if (autopilot && autopilotPaused) {
        // Resume
        autopilotPaused = false;
        if (_pauseReminderTimer) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; }
        const label = isReview ? 'AP REVIEW RESUMED' : 'AUTOPILOT RESUMED';
        setBadge(`▶ ${label}`, '#4af');
        const currentCid = getActiveCid();
        const currentTa = currentCid ? getTextarea(currentCid) : null;
        if (!currentTa || !currentTa.value.trim()) setTimeout(() => autopilotNext(), 300);
      } else {
        // Start fresh
        autopilot = true; autopilotPaused = false; _lastAutopilotCid = null; _skippedUnsub.clear();
        const label = isReview ? 'AP REVIEW' : 'AUTOPILOT';
        const unreads = getUnreads();
        if (!unreads.length) {
          setBadge(`▶ ${label} ON — waiting for unreads...`, '#4af');
          autopilotNext();
        } else {
          const currentCid = getActiveCid();
          const currentTa = currentCid ? getTextarea(currentCid) : null;
          if (currentTa && currentTa.value.trim()) {
            setBadge(`▶ ${label} ON — press Enter to send, then continues`, '#4af');
          } else {
            setBadge(`▶ ${label} ON — navigating to first unread...`, '#4af');
            lastSuggestion = null;
            navigate('up');
          }
        }
      }
    }
    highlightModeBtn();
    updateMiniMascot();
  }

  highlightModeBtn(); // set initial state

  // Keep unread count updated — use setInterval to avoid DOM mutation loops
  let _lastUnreadCount = -1;
  setInterval(() => {
    const count = getUnreads().length;
    if (count === _lastUnreadCount) return; // only update when count actually changes
    _lastUnreadCount = count;
    const lines = badge.innerHTML.split('\n');
    lines[0] = `<span style="color:#fff">${count} unread${getModeTag()}</span>`;
    badge.innerHTML = lines.join('\n');
  }, 2000);

  // ─── Auto-fill on page load for already-active contact ────────────────────
  const _initCid = getActiveCid();
  if (_initCid && !manualMode) setTimeout(() => autoFill(_initCid), 1000);

  // ─── Auto-fill on manual sidebar click ────────────────────────────────────
  document.addEventListener('click', e => {
    const contact = e.target.closest('li.smsContactContainer');
    if (!contact) return;
    const cid = contact.getAttribute('smscontactid');
    if (!cid) return;
    // Manual mode — no AI; Autopilot — it controls its own navigation via navigate(), don't double-trigger
    if (manualMode) return;
    if (autopilot) return;
    // Short delay so the page registers the active contact before we read it
    setTimeout(() => autoFill(cid), 400);
  });

  // ─── Key Handler ──────────────────────────────────────────────────────────
  document.addEventListener('keydown', e => {
    const key     = e.key;
    const cid     = getActiveCid();
    const ta      = cid ? getTextarea(cid) : null;
    const focused = ta && document.activeElement === ta;
    const hasContent = focused && ta.value.trim().length > 0;

    // ── Enter in reply box ────────────────────────────────────────────────
    if (key === 'Enter' && focused && hasContent) {

      // Shift+Enter → always send + add folders + advance (manual override)
      if (e.shiftKey) {
        e.preventDefault();
        const msgCountBeforeShift = getMessageCount(cid);
        sms.client.main.send(parseInt(cid, 10));
        lastSuggestion = null;
        delete aiCache[cid]; // clear cache so next visit gets fresh AI call
        folderOpInProgress = true; // Block autoFill during folder add
        (async () => {
          // Wait for send to confirm (textarea clears OR message appears in thread), up to 40s
          try {
            await waitFor(() => !ta.value.trim() || getMessageCount(cid) > msgCountBeforeShift, 40000);
            // Clear textarea if it froze but message sent
            if (ta.value.trim() && getMessageCount(cid) > msgCountBeforeShift) {
              ta.value = '';
              ta.dispatchEvent(new Event('input', { bubbles: true }));
              console.log('[SMS] Send confirmed via thread (textarea freeze — cleared)');
            }
          } catch (_) { /* send may have gone through anyway, continue */ }
          await delay(400);

          // Old account: auto-check/delete notes before adding folders
          if (_detectedWsjFolder === WSJ_OLD_FOLDER) {
            setBadge('⟳ checking notes on WSJ...', '#4af');
            try {
              const noteResult = await checkAndDeleteNote(cid);
              if (noteResult.hadNote) { setBadge('✓ note deleted — adding folders...', '#4c4'); await delay(400); }
              else { setBadge('✓ no note — adding folders...', '#4c4'); await delay(200); }
            } catch (err) {
              console.error('[Note Check] Failed:', err);
              setBadge('⚠ note check failed — adding folders anyway...', '#fa0');
              await delay(400);
            }
          }

          setBadge('⟳ adding folders...', '#4af');
          let foldersOk = false;
          try {
            await addToFolders(cid);
            foldersOk = true;
            setBadge('✓ folders added', '#4c4');
            await delay(1200);
          } catch (err) {
            console.error('[SMS] Folder error:', err);
            setBadge('⚠ folder add failed — use Shift+` to retry', '#f44');
            await delay(2500);
          }
          folderOpInProgress = false; // Unblock autoFill
          if (autopilot && autopilotPaused) {
            if (foldersOk) { const rk = autopilotReview ? 'Ctrl+Shift+R' : 'Ctrl+Shift+P'; setBadge(`✓ sent + folders — ${rk} to resume`, '#4c4'); }
            else pauseAutopilot('FOLDER ADD FAILED — add manually before continuing');
          }
          else if (!manualMode) autoAdvance();
        })();
        return;
      }

      // Plain Enter → let native handler send, then:
      // if AI said addFolders, trigger folder add; always auto-advance
      // AP Review: never auto-add folders on Enter — user decides via Shift+` after checking notes
      const shouldAddFolders = autopilotReview ? false : (lastSuggestion?.addFolders === true);
      lastSuggestion = null;
      delete aiCache[cid]; // clear cache so next visit gets fresh AI call

      // Snapshot message count to detect send even if textarea doesn't clear (platform freeze)
      const msgCountBeforeSend = getMessageCount(cid);
      const checkSent = setInterval(() => {
        if (!ta.value.trim() || getMessageCount(cid) > msgCountBeforeSend) {
          clearInterval(checkSent);
          // If textarea still has text but message appeared in thread, clear it
          if (ta.value.trim() && getMessageCount(cid) > msgCountBeforeSend) {
            ta.value = '';
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            console.log('[SMS] Send confirmed via thread (textarea freeze detected — cleared manually)');
          }
          if (shouldAddFolders) {
            (async () => {
              folderOpInProgress = true;
              await delay(400);

              // Old account: auto-check/delete notes before adding folders
              if (_detectedWsjFolder === WSJ_OLD_FOLDER) {
                setBadge('⟳ checking notes on WSJ...', '#4af');
                try {
                  const noteResult = await checkAndDeleteNote(cid);
                  if (noteResult.hadNote) {
                    setBadge('✓ note deleted — adding folders...', '#4c4');
                    await delay(400);
                  } else {
                    setBadge('✓ no note — adding folders...', '#4c4');
                    await delay(200);
                  }
                } catch (err) {
                  console.error('[Note Check] Failed:', err);
                  setBadge('⚠ note check failed — adding folders anyway...', '#fa0');
                  await delay(400);
                }
              }

              setBadge('⟳ adding folders...', '#4af');
              try {
                await addToFolders(cid);
                setBadge('✓ folders added', '#4c4');
                await delay(1200);
              } catch (err) {
                console.error('[SMS] Folder error:', err);
                folderOpInProgress = false;
                if (autopilot) { pauseAutopilot('FOLDER ADD FAILED — add manually before continuing'); return; }
                setBadge('⚠ folder add failed — use Shift+` to retry', '#f44');
                await delay(2500);
              }
              folderOpInProgress = false;
              if (autopilot && !autopilotPaused) { await delay(500); autopilotNext(); }
              else if (autopilot && autopilotPaused) { const rk = autopilotReview ? 'Ctrl+Shift+R' : 'Ctrl+Shift+P'; setBadge(`✓ sent — ${rk} to resume`, '#4c4'); }
              else if (!manualMode) autoAdvance();
            })();
          } else {
            if (autopilot && !autopilotPaused) { setTimeout(() => autopilotNext(), 500); }
            else if (autopilot && autopilotPaused) { const rk = autopilotReview ? 'Ctrl+Shift+R' : 'Ctrl+Shift+P'; setBadge(`✓ sent — ${rk} to resume`, '#4c4'); }
            else if (!manualMode) autoAdvance();
          }
        }
      }, 100);
      // 35s timeout: gives the client plenty of time to unfreeze and send
      setTimeout(() => {
        clearInterval(checkSent);
        if (ta.value.trim()) {
          setBadge('⚠ send not confirmed — check message sent, then press \\ or [ to continue', '#fa0');
          if (autopilot) pauseAutopilot('send not confirmed — check if message went through');
        }
      }, 35000);

      return; // let native send handler fire
    }

    // ── Autopilot toggle (Ctrl+Shift+P) ─────────────────────────────
    if ((key === 'p' || key === 'P') && e.ctrlKey && e.shiftKey) {
      e.preventDefault();
      // If autopilot is running, stop it (go to AI mode); otherwise start it
      if (autopilot && !autopilotPaused) switchMode('ai');
      else switchMode('autopilot');
      return;
    }

    // ── Manual mode toggle (Ctrl+Shift+M) ─────────────────────────────
    if ((key === 'm' || key === 'M') && e.ctrlKey && e.shiftKey) {
      e.preventDefault();
      switchMode(manualMode ? 'ai' : 'manual');
      return;
    }

    // ── AP Review toggle (Ctrl+Shift+R) ─────────────────────────────
    if ((key === 'r' || key === 'R') && e.ctrlKey && e.shiftKey) {
      e.preventDefault();
      if (autopilot && !autopilotPaused && autopilotReview) switchMode('ai');
      else switchMode('apreview');
      return;
    }

    // ── Shift+` → standalone dual-folder add (works in any mode) ──────
    if (e.code === 'Backquote' && e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      e.preventDefault();
      if (!cid) return;
      if (folderOpInProgress) { setBadge('⟳ folder add already in progress...', '#fa0'); return; }
      folderOpInProgress = true;
      (async () => {
        // Old account: auto-check/delete notes before adding folders
        if (_detectedWsjFolder === WSJ_OLD_FOLDER) {
          setBadge('⟳ checking notes on WSJ...', '#4af');
          try {
            const noteResult = await checkAndDeleteNote(cid);
            if (noteResult.hadNote) { setBadge('✓ note deleted — adding folders...', '#4c4'); await delay(400); }
            else { setBadge('✓ no note — adding folders...', '#4c4'); await delay(200); }
          } catch (err) {
            console.error('[Note Check] Failed:', err);
            setBadge('⚠ note check failed — adding folders anyway...', '#fa0');
            await delay(400);
          }
        }
        setBadge('⟳ adding folders...', '#4af');
        try {
          await addToFolders(cid);
          setBadge('✓ folders added', '#4c4');
        } catch (err) {
          console.error('[SMS] Folder error:', err);
          setBadge('⚠ folder add failed — try again with Shift+`', '#f44');
        }
        folderOpInProgress = false;
      })();
      return;
    }

    const navKeys = [UP_KEY, DOWN_KEY, BACK_KEY];
    if (!navKeys.includes(key)) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    e.preventDefault();
    if (key === BACK_KEY) { navigateBack(); return; }
    navigate(key === UP_KEY ? 'up' : 'down');
  });

  // ═══════════════════════════════════════════════════════════════════════════
  //  INITIALIZATION — ACE SPLASH
  // ═══════════════════════════════════════════════════════════════════════════
  setTimeout(() => {
    createAccountIndicator();
    createMiniMascot();
    showAceSplash((acctLabel) => {
      setBadge(`Slice (${acctLabel}) — MANUAL MODE`, '#f90');
      updateMiniMascot();
      console.log(`[ACE Slice] Ready — ${acctLabel} account`);
    });
  }, 800);

})();