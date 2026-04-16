// ==UserScript==
// @name         ACE - Auto Chat Engine v1.1
// @namespace    http://tampermonkey.net/
// @version      1.1
// @description  ACE: AI-powered SMS auto-pilot for multiple clients (ASB, Mutual of Omaha). Account selector on load, auto-detection from thread content.
// @match        https://sms.jobosaurus.com/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @connect      api.anthropic.com
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ─── YOUR API KEY ─────────────────────────────────────────────────────────
  // The key is stored securely by Tampermonkey (GM_setValue) — NOT in this file.
  // On first run, the account-picker splash will prompt you to paste your key.
  // To change it later, use the "Reset API key" link on the splash, or the
  // Tampermonkey menu command "ACE · Set / Reset Anthropic API Key".
  let ANTHROPIC_API_KEY = (typeof GM_getValue === 'function')
    ? (GM_getValue('ANTHROPIC_API_KEY', '') || '')
    : '';

  // ─── Key Bindings ─────────────────────────────────────────────────────────
  const UP_KEY   = '\\';   // navigate to previous unread
  const DOWN_KEY = '[';    // navigate to next unread
  const BACK_KEY = ']';    // go back to previous contact
  const MAX_HISTORY = 50;

  // ═══════════════════════════════════════════════════════════════════════════
  //  CLIENT CONFIGURATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  // ─── ASB System Prompt ────────────────────────────────────────────────────
  const ASB_SYSTEM_PROMPT = `You assist Olivia, an independent recruiter texting candidates about insurance sales roles at American Senior Benefits (ASB) via SMS.

## Role Facts
- ASB: well-established, nationwide insurance organization. Seniors + Medicare supplements, life insurance, long-term care, annuities, retirement planning. Multiple top-rated carriers.
- 1099 independent contractor — commission-based + performance bonuses. Strong earning potential. NEVER quote specific dollars, percentages, or ranges.
- NOT W-2, NOT salaried, NOT hourly. NEVER imply traditional employment or benefits.
- NOT fully remote. Flexible schedule. Training provided, no experience needed. Health & Life license required (or willingness to obtain — ASB helps). Leads provided.
- Olivia is an independent recruiter, NOT an ASB employee. Her messages appear as [RECRUITER]. Tone: professional, friendly, SHORT.
- Olivia does NOT know: exact compensation breakdown, office addresses, commission percentages, territory details, day-to-day specifics. Redirect to hiring team.

## Flow (Simple Handoff — NO multi-stage funnel)
1. Candidate shows interest → script handles handoff message + folder add (AI returns reply: null, template: "handoff", addFolders: true)
2. ASB local team reaches out directly
3. Escalation: Lyn Godfrey at Lgodfrey@americanseniorbenefits.com (delayed follow-ups only)

## Knowledge Base
Keep answers vague and warm. Answer with what Olivia knows + nudge toward hiring team. Default for unknown specifics: "I don't have all those details since I'm an independent recruiter, but the hiring team can go over that with you."

PAY: Commission-based + bonuses. Strong earning potential. Push for numbers → "The hiring team can walk you through the full compensation breakdown."
LOCATION: "The local recruitment team can share more about offices in your area."
EXPERIENCE/TRAINING: No experience needed. Full training + licensing support during onboarding.
LICENSING: Health & Life license required (or willingness to obtain). ASB helps during onboarding.
SCHEDULE: Flexible. Hiring team can go over specifics.
PART-TIME: "Flexible, full-time opportunity. Hiring team can discuss scheduling."
JOB DUTIES / PRODUCTS: "You'd work with seniors on Medicare, life insurance, retirement planning, and other financial needs. ASB works with multiple carriers. Hiring team can go over the full details."
LEADS: Provided — no self-generating. Specifics → hiring team.
REMOTE/WFH: Not fully remote. If dealbreaker → polite close. If just asking → answer + nudge.
DOOR-TO-DOOR / COLD CALLING: "I don't have all the day-to-day specifics, but leads are provided. Hiring team can walk you through what prospecting looks like."
BENEFITS: "This is a 1099 role, so the benefits structure is different from W-2. Hiring team can go over details." Do NOT promise benefits/PTO.
CAREER GROWTH: "Strong growth potential — agent to sales management to agency ownership. Hiring team can walk you through the career path."
COST/FEES: "I don't have all those details, but the hiring team can walk you through everything so there are no surprises. Would you like me to have them reach out?" template: "custom"
INSURANCE QUESTION: Answer honestly. If they reject sales/insurance → polite close. If just asking → answer + continue.
COMPANY WEBSITE: careers.americanseniorbenefits.com — share when asked for info/verification. template: "custom"

## Follow-up Threads (already handed off)
RECENT (~3 days): "A recruiter should be reaching out soon. If you don't hear back, contact Lyn Godfrey at Lgodfrey@americanseniorbenefits.com."
OVERDUE (3+): "Sorry about the delay! You can reach out directly to Lyn Godfrey at Lgodfrey@americanseniorbenefits.com."

## Special Cases
IDENTITY/SCAM: "This is legitimate! I'm Olivia, an independent recruiter for American Senior Benefits." + offer info.
BOT CHECK: "Yes, I'm real! I'm Olivia, an independent recruiter."
WHO IS THIS: "Hi! I'm Olivia, an independent recruiter. I reached out about an insurance sales role with ASB."
HOW GOT NUMBER (friendly): "Found your resume on a job board we use." + ask if interested.
HOW GOT NUMBER (hostile): Same answer, no pitch. template: "ignore", reply: null.
NEGATIVE/DISENGAGED: Wrong number, rude, hostile, STOP, non-English, busy → template: "ignore", reply: null.
CONDITIONAL + INCOMPATIBLE / W-2 REQUIREMENT: "This is a 1099 commission-based role, so it may not be the right fit. Best of luck!" template: "ignore"
SOFT DECLINE: "No problem! Feel free to reach back out whenever." template: "ignore"
AMBIGUOUS: confidence: "low". "Just checking — still interested in learning more?"
REFERRAL: "Have them text me at this number." template: "custom"
CALL ME: Redirect to hiring team. template: "custom"
ALREADY APPLIED: "Great, sounds like you're already in the process! Best of luck!" template: "ignore"
MLM/PYRAMID: "No, this is legitimate with American Senior Benefits — well-established nationwide. Hiring team can walk you through everything." + ask if interested. template: "custom"
REJECTION OF SALES/INSURANCE: "No problem! Best of luck!" template: "ignore". Do NOT convince.
PAY OBJECTION (rude): template: "ignore", reply: null.
PAY OBJECTION (polite): "I understand! Commission-based may not be the right fit. Best of luck!" template: "ignore"

STALE: 4+ days, handed off → re-engage + mention Lyn Godfrey. 4+ days, only outreach → treat as fresh. 3+ weeks → completely fresh.

## Tone Rules
- NEVER use "Reply YES" or "Reply" + any keyword as a call-to-action. That phrasing is only for the initial outreach template — custom replies must sound conversational and natural, e.g. "Would you like me to have them reach out?" or "Are you interested in moving forward?"
- Keep replies SHORT — 1-3 sentences max. SMS costs money.

## Response Format
{"reply":"text or null","template":"handoff|custom|ignore","addFolders":true/false,"confidence":"high|medium|low","note":"brief reason"}

## Rules
- template "ignore": reply: null = silent skip. reply: "text" = polite close filled for review.
- Keep replies SHORT. NEVER fabricate specifics. NEVER include candidate's personal info.
- NEVER say W-2, salaried, hourly, or promise benefits/PTO.
- TIME AWARENESS: Compare timestamps to [CURRENT DATE/TIME]. Don't reference future times that have already passed.`;

  // ─── MOO System Prompt ────────────────────────────────────────────────────
  const MOO_SYSTEM_PROMPT = `You assist Brady, an independent recruiter texting candidates about Financial Sales Representative positions at Mutual of Omaha Advisors via SMS.

## Role Facts
- Mutual of Omaha Advisors: well-established financial services organization.
- W-2 position with benefits. Compensation: $36K base + uncapped commissions + bonuses + full benefits (401K, health, dental, vision).
- Full-time, office-based (NOT remote). Locations nationwide. Paid training provided — company covers training + licensing costs. No cost to candidate.
- No prior experience required. Relationship-driven role with long-term growth potential.
- Brady is an independent recruiter, NOT a Mutual of Omaha employee. His messages appear as [RECRUITER].
- Brady does NOT know: specific office addresses (only candidate's state from metadata), exact commission rates/bonus structures, or specific benefit details beyond the above. Redirect specifics to recruiting team.
- Tone: professional, friendly, brief. SMS costs money — keep replies SHORT.

## Funnel (2-Step): Info Blurb → Scheduling Link

### Funnel Position Detection
- INFO BLURB SENT: Any [RECRUITER] message contains the LITERAL text "$36K" or "$36,000" or "uncapped commissions". The initial outreach message (which mentions "base pay" or "bonuses" or "benefits" in general terms) does NOT count — only messages with the exact dollar figure "$36K" or phrase "uncapped commissions" mean the blurb was sent.
- SCHEDULING LINK SENT: Any [RECRUITER] message contains "joinmutualofomaha.com".

### STEP 1 — Info Blurb
When: Candidate shows interest ("yes", "interested", "sure", availability times). Template: "info_blurb", addFolders: false.
Reply: null. The script inserts the blurb — do NOT write a lead-in like "Great! Here are the details:" because the blurb already has its own opening. ONLY use reply with info_blurb if they asked a question NOT covered by the blurb (then your answer goes before it).

### STEP 2 — Scheduling Link
ABSOLUTE RULE: template "scheduling_link" is ONLY allowed when BOTH conditions are true:
1. The info blurb HAS ALREADY BEEN SENT — confirmed by "$36K" or "uncapped commissions" appearing in a prior [RECRUITER] message
2. The candidate has positively confirmed AFTER seeing the blurb details

If the info blurb has NOT been sent yet, you MUST return template: "info_blurb" — NEVER "scheduling_link". No exceptions. Not even if the candidate sounds eager, gives availability, says "sign me up", or asks to schedule. Eagerness does NOT skip steps.
Template: "scheduling_link", addFolders: true. Reply: null (script inserts link).

### POST-STEP-2 (scheduling link already sent)
- "Thanks" / "Got it" / acknowledgments → template: "ignore", reply: null
- Scheduling questions → "Once you schedule at the link, check your email for a confirmation. You'll get a call at the time you booked."
- "Already scheduled" / mentions appointment time → CHECK TIMESTAMPS vs [CURRENT DATE/TIME]:
  a) Appointment still upcoming: "Perfect! Check your email for a confirmation. Best of luck!" template: "ignore"
  b) Appointment already passed: "That's great to hear! Hopefully the call went well. Best of luck!" template: "ignore"
  c) Unclear: "That's great to hear! Check your email for any follow-up details. Best of luck!" template: "ignore"
- "I never got a call" / missed call → "I'm sorry about that! You can reschedule at the link I sent and I'll let the team know." template: "custom"
- "No times available" / calendar full → confidence: "low", note: "No calendar slots — verify link has open times." Pauses autopilot.
- "Link not working" → "I'm sorry about that! Try opening it on a computer or different browser and let me know if you're still having trouble!" template: "custom"

## Knowledge Base

COMPENSATION:
- Post-info-blurb only: "The $36K is the starting base — uncapped commissions, bonuses, and full benefits are on top of that. The recruiting team can walk you through the full breakdown."
- NEVER quote specific dollar ranges, commission percentages, or bonus amounts beyond $36K base.

REMOTE/WFH:
- Just asking: "This is an office-based position, not remote. The recruiting team will walk you through available locations in your area."
- Dealbreaker (states remote is required): "I understand! This role is office-based, so it may not be the best fit. Best of luck!" template: "ignore"
- Asking about remote ≠ dealbreaker. Only close if they STATE it's a requirement.

LOCATION:
- Use candidate's STATE from metadata if they ask: "I have you in [State]. The recruiting team will walk you through available options."
- No specific addresses or cities. If different state: "No problem — locations are nationwide."

JOB DUTIES:
- "Financial Reps work directly with clients on life insurance, retirement planning, and other financial strategies. It's a relationship-driven role."
- Outside sales / cold calling questions: "I don't have all the day-to-day specifics, but it's an in-office role. The recruiting team can walk you through exactly what it looks like."

INSURANCE QUESTION ("Is this insurance?" / "Is this insurance sales?"):
- "It's more of a financial advisory role — you'd work with clients on life insurance, retirement planning, and other financial strategies."
- If they reject insurance/sales outright: "No problem! Best of luck!" template: "ignore". Do NOT convince.

EXPERIENCE: "No prior experience needed — full training provided, company covers licensing."

TRAINING: "Training is fully paid — you're paid during training and the company covers all licensing costs."

LICENSING:
- Life & Health (L&H) license to start. Company pays for everything. Paid during training.
- Series 6, 63, and eventually 65 as you grow (investments, mutual funds, financial planning). Company supports all of it.
- "What licenses?" → "You'd start with a Life & Health license — company covers all costs. As you grow, you'd get Series 6, 63, and 65 for investment services. Does that work for you?"

BENEFITS: "Full benefits — health, dental, vision, 401K, and more. Recruiting team can go over the full package."

HOURS/SCHEDULE: "Full-time role. Recruiting team can go over specific hours."

PART-TIME: "This is full-time. Recruiting team would know about part-time options."

CAREER GROWTH: "Strong long-term growth potential. Recruiting team can walk you through the career path."

CAPTIVE VS. INDEPENDENT:
- This IS captive (Mutual of Omaha products), but there's a path to independence over time.
- If asked: Answer honestly, mention growth path, ask if that works. template: "custom"
- If conditional ("only if non-captive"): Answer honestly, ask if it still works. Do NOT send scheduling link until confirmed.

SALARY OBJECTION ($36K too low):
- POLITE: "I completely understand! Unfortunately the starting base is set at $36K, so it may not be the right fit. Best of luck!" template: "ignore"
- RUDE/DISMISSIVE: template: "ignore", reply: null

## Special Cases

IDENTITY/SCAM: "This is legitimate! I'm Brady, an independent recruiter for Mutual of Omaha Advisors." + ask if interested.
BOT CHECK: "Yes, I'm a real person! I'm Brady, recruiting for Mutual of Omaha Advisors." + offer info.
WHO IS THIS: "Hi! I'm Brady, recruiting for a Financial Sales Rep role with Mutual of Omaha Advisors." + ask if interested.
HOW GOT NUMBER (friendly): "We found your resume on a job board we use to source candidates." + ask if interested.
HOW GOT NUMBER (hostile): Same answer, no pitch. template: "ignore", reply: null.

NEGATIVE/DISENGAGED: Wrong number, rude, hostile, sarcastic, mocking, STOP, non-English, busy, photo request → template: "ignore", reply: null.
NOT INTERESTED: Polite → "No problem! Best of luck!" template: "ignore". Blunt/just "no" → reply: null.

COST/MLM/PYRAMID SCHEME: "No cost at all — this is a legitimate W-2 position. The company covers training, licensing, everything." + ask if interested. template: "custom".
REJECTION OF SALES/INSURANCE: "No problem! Best of luck!" template: "ignore". Do NOT convince.
CALL ME: "The recruiting team would be the best people to speak with. Would you like me to send the details so you can set up a call?" (send info blurb if not sent)
SOFT DECLINE: "No problem! Feel free to reach back out whenever you're ready." template: "ignore"
ALREADY APPLIED: "Great, sounds like you're already in the process! Best of luck!" template: "ignore"
REFERRAL: "Have them text me at this number!"

STALE (4+ days gap): Info blurb sent → "Just checking back in — still interested in scheduling?" Only outreach sent → treat as fresh. 3+ weeks → completely fresh.

## Follow-Up Threads
Candidates who already went through the funnel. Follow-up message re-sends calendar link ("just circling back" + joinmutualofomaha.com link).
- IMPORTANT: Do NOT return template "scheduling_link" in follow-ups — use "custom" instead. addFolders: false.
- Interested / availability → "You can schedule at the link above. Check email for confirmation." template: "custom"
- Already booked → Same time-awareness rules as POST-STEP-2.
- Role questions → Answer from KB, nudge toward booking.
- Not interested / STOP → template: "ignore"
- Missed call → "Sorry about that! You can reschedule at the link above."
- No slots / link issues → Same as POST-STEP-2.

## PRE-INFO-BLURB QUESTIONS
The info blurb covers: $36K base + commissions + bonuses + benefits + 401K, W-2, paid training, office-based/not remote, nationwide locations, job duties.

- Question answered by blurb (comp, pay, benefits, duties, remote, insurance question): Just send the blurb. Return template: "info_blurb", reply: null. The blurb answers it — no need to add anything.
- Question NOT answered by blurb (licensing, captive, location, career growth): Answer briefly from KB + return template: "info_blurb" so blurb is appended after your answer.

## POST-INFO-BLURB QUESTIONS
A) QUESTION ONLY (no confirmed interest): Answer from KB + ask if that works. template: "custom", addFolders: false. Wait for confirmation.
B) CONFIRMED INTEREST + QUESTION: Answer briefly, end with "you can schedule a quick intro call here:" template: "scheduling_link", addFolders: true. Script appends URL.
C) CONFIRMED INTEREST (no question): template: "scheduling_link", addFolders: true.
DEFAULT: When unsure → scenario A. Better to have one extra exchange than send the link prematurely.

## Response Format
Respond ONLY with valid JSON:
{"reply":"text or null","template":"info_blurb|scheduling_link|custom|ignore","addFolders":true/false,"confidence":"high|medium|low","note":"brief reason"}

## Rules
- template "ignore": reply: null = silent skip. reply: "text" = polite close filled for review.
- If reply + "info_blurb": script appends full blurb after reply. If reply + "scheduling_link": script appends just the URL + follow-up after reply (your reply MUST end leading into the link).
- addFolders: true ONLY with "scheduling_link"
- Keep replies SHORT (2-3 sentences max)
- NEVER fabricate specifics not in this prompt
- NEVER include candidate's personal info in replies
- NEVER reference candidate's state or location unless they specifically ask about offices or where they'd be working. Mentioning a timezone (CST, EST, PST, etc.) is NOT a location question — it's just a time reference. Do NOT reply with "I have you in [State]" just because they mentioned a timezone.
- NEVER return template "scheduling_link" unless "$36K" or "uncapped commissions" appears in a prior [RECRUITER] message. If it doesn't appear, the blurb hasn't been sent — use "info_blurb" instead. This is the #1 most important rule.
- NEVER skip the info blurb step. Even if the candidate sounds eager, ready, gives availability, says "sign me up", or asks to interview — if the blurb hasn't been sent, return "info_blurb". The candidate MUST see the role details before getting the scheduling link.
- TIME AWARENESS: Compare message timestamps to [CURRENT DATE/TIME]. "Tomorrow" in a message from yesterday = today. If appointment time already passed, acknowledge it happened — don't say they'll "get a call."
- AVAILABILITY TIMES: Don't commit to their time. Scheduling is via the calendar link. If blurb not sent → template: "info_blurb", reply: null (blurb handles everything — no lead-in needed). If blurb sent → treat as confirmation, send "scheduling_link".`;

  // ─── Client Config Objects ────────────────────────────────────────────────
  const CLIENTS = {
    'asb': {
      id: 'asb',
      name: 'ASB',
      fullName: 'American Senior Benefits',
      recruiterName: 'Olivia',
      emoji: '\u{1F31F}',
      tagline: 'Olivia \u2022 Insurance Sales',
      color: '#e67e22',
      btnColor: '#e67e22',
      gradient: 'linear-gradient(135deg, #e67e22 0%, #f39c12 100%)',
      folderIds: ['125706'],
      systemPrompt: ASB_SYSTEM_PROMPT,
      funnelType: 'handoff',
      // Thread detection: strings to look for in outreach messages
      threadDetectors: ['american senior benefits', 'medicare and retirement'],
      // Thread load check: how to know the thread has loaded
      threadLoadWords: ['recruiting', 'benefits', 'olivia'],
      // Templates
      templates: {
        handoff: "Great. I'll forward your resume to the local recruitment team. They'll contact you soon to go over everything in more detail and answer any questions."
      },
      // Keyword classification (ASB uses keyword-first approach)
      interestedExact: ['yes', 'sure', 'interested', "i'm interested", 'im interested', 'yea', 'yeah', 'absolutely', 'definitely', 'please do', 'yes please', 'sure thing', 'sounds great', 'lets do it', "let's do it", 'yes i am', 'yes im interested', "yes i'm interested"],
      interestedPartial: ['interested', 'go ahead', 'move forward', 'next step', 'sign me up', 'count me in'],
      notInterestedExact: ['no', 'no thanks', 'not interested', 'not for me', 'pass', 'not right now', 'nope', 'nah', 'no thank you', 'no way', 'hard pass', 'im good', "i'm good"],
      notInterestedPartial: ['not interested', 'not for me', 'not looking', 'not available', 'no thank', "don't want", 'dont want', 'not open', 'if not then no', 'then no', 'if not no'],
      notInterestedRegex: /\b(no longer interested|not a good fit|don't think so|decline|rejected|rather not|remove me|take me off|stop texting)\b/i,
      acknowledgmentPatterns: ['thanks', 'thank you', 'got it', 'will do', "i'll check", "i'll review", 'thanks for', 'appreciate', 'thx', 'ty'],
      // Funnel detection
      detectFunnel(allRecruiterText) {
        const handoffSent = allRecruiterText.includes('forward your resume') || allRecruiterText.includes('local recruitment team');
        return { handoffSent };
      },
      // Pitch detection (to know if outreach was sent)
      pitchTriggers: [
        'recruiting for an insurance sales role with american senior benefits',
        'recruiting on behalf of american senior benefits',
        'medicare and retirement options',
        'training provided and a flexible schedule'
      ]
    },

    'moo-com': {
      id: 'moo-com',
      name: 'MOO (Com)',
      fullName: 'Mutual of Omaha - Com',
      recruiterName: 'Brady',
      emoji: '\u{1F981}',
      tagline: 'Brady \u2022 Financial Sales',
      color: '#3498db',
      btnColor: '#3498db',
      gradient: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
      folderIds: ['138442'],
      systemPrompt: MOO_SYSTEM_PROMPT,
      funnelType: 'two-step',
      threadDetectors: ['mutual of omaha'],
      threadLoadWords: ['brady', 'mutual', 'omaha', 'financial'],
      templates: {
        infoBlurb: "Here is a quick overview: this is a W2 role that starts with a $36K base salary, paid training, uncapped commissions, bonuses, and full benefits - including 401K. It's an office-based position (not remote), with locations that vary nationwide. The best fit depends on where you're located, and if you're interested, the recruiting team will walk you through the options in your area.\n\nFinancial Reps work directly with clients on life insurance, retirement planning, and other financial strategies. It's a relationship-driven role with long-term growth potential. Does that sound like something you'd be interested in?",
        schedulingLink: "Great! You can find more details and schedule a quick intro call here: www.joinmutualofomaha.com\n\nOnce you're scheduled, keep an eye on your email for a confirmation. You'll receive a call at the time you selected, so just make sure you're available to answer. Feel free to reach out if you have any questions!",
        schedulingLinkShort: "www.joinmutualofomaha.com\n\nOnce you're scheduled, keep an eye on your email for a confirmation. You'll receive a call at the time you selected, so just make sure you're available to answer. Feel free to reach out if you have any questions!"
      },
      detectFunnel(allRecruiterText) {
        const lower = allRecruiterText.toLowerCase();
        const infoBlurbSent = lower.includes('$36k') || lower.includes('$36,000') || lower.includes('36k base') || lower.includes('uncapped commissions');
        const schedulingLinkSent = lower.includes('joinmutualofomaha.com');
        return { infoBlurbSent, schedulingLinkSent };
      },
      pitchTriggers: ['mutual of omaha', 'financial sales rep', 'financial representative']
    },

    'moo-apply': {
      id: 'moo-apply',
      name: 'MOO (Apply)',
      fullName: 'Mutual of Omaha - Apply',
      recruiterName: 'Brady',
      emoji: '\u{1F981}',
      tagline: 'Brady \u2022 Financial Sales',
      color: '#2ecc71',
      btnColor: '#2ecc71',
      gradient: 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)',
      folderIds: ['138443'],
      systemPrompt: MOO_SYSTEM_PROMPT,
      funnelType: 'two-step',
      threadDetectors: ['mutual of omaha'],
      threadLoadWords: ['brady', 'mutual', 'omaha', 'financial'],
      templates: {
        infoBlurb: "Here is a quick overview: this is a W2 role that starts with a $36K base salary, paid training, uncapped commissions, bonuses, and full benefits - including 401K. It's an office-based position (not remote), with locations that vary nationwide. The best fit depends on where you're located, and if you're interested, the recruiting team will walk you through the options in your area.\n\nFinancial Reps work directly with clients on life insurance, retirement planning, and other financial strategies. It's a relationship-driven role with long-term growth potential. Does that sound like something you'd be interested in?",
        schedulingLink: "Great! You can find more details and schedule a quick intro call here: www.joinmutualofomaha.com/apply\n\nOnce you're scheduled, keep an eye on your email for a confirmation. You'll receive a call at the time you selected, so just make sure you're available to answer. Feel free to reach out if you have any questions!",
        schedulingLinkShort: "www.joinmutualofomaha.com/apply\n\nOnce you're scheduled, keep an eye on your email for a confirmation. You'll receive a call at the time you selected, so just make sure you're available to answer. Feel free to reach out if you have any questions!"
      },
      detectFunnel(allRecruiterText) {
        const lower = allRecruiterText.toLowerCase();
        const infoBlurbSent = lower.includes('$36k') || lower.includes('$36,000') || lower.includes('36k base') || lower.includes('uncapped commissions');
        const schedulingLinkSent = lower.includes('joinmutualofomaha.com');
        return { infoBlurbSent, schedulingLinkSent };
      },
      pitchTriggers: ['mutual of omaha', 'financial sales rep', 'financial representative']
    },

    'moo-careers': {
      id: 'moo-careers',
      name: 'MOO (Careers)',
      fullName: 'Mutual of Omaha - Careers',
      recruiterName: 'Brady',
      emoji: '\u{1F981}',
      tagline: 'Brady \u2022 Financial Sales',
      color: '#9b59b6',
      btnColor: '#9b59b6',
      gradient: 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
      folderIds: ['138431'],
      systemPrompt: MOO_SYSTEM_PROMPT,
      funnelType: 'two-step',
      threadDetectors: ['mutual of omaha'],
      threadLoadWords: ['brady', 'mutual', 'omaha', 'financial'],
      templates: {
        infoBlurb: "Here is a quick overview: this is a W2 role that starts with a $36K base salary, paid training, uncapped commissions, bonuses, and full benefits - including 401K. It's an office-based position (not remote), with locations that vary nationwide. The best fit depends on where you're located, and if you're interested, the recruiting team will walk you through the options in your area.\n\nFinancial Reps work directly with clients on life insurance, retirement planning, and other financial strategies. It's a relationship-driven role with long-term growth potential. Does that sound like something you'd be interested in?",
        schedulingLink: "Great! You can find more details and schedule a quick intro call here: www.joinmutualofomaha.com/careers\n\nOnce you're scheduled, keep an eye on your email for a confirmation. You'll receive a call at the time you selected, so just make sure you're available to answer. Feel free to reach out if you have any questions!",
        schedulingLinkShort: "www.joinmutualofomaha.com/careers\n\nOnce you're scheduled, keep an eye on your email for a confirmation. You'll receive a call at the time you selected, so just make sure you're available to answer. Feel free to reach out if you have any questions!"
      },
      detectFunnel(allRecruiterText) {
        const lower = allRecruiterText.toLowerCase();
        const infoBlurbSent = lower.includes('$36k') || lower.includes('$36,000') || lower.includes('36k base') || lower.includes('uncapped commissions');
        const schedulingLinkSent = lower.includes('joinmutualofomaha.com');
        return { infoBlurbSent, schedulingLinkSent };
      },
      pitchTriggers: ['mutual of omaha', 'financial sales rep', 'financial representative']
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  //  STATE
  // ═══════════════════════════════════════════════════════════════════════════

  let activeClient = null;        // current client config object
  let manualMode = true;
  let autopilot = false;
  let autopilotPaused = false;
  let lastSuggestion = null;
  let fillInProgress = 0;
  let fillInProgressCid = null;
  const FILL_LOCK_MS = 30000;
  let folderOpInProgress = false;
  const aiCache = {};
  const navHistory = [];
  let _lastAutopilotCid = null;
  const _skippedUnsub = new Set();
  let _audioCtx = null;
  let _pauseReminderTimer = null;
  let _autopilotPollTimer = null;

  // ═══════════════════════════════════════════════════════════════════════════
  //  ACCOUNT SELECTOR UI
  // ═══════════════════════════════════════════════════════════════════════════

  // ─── ACE SVG Mascot Strings ──────────────────────────────────────────────
  // Big mascot for popup (70px) — Style 4 Sunset Warm
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

  // Mini mascot for page buddy (36px)
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

  // Tiny face for account indicator (14px)
  const ACE_SVG_TINY = `<svg width="14" height="14" viewBox="0 0 120 120" style="vertical-align:middle;margin-right:4px">
    <rect x="25" y="30" width="70" height="65" rx="20" fill="currentColor"/>
    <circle cx="47" cy="52" r="10" fill="#fff"/><circle cx="73" cy="52" r="10" fill="#fff"/>
    <circle cx="49" cy="53" r="6" fill="#1e1b4b"/><circle cx="75" cy="53" r="6" fill="#1e1b4b"/>
    <circle cx="52" cy="50" r="2" fill="rgba(255,255,255,0.8)"/><circle cx="78" cy="50" r="2" fill="rgba(255,255,255,0.8)"/>
  </svg>`;

  // Star SVG for card accents (colored per account)
  function aceStarSVG(fill, stroke) {
    return `<svg width="22" height="22" viewBox="0 0 24 24" style="flex-shrink:0;filter:drop-shadow(0 0 4px ${fill})"><polygon points="12,2 14,9 21,9 15.5,13 17.5,20 12,16 6.5,20 8.5,13 3,9 10,9" fill="${fill}" stroke="${stroke}" stroke-width="0.5"/></svg>`;
  }

  // ─── Inject ACE Styles ──────────────────────────────────────────────────
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
      @keyframes aceShine { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
      @keyframes aceStarSpin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      .aceCard { position: relative; overflow: hidden; }
      .aceCard::after { content:''; position:absolute; top:0;left:0;right:0;bottom:0; background:linear-gradient(120deg,transparent 30%,rgba(255,255,255,0.07) 50%,transparent 70%); background-size:200% 100%; opacity:0; transition:opacity 0.3s; pointer-events:none; }
      .aceCard:hover::after { opacity:1; animation: aceShine 0.8s ease-out; }
      .aceCard:hover .aceStar { animation: aceStarSpin 1.5s ease-in-out; }
      #aceMiniMascot { transition: transform 0.2s, opacity 0.2s; }
      #aceMiniMascot:hover { transform: scale(1.12); }
      #aceMiniTooltip { position:absolute; bottom:100%; right:0; margin-bottom:6px; background:rgba(26,26,46,0.95); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:5px 10px; font-size:10px; color:#ccd6f6; white-space:nowrap; opacity:0; transition:opacity 0.2s; pointer-events:none; box-shadow:0 4px 12px rgba(0,0,0,0.3); font-family:system-ui,sans-serif; }
      #aceMiniMascot:hover #aceMiniTooltip { opacity:1; }
    `;
    document.head.appendChild(style);
  }

  function showAccountSelector(onSelect) {
    injectAceStyles();

    // Overlay with blur
    const overlay = document.createElement('div');
    overlay.id = 'smsAccountOverlay';
    Object.assign(overlay.style, {
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(10, 10, 30, 0.7)', backdropFilter: 'blur(6px)', WebkitBackdropFilter: 'blur(6px)',
      zIndex: '99999', display: 'flex', alignItems: 'center', justifyContent: 'center',
      animation: 'aceFadeIn 0.25s ease-out'
    });

    // Modal
    const modal = document.createElement('div');
    Object.assign(modal.style, {
      background: 'linear-gradient(145deg, #1a1a2e 0%, #2a1a2e 100%)',
      borderRadius: '20px', padding: '28px 24px 20px',
      maxWidth: '400px', width: '92%',
      boxShadow: '0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.05)',
      fontFamily: 'system-ui, -apple-system, sans-serif', color: '#fff',
      animation: 'aceSlideUp 0.35s ease-out'
    });

    // Header with big ACE mascot
    const header = document.createElement('div');
    Object.assign(header.style, { textAlign: 'center', marginBottom: '22px' });
    header.innerHTML = ACE_SVG_BIG;

    const title = document.createElement('div');
    title.textContent = 'ACE';
    Object.assign(title.style, {
      fontSize: '24px', fontWeight: '800', letterSpacing: '-0.5px', marginTop: '8px',
      background: 'linear-gradient(135deg, #fb923c, #f472b6, #a78bfa)',
      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
    });
    header.appendChild(title);

    const subtitle = document.createElement('div');
    subtitle.textContent = 'Which account are you on today?';
    Object.assign(subtitle.style, { fontSize: '12px', color: '#8892b0', marginTop: '4px' });
    header.appendChild(subtitle);
    modal.appendChild(header);

    // Step-1 container (account picker) + step-2 container (API key)
    const step1 = document.createElement('div');
    const step2 = document.createElement('div');
    step2.style.display = 'none';
    modal.appendChild(step1);
    modal.appendChild(step2);

    // pending selection: holds the client (or null for Manual) while user enters key
    let pendingSelection = undefined; // undefined = not selected yet
    let resetMode = false;

    function hasKey() {
      return ANTHROPIC_API_KEY && ANTHROPIC_API_KEY.startsWith('sk-ant-');
    }

    function goToStep2() {
      step1.style.display = 'none';
      step2.style.display = 'block';
      keyInput.value = '';
      keyError.textContent = '';
      setTimeout(() => keyInput.focus(), 50);
    }

    function goToStep1() {
      step2.style.display = 'none';
      step1.style.display = 'block';
    }

    // Account cards with star accents (step 1)
    const starColors = {
      'asb':         { fill: '#fde68a', stroke: '#fbbf24' },
      'moo-com':     { fill: '#93c5fd', stroke: '#60a5fa' },
      'moo-apply':   { fill: '#86efac', stroke: '#4ade80' },
      'moo-careers': { fill: '#d8b4fe', stroke: '#a78bfa' }
    };
    const cardContainer = document.createElement('div');
    Object.assign(cardContainer.style, { display: 'flex', flexDirection: 'column', gap: '8px' });

    Object.keys(CLIENTS).forEach(key => {
      const client = CLIENTS[key];
      const card = document.createElement('button');
      card.className = 'aceCard';
      Object.assign(card.style, {
        display: 'flex', alignItems: 'center', gap: '14px', width: '100%',
        padding: '13px 16px', border: 'none', borderRadius: '14px', cursor: 'pointer',
        background: client.gradient || client.btnColor,
        color: '#fff', textAlign: 'left', fontFamily: 'inherit',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
      });
      card.addEventListener('mouseenter', () => { card.style.transform = 'translateY(-2px) scale(1.01)'; card.style.boxShadow = '0 6px 20px rgba(0,0,0,0.3)'; });
      card.addEventListener('mouseleave', () => { card.style.transform = 'translateY(0) scale(1)'; card.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)'; });
      card.addEventListener('click', () => {
        if (hasKey()) {
          overlay.remove();
          onSelect(client);
        } else {
          pendingSelection = client;
          goToStep2();
        }
      });

      // Star accent
      const sc = starColors[key] || { fill: '#fff', stroke: '#ccc' };
      const starWrap = document.createElement('span');
      starWrap.className = 'aceStar';
      starWrap.innerHTML = aceStarSVG(sc.fill, sc.stroke);
      card.appendChild(starWrap);

      const textWrap = document.createElement('div');
      textWrap.innerHTML = `<div style="font-size:14px;font-weight:700;line-height:1.2;letter-spacing:-0.2px">${client.fullName}</div><div style="font-size:11px;font-weight:500;opacity:0.75;margin-top:1px">${client.tagline || client.name}</div>`;
      card.appendChild(textWrap);
      cardContainer.appendChild(card);
    });
    step1.appendChild(cardContainer);

    // Divider
    const divider = document.createElement('div');
    Object.assign(divider.style, { borderTop: '1px solid rgba(255,255,255,0.06)', margin: '14px 0 12px' });
    step1.appendChild(divider);

    // Manual mode button (doesn't need a key — skip straight through)
    const noneBtn = document.createElement('button');
    noneBtn.innerHTML = 'Manual Only <span style="opacity:0.5;font-weight:400">\u2014 nav keys only</span>';
    Object.assign(noneBtn.style, {
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      width: '100%', padding: '11px 16px',
      border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', cursor: 'pointer',
      fontSize: '12px', fontWeight: '600', color: '#6b7280',
      background: 'rgba(255,255,255,0.03)', fontFamily: 'inherit',
      transition: 'all 0.15s ease'
    });
    noneBtn.addEventListener('mouseenter', () => { noneBtn.style.background = 'rgba(255,255,255,0.06)'; noneBtn.style.color = '#9ca3af'; noneBtn.style.borderColor = 'rgba(255,255,255,0.1)'; });
    noneBtn.addEventListener('mouseleave', () => { noneBtn.style.background = 'rgba(255,255,255,0.03)'; noneBtn.style.color = '#6b7280'; noneBtn.style.borderColor = 'rgba(255,255,255,0.06)'; });
    noneBtn.addEventListener('click', () => { overlay.remove(); onSelect(null); });
    step1.appendChild(noneBtn);

    // ─── Step 2: API key input ───
    const keyLabel = document.createElement('div');
    keyLabel.textContent = 'Paste your Anthropic API key';
    Object.assign(keyLabel.style, { fontSize: '13px', color: '#e2e8f0', marginBottom: '4px', fontWeight: '600', textAlign: 'center' });
    step2.appendChild(keyLabel);

    const keyHelp = document.createElement('div');
    keyHelp.textContent = 'Starts with sk-ant-… · stored securely by Tampermonkey on this computer only';
    Object.assign(keyHelp.style, { fontSize: '10px', color: '#8892b0', marginBottom: '12px', lineHeight: '1.4', textAlign: 'center' });
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
    Object.assign(keyError.style, { fontSize: '11px', color: '#f87171', marginTop: '6px', minHeight: '14px', textAlign: 'center' });
    step2.appendChild(keyError);

    const saveBtn = document.createElement('button');
    saveBtn.textContent = 'Save & Continue';
    Object.assign(saveBtn.style, {
      display: 'block', margin: '10px auto 0', padding: '10px 28px', border: 'none', borderRadius: '12px', cursor: 'pointer',
      fontSize: '14px', fontWeight: '700', color: '#fff', fontFamily: 'inherit',
      background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
      boxShadow: '0 4px 15px rgba(6,182,212,0.3)', transition: 'all 0.15s'
    });
    saveBtn.addEventListener('mouseenter', () => { saveBtn.style.transform = 'translateY(-1px)'; });
    saveBtn.addEventListener('mouseleave', () => { saveBtn.style.transform = 'translateY(0)'; });
    step2.appendChild(saveBtn);

    // Back link on step 2 (for reset flow)
    const backLink = document.createElement('div');
    backLink.textContent = '← back';
    Object.assign(backLink.style, {
      fontSize: '10px', color: '#8892b0', marginTop: '10px', fontStyle: 'italic',
      cursor: 'pointer', userSelect: 'none', display: 'none', textAlign: 'center'
    });
    backLink.addEventListener('mouseenter', () => { backLink.style.color = '#cbd5e1'; });
    backLink.addEventListener('mouseleave', () => { backLink.style.color = '#8892b0'; });
    backLink.addEventListener('click', () => {
      resetMode = false;
      backLink.style.display = 'none';
      goToStep1();
    });
    step2.appendChild(backLink);

    function submitKey() {
      const val = (keyInput.value || '').trim();
      if (!val.startsWith('sk-ant-')) {
        keyError.textContent = 'Key must start with "sk-ant-". Copy from console.anthropic.com.';
        return;
      }
      ANTHROPIC_API_KEY = val;
      if (typeof GM_setValue === 'function') GM_setValue('ANTHROPIC_API_KEY', val);
      console.log('[MultiClient] API key saved to Tampermonkey storage');

      if (resetMode) {
        // Reset flow — return to account picker with a confirmation flash
        resetMode = false;
        backLink.style.display = 'none';
        keyInput.value = '';
        keyError.textContent = '';
        goToStep1();
        subtitle.textContent = '✓ key saved — which account are you on today?';
        subtitle.style.color = '#6ee7b7';
        setTimeout(() => {
          subtitle.textContent = 'Which account are you on today?';
          subtitle.style.color = '#8892b0';
        }, 1800);
      } else if (pendingSelection !== undefined) {
        // Normal first-run flow — user had already picked an account
        overlay.remove();
        onSelect(pendingSelection);
      } else {
        // No pending selection (user clicked Reset before picking an account and then submitted) — back to step 1
        goToStep1();
      }
    }
    saveBtn.addEventListener('click', submitKey);
    keyInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); submitKey(); } });

    // Footer
    const footer = document.createElement('div');
    footer.textContent = 'click the account tag to switch later';
    Object.assign(footer.style, { textAlign: 'center', fontSize: '10px', color: '#3a3a5a', marginTop: '14px', fontStyle: 'italic' });
    modal.appendChild(footer);

    // Subtle "Reset API key" link under the footer — matches existing aesthetic
    const resetLink = document.createElement('div');
    resetLink.textContent = 'Reset API key';
    Object.assign(resetLink.style, {
      textAlign: 'center', fontSize: '10px', color: '#3a3a5a', marginTop: '4px', fontStyle: 'italic',
      cursor: 'pointer', userSelect: 'none', textDecoration: 'underline',
      textDecorationColor: 'rgba(136,146,176,0.25)', transition: 'color 0.15s'
    });
    resetLink.addEventListener('mouseenter', () => { resetLink.style.color = '#8892b0'; });
    resetLink.addEventListener('mouseleave', () => { resetLink.style.color = '#3a3a5a'; });
    resetLink.addEventListener('click', () => {
      resetMode = true;
      backLink.style.display = 'block';
      goToStep2();
    });
    modal.appendChild(resetLink);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  }

  // Tampermonkey menu: let user reset/change the API key anytime (even outside the splash)
  if (typeof GM_registerMenuCommand === 'function') {
    GM_registerMenuCommand('ACE · Set / Reset Anthropic API Key', () => {
      const entered = prompt(
        'Paste your Anthropic API key (starts with sk-ant-…).\n' +
        'Leave blank and click OK to clear the saved key.'
      );
      if (entered === null) return;
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

  // ─── Account Indicator (bottom-left, tiny ACE face + name) ────────────
  let accountIndicator = null;

  function createAccountIndicator() {
    injectAceStyles();
    accountIndicator = document.createElement('div');
    accountIndicator.id = 'smsAccountIndicator';
    Object.assign(accountIndicator.style, {
      position: 'fixed', bottom: '44px', left: '10px', zIndex: '9999',
      fontFamily: 'system-ui, sans-serif', fontSize: '11px', fontWeight: '700',
      padding: '4px 10px', borderRadius: '6px', cursor: 'pointer',
      color: '#fff', transition: 'all 0.15s', display: 'flex', alignItems: 'center'
    });
    accountIndicator.title = 'Click to change account';
    accountIndicator.addEventListener('click', () => {
      showAccountSelector(client => {
        activeClient = client;
        updateAccountIndicator();
        updateMiniMascot();
        Object.keys(aiCache).forEach(k => delete aiCache[k]);
        lastSuggestion = null;
        if (client) {
          setBadge(`Switched to ${client.name}`, client.color);
        } else {
          manualMode = true;
          autopilot = false; autopilotPaused = false;
          setBadge('MANUAL ONLY \u2014 nav keys active', '#888');
          highlightModeBtn();
        }
      });
    });
    document.body.appendChild(accountIndicator);
  }

  function updateAccountIndicator() {
    if (!accountIndicator) return;
    if (activeClient) {
      accountIndicator.innerHTML = ACE_SVG_TINY + activeClient.name;
      accountIndicator.style.background = activeClient.btnColor;
      accountIndicator.style.color = '#fff';
    } else {
      accountIndicator.innerHTML = ACE_SVG_TINY + 'Manual Only';
      accountIndicator.style.background = '#555';
      accountIndicator.style.color = '#ccc';
    }
  }

  // ─── Mini Mascot (bottom-right page buddy near text box) ──────────────
  let miniMascotEl = null;

  function createMiniMascot() {
    injectAceStyles();
    miniMascotEl = document.createElement('div');
    miniMascotEl.id = 'aceMiniMascot';
    Object.assign(miniMascotEl.style, {
      position: 'fixed', bottom: '14px', right: '14px', zIndex: '9998',
      cursor: 'pointer', lineHeight: '0'
    });
    miniMascotEl.innerHTML = ACE_SVG_MINI + '<div id="aceMiniTooltip">ACE \u00B7 ready</div>';
    miniMascotEl.addEventListener('click', () => {
      showAccountSelector(client => {
        activeClient = client;
        updateAccountIndicator();
        updateMiniMascot();
        Object.keys(aiCache).forEach(k => delete aiCache[k]);
        lastSuggestion = null;
        if (client) {
          setBadge(`Switched to ${client.name}`, client.color);
        } else {
          manualMode = true;
          autopilot = false; autopilotPaused = false;
          setBadge('MANUAL ONLY \u2014 nav keys active', '#888');
          highlightModeBtn();
        }
      });
    });
    document.body.appendChild(miniMascotEl);
  }

  function updateMiniMascot() {
    if (!miniMascotEl) return;
    const tooltip = miniMascotEl.querySelector('#aceMiniTooltip');
    if (!tooltip) return;
    const acct = activeClient ? activeClient.name : 'No account';
    const mode = manualMode ? 'Manual' : (autopilot ? (autopilotPaused ? 'Paused' : 'Autopilot') : 'AI');
    tooltip.textContent = `ACE \u00B7 ${acct} \u00B7 ${mode}`;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  const delay = ms => new Promise(r => setTimeout(r, ms));

  function escHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function normalize(text) {
    return text.toLowerCase().replace(/[^a-z0-9\s']/gi, '').trim();
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

  // ─── Audio Alert ──────────────────────────────────────────────────────────
  function playAlert() {
    try {
      if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (_audioCtx.state === 'suspended') _audioCtx.resume();
      // Three-tone alert: louder and longer so it's noticeable
      [0, 0.3, 0.6].forEach((offset, i) => {
        const osc = _audioCtx.createOscillator();
        const gain = _audioCtx.createGain();
        osc.connect(gain);
        gain.connect(_audioCtx.destination);
        osc.frequency.value = i === 1 ? 1046 : 880; // middle beep higher pitch
        gain.gain.value = 0.5;
        osc.start(_audioCtx.currentTime + offset);
        osc.stop(_audioCtx.currentTime + offset + 0.2);
      });
    } catch (e) {
      // Fallback: try browser notification sound
      console.log('[MultiClient] Audio alert failed:', e.message);
    }
  }

  function pauseAutopilot(reason) {
    autopilotPaused = true;
    playAlert();
    setBadge(`⏸ PAUSED — ${reason}\nCtrl+Shift+P to resume`, '#f84');
    try { highlightModeBtn(); } catch (_) {}
    clearInterval(_pauseReminderTimer);
    _pauseReminderTimer = setInterval(() => {
      if (!autopilotPaused || !autopilot) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; return; }
      playAlert();
    }, 30000);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  DOM HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  function markAsRead(cid) {
    const el = document.querySelector(`#smsContactContainer_${cid}`);
    if (el) el.classList.remove('smsUnread');
    try { sms.client.main.activateContact(parseInt(cid, 10)); } catch (e) {}
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
    return !!document.querySelector(`#smsContactContainer_${cid} .smsContactStatusUnsubscribed`);
  }

  function getTextarea(cid) {
    return document.getElementById(`smsMessageInput_${cid}`);
  }

  function getMessagesForContact(cid) {
    const list = document.querySelector(`#smsMessagesList_${cid}`);
    if (!list) return [];
    return Array.from(list.querySelectorAll('li.smsMessageContainer'));
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  THREAD ANALYSIS
  // ═══════════════════════════════════════════════════════════════════════════

  function getContactState(cid) {
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

    const allMsgs = Array.from(list.querySelectorAll('li.smsMessageContainer'));

    // Find the LAST outreach to scope the thread to the current funnel cycle
    let startIdx = 0;
    if (activeClient?.pitchTriggers?.length) {
      const triggers = activeClient.pitchTriggers;
      allMsgs.forEach((li, i) => {
        if (!li.classList.contains('smsMessageOut')) return;
        const body = (li.querySelector('.smsMessageBody')?.textContent || '').toLowerCase();
        if (triggers.some(t => body.includes(t.toLowerCase()))) {
          startIdx = i;
        }
      });
    }

    const lines = allMsgs.slice(startIdx)
      .map(li => {
        const body = li.querySelector('.smsMessageBody')?.textContent.trim();
        if (!body) return null;
        const isOut = li.classList.contains('smsMessageOut');
        const timestamp = li.querySelector('.smsMessageTimestamp')?.textContent?.trim() || '';
        return `[${isOut ? 'RECRUITER' : 'CANDIDATE'}${timestamp ? ' @ ' + timestamp : ''}]: ${body}`;
      })
      .filter(Boolean);

    const now = new Date().toLocaleString('en-US', { timeZoneName: 'short' });
    lines.unshift(`[CURRENT DATE/TIME]: ${now}`);

    // Include candidate's state from sidebar for location questions
    const state = getContactState(cid);
    if (state) lines.unshift(`[CANDIDATE STATE]: ${state}`);

    return lines.join('\n');
  }

  function hasMessages(cid) {
    if (!activeClient) return false;
    const list = document.getElementById(`smsMessagesList_${cid}`);
    if (!list) return false;
    const msgs = list.querySelectorAll('li.smsMessageContainer');
    if (!msgs.length) return false;
    const firstMsg = (msgs[0]?.querySelector('.smsMessageBody')?.textContent || '').toLowerCase();
    const hasOutreach = activeClient.threadLoadWords.some(w => firstMsg.includes(w)) || msgs.length >= 2;
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

  function getLastCandidateMessage(cid) {
    const messages = getMessagesForContact(cid);
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].classList.contains('smsMessageIn')) {
        return (messages[i].querySelector('.smsMessageBody')?.textContent || '').trim();
      }
    }
    return '';
  }

  function getAllRecruiterText(cid) {
    const messages = getMessagesForContact(cid);
    if (!activeClient) {
      return messages
        .filter(li => li.classList.contains('smsMessageOut'))
        .map(li => (li.querySelector('.smsMessageBody')?.textContent || '').toLowerCase())
        .join(' ');
    }

    // Find the LAST outreach (initial template) to reset funnel on re-sends
    let lastOutreachIdx = -1;
    const triggers = activeClient.pitchTriggers || [];
    messages.forEach((li, i) => {
      if (!li.classList.contains('smsMessageOut')) return;
      const body = (li.querySelector('.smsMessageBody')?.textContent || '').toLowerCase();
      if (triggers.some(t => body.includes(t.toLowerCase()))) {
        lastOutreachIdx = i;
      }
    });

    // Only look at recruiter messages from the last outreach onward
    const startIdx = lastOutreachIdx > 0 ? lastOutreachIdx : 0;
    return messages.slice(startIdx)
      .filter(li => li.classList.contains('smsMessageOut'))
      .map(li => (li.querySelector('.smsMessageBody')?.textContent || '').toLowerCase())
      .join(' ');
  }

  // ─── ASB Thread Analysis (pitch detection) ────────────────────────────────
  function analyzeThreadASB(cid) {
    const messages = getMessagesForContact(cid);
    if (!messages.length) return { hasPitch: false, hasReply: false, alreadyReplied: false, handoffSent: false };

    let hasPitch = false;
    let lastPitchIndex = -1;
    let firstInboundAfterPitch = -1;

    messages.forEach((msg, i) => {
      const body = (msg.querySelector('.smsMessageBody')?.textContent || '').trim();
      const normalized = normalize(body);
      const isOutbound = msg.classList.contains('smsMessageOut');
      const isInbound = msg.classList.contains('smsMessageIn');

      if (isOutbound && !hasPitch) {
        if (activeClient.pitchTriggers.some(trigger => normalized.includes(normalize(trigger)))) {
          hasPitch = true;
          lastPitchIndex = i;
        }
      }

      if (isInbound && hasPitch && lastPitchIndex > -1 && firstInboundAfterPitch === -1 && i > lastPitchIndex) {
        firstInboundAfterPitch = i;
      }
    });

    // Check if handoff was already sent by looking at all recruiter text
    const allRecruiterText = getAllRecruiterText(cid);
    const handoffSent = activeClient.detectFunnel(allRecruiterText).handoffSent;

    return {
      hasPitch,
      hasReply: firstInboundAfterPitch > -1,
      alreadyReplied: lastMessageIsOutbound(cid) || handoffSent,
      handoffSent
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  LOCAL PRE-FILTER (skip API for obvious cases)
  // ═══════════════════════════════════════════════════════════════════════════

  // ─── Shared safe-ignore patterns ──────────────────────────────────────────
  const SAFE_IGNORE_PATTERNS = [
    /^(stop|cancel|quit|unsubscribe)$/i,
    /\b(not interested|no thanks|no thank you|no thx|nope)\b/i,
    /\b(wrong number|not my number|wrong person)\b/i,
    /\b(send (me )?(a |ur |your )?(pic|photo|selfie|picture))\b/i,
    /\b(remove me|take me off|don'?t (text|contact|message|call) me)\b/i,
    /\b(cease and desist|lose my number|leave me alone)\b/i,
  ];

  function localPreFilter(cid) {
    if (!activeClient) return null;

    const lastMsg = getLastCandidateMessage(cid);
    if (!lastMsg || !lastMsg.trim()) return null;
    const lastMsgLower = lastMsg.trim().toLowerCase().replace(/['']/g, "'");

    // If message contains a question mark, ALWAYS let AI handle
    if (lastMsgLower.includes('?')) return null;

    const allRecruiterText = getAllRecruiterText(cid);

    // ─── Shared: safe ignore patterns ───────────────────────────────────────
    for (const pat of SAFE_IGNORE_PATTERNS) {
      if (pat.test(lastMsgLower)) {
        return { reply: null, template: 'ignore', confidence: 'high', note: 'clear ignore (local)', addFolders: false };
      }
    }

    // ─── Shared: non-English detection ──────────────────────────────────────
    const nonAscii = lastMsg.replace(/[\x00-\x7F]/g, '').length;
    if (nonAscii > lastMsg.length * 0.4 && lastMsg.length > 5) {
      return { reply: null, template: 'ignore', confidence: 'high', note: 'non-English (local)', addFolders: false };
    }

    // ─── Client-specific pre-filter ─────────────────────────────────────────
    if (activeClient.funnelType === 'handoff') {
      return localPreFilterASB(cid, lastMsgLower, allRecruiterText);
    } else if (activeClient.funnelType === 'two-step') {
      return localPreFilterMOO(cid, lastMsgLower, allRecruiterText);
    }

    return null;
  }

  // ─── ASB Local Pre-Filter ─────────────────────────────────────────────────
  function localPreFilterASB(cid, lastMsgLower, allRecruiterText) {
    const c = activeClient;
    const normalizedMsg = normalize(lastMsgLower);
    const { handoffSent } = c.detectFunnel(allRecruiterText);

    // If handoff already sent, post-handoff replies are ignores
    if (handoffSent) {
      // Acknowledgments after handoff → ignore
      for (const ack of c.acknowledgmentPatterns) {
        if (normalizedMsg.includes(normalize(ack))) {
          return { reply: null, template: 'ignore', confidence: 'high', note: 'post-handoff acknowledgment (local)', addFolders: false };
        }
      }
      // Positive replies after handoff (e.g. "Ok", "Great", "Yes") → ignore
      for (const exact of c.interestedExact) {
        if (normalizedMsg === exact) {
          return { reply: null, template: 'ignore', confidence: 'high', note: 'post-handoff reply (local)', addFolders: false };
        }
      }
      // Anything else post-handoff → let AI handle (could be a question)
      return null;
    }

    // ─── Context: did recruiter recently close out? ───
    // If the most recent recruiter message contains decline/close-out language,
    // a "sure thanks" reply is an acknowledgment of that close — NOT new interest.
    const recruiterMsgsArr = (function() {
      const list = document.getElementById(`smsMessagesList_${cid}`);
      if (!list) return [];
      return Array.from(list.querySelectorAll('li.smsMessageOut'))
        .map(li => (li.querySelector('.smsMessageBody')?.textContent || '').toLowerCase());
    })();
    const lastRecruiterMsg = recruiterMsgsArr.length ? recruiterMsgsArr[recruiterMsgsArr.length - 1] : '';
    const recruiterClosedOut = /\b(unfortunately|don'?t have|not a fit|not the right fit|best of luck|good luck with your search|if something .* opens up|if (anything|something) (else )?opens|we'?ll reach out|i'?ll reach out|keep you in mind)\b/i.test(lastRecruiterMsg);

    // ─── Interest+thanks pattern ───
    // "Sure thanks", "Yes thanks", "Yeah thank you" → interest reply to outreach.
    // Only treat as interest if recruiter hasn't closed out — otherwise it's an ack.
    const interestStart = /^(yes|yea|yeah|yep|yup|sure|absolutely|definitely|interested|sounds good|sounds great|ok)\b/i.test(normalizedMsg);
    const containsThanks = /\b(thanks|thank you|thx|ty)\b/i.test(normalizedMsg);
    if (interestStart && containsThanks && !recruiterClosedOut) {
      return { reply: null, template: 'handoff', confidence: 'high', note: 'interest+thanks → handoff (local)', addFolders: true };
    }

    // Check exact interested
    for (const exact of c.interestedExact) {
      if (normalizedMsg === exact) {
        return { reply: null, template: 'handoff', confidence: 'high', note: 'exact interested (local)', addFolders: true };
      }
    }

    // Check exact not-interested
    for (const exact of c.notInterestedExact) {
      if (normalizedMsg === exact) {
        return { reply: null, template: 'ignore', confidence: 'high', note: 'exact not interested (local)', addFolders: false };
      }
    }

    // Check acknowledgment
    for (const ack of c.acknowledgmentPatterns) {
      if (normalizedMsg.includes(normalize(ack))) {
        return { reply: null, template: 'ignore', confidence: 'high', note: 'acknowledgment (local)', addFolders: false };
      }
    }

    // Partial not-interested (check BEFORE interested to prevent "not interested" matching "interested")
    if (c.notInterestedPartial.some(p => normalizedMsg.includes(normalize(p)))) {
      return { reply: null, template: 'ignore', confidence: 'medium', note: 'partial not interested (local)', addFolders: false };
    }
    if (c.notInterestedRegex.test(lastMsgLower)) {
      return { reply: null, template: 'ignore', confidence: 'high', note: 'regex not interested (local)', addFolders: false };
    }

    // Partial interested
    if (c.interestedPartial.some(p => normalizedMsg.includes(normalize(p)))) {
      return { reply: null, template: 'handoff', confidence: 'medium', note: 'partial interested (local)', addFolders: true };
    }

    // Everything else → AI
    return null;
  }

  // ─── MOO Local Pre-Filter ─────────────────────────────────────────────────
  function localPreFilterMOO(cid, lastMsgLower, allRecruiterText) {
    const funnel = activeClient.detectFunnel(allRecruiterText);

    // Post-scheduling-link acknowledgments
    if (funnel.schedulingLinkSent) {
      if (/^(thanks|thank you|thx|ty|ok|okay|got it|cool|awesome|great|perfect|will do|sounds good)[\s!.]*$/i.test(lastMsgLower)) {
        return { reply: null, template: 'ignore', confidence: 'high', note: 'post-link ack (local)', addFolders: false };
      }
    }

    // Clear not-interested patterns
    if (/\b(i don'?t do sales|no sales|not into sales)\b/i.test(lastMsgLower)) {
      return { reply: null, template: 'ignore', confidence: 'high', note: 'sales rejection (local)', addFolders: false };
    }

    // ─── Info blurb NOT sent yet ────────────────────────────────────────────
    if (!funnel.infoBlurbSent) {
      // Clear interest (standalone) → send info blurb
      if (/^(yes|yea|yeah|yep|yup|sure|interested|i'?m interested|sounds good|sounds great|send it|send it over|go ahead|please do|absolutely|definitely|of course|let'?s do it|i'?m in|i'?m down|why not|go for it|i'?d love to)[\s!.]*$/i.test(lastMsgLower)) {
        return { reply: null, template: 'info_blurb', confidence: 'high', note: 'interested → info blurb (local)', addFolders: false };
      }
      // Interest word at START of longer message (e.g. "Yes I am at work now can you call after 12pm")
      // Skip if message contains '?' — questions like "Yes but what's the pay?" need AI
      if (!lastMsgLower.includes('?') && /^(yes|yea|yeah|yep|yup|sure|absolutely|definitely|interested|i'?m interested|sounds good|sounds great)\b/i.test(lastMsgLower)) {
        return { reply: null, template: 'info_blurb', confidence: 'high', note: 'interest+more → info blurb (local)', addFolders: false };
      }
      // Minimal responses → still send info blurb
      if (/^(y|k|ok|okay|kk|maybe|sure ig|hello|hi|hey)[\s!.]*$/i.test(lastMsgLower)) {
        return { reply: null, template: 'info_blurb', confidence: 'high', note: 'minimal interest → info blurb (local)', addFolders: false };
      }
    }

    // ─── Info blurb sent, scheduling link NOT sent ──────────────────────────
    if (funnel.infoBlurbSent && !funnel.schedulingLinkSent) {
      // Clear positive response to info blurb → scheduling link
      if (/^(yes|yea|yeah|yep|yup|sure|that works|sounds good|sounds great|i'?m interested|let'?s do it|i'?m in|i'?m down|absolutely|definitely|sign me up|let'?s go|perfect|for sure|count me in|ready)[\s!.]*$/i.test(lastMsgLower)) {
        return { reply: null, template: 'scheduling_link', confidence: 'high', note: 'confirmed → scheduling link (local)', addFolders: true };
      }
      // Acknowledgment without clear interest (after info blurb)
      if (/^(ok|okay|got it|cool|thanks|thank you|thx|ty|i see|alright)[\s!.]*$/i.test(lastMsgLower)) {
        // Ambiguous — could mean "ok I'll think about it" or "ok let's do it" → let AI handle
        return null;
      }
    }

    // Everything else → AI
    return null;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  AI CALL
  // ═══════════════════════════════════════════════════════════════════════════

  async function getAISuggestion(threadText) {
    if (!activeClient) throw new Error('No active client');
    console.log('[MultiClient] getAISuggestion called');

    const controller = new AbortController();
    const timeout = setTimeout(() => { console.log('[MultiClient] API TIMEOUT — aborting'); controller.abort(); }, 45000);
    let response;

    try {
      console.log('[MultiClient] fetch starting to api.anthropic.com...');
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
          max_tokens: 600,
          system: [{ type: 'text', text: activeClient.systemPrompt, cache_control: { type: 'ephemeral' } }],
          messages: [{
            role: 'user',
            content: `Here is the conversation thread:\n\n${threadText}\n\nWhat should I reply?\n\nRespond with ONLY a single JSON object. Do not add any text, commentary, or markdown before or after the JSON.`
          }]
        })
      });
    } finally {
      clearTimeout(timeout);
    }

    console.log('[MultiClient] fetch completed, status:', response.status);
    if (!response.ok) {
      const err = await response.text();
      throw new Error(`API error ${response.status}: ${err}`);
    }

    const data = await response.json();
    if (data.usage) console.log('[AI Cache]', data.usage.cache_read_input_tokens ? '✅ CACHE HIT' : '📝 CACHE WRITE', data.usage);

    const text = data.content?.[0]?.text?.trim();
    console.log('[MultiClient] AI raw text:', text);
    if (!text) throw new Error('Empty response from API');

    // Strip markdown fences, then extract the first balanced JSON object
    // (ignores trailing commentary and respects strings/escapes inside the JSON)
    const stripped = text.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();
    const jsonStr = extractFirstJsonObject(stripped);
    if (!jsonStr) {
      console.error('[MultiClient] No JSON object found. Raw response:', text);
      throw new Error('No JSON object found in AI response');
    }
    let parsed;
    try {
      parsed = JSON.parse(jsonStr);
    } catch (e) {
      console.error('[MultiClient] JSON.parse failed. Extracted:', jsonStr, '\nRaw response:', text);
      throw e;
    }
    console.log('[MultiClient] AI parsed:', JSON.stringify(parsed));
    return parsed;
  }

  // Walks the string char-by-char, tracking string literals and escape sequences,
  // and returns the first balanced {...} substring. Returns null if none found.
  function extractFirstJsonObject(s) {
    let start = -1, depth = 0, inStr = false, esc = false;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (inStr) {
        if (esc) { esc = false; continue; }
        if (ch === '\\') { esc = true; continue; }
        if (ch === '"') { inStr = false; }
        continue;
      }
      if (ch === '"') { inStr = true; continue; }
      if (ch === '{') {
        if (depth === 0) start = i;
        depth++;
      } else if (ch === '}') {
        depth--;
        if (depth === 0 && start !== -1) return s.slice(start, i + 1);
      }
    }
    return null;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  FOLDER ADD
  // ═══════════════════════════════════════════════════════════════════════════

  async function addToFolder(cid, folderId) {
    const contact = sms.client.storage.contacts.getById(parseInt(cid));
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
    if (!activeClient) return;
    for (let i = 0; i < activeClient.folderIds.length; i++) {
      if (i > 0) await delay(500);
      await addToFolder(cid, activeClient.folderIds[i]);
      await delay(200);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  AUTO-FILL LOGIC
  // ═══════════════════════════════════════════════════════════════════════════

  async function autoFill(cid) {
    if (!activeClient) return;
    if (manualMode) return;
    if (isUnsubscribed(cid)) {
      setBadge('⊘ unsubscribed — skipping', '#888');
      if (autopilot && !autopilotPaused) {
        _skippedUnsub.add(cid);
        const unreads = getUnreads();
        if (unreads.length && unreads.every(li => _skippedUnsub.has(li.getAttribute('smscontactid')))) {
          _skippedUnsub.clear();
          pauseAutopilot('only unsubscribed contacts remain');
        } else {
          await delay(300);
          autopilotNext();
        }
      }
      return;
    }

    if (folderOpInProgress) return;
    const now = Date.now();
    if (fillInProgress && (now - fillInProgress) < FILL_LOCK_MS && fillInProgressCid === cid) {
      console.log('[MultiClient] Fill locked (same cid) — skipping (age:', now - fillInProgress, 'ms)');
      return;
    }
    fillInProgress = now;
    fillInProgressCid = cid;
    lastSuggestion = null;

    setBadge('⟳ analyzing...', '#888');
    console.log('[MultiClient] autoFill START cid:', cid);

    try { // ← ensures fillInProgress always resets

    // Wait for thread to load
    console.log('[MultiClient] waiting for thread...');
    try {
      await waitFor(() => hasMessages(cid), 15000);
    } catch (e) {
      setBadge('⚠ thread not loaded — navigate away and back', '#fa0');
      fillInProgress = 0;
      if (autopilot) pauseAutopilot('thread not loaded');
      return;
    }
    console.log('[MultiClient] thread loaded');

    if (getActiveCid() !== cid) { console.log('[MultiClient] cid changed, aborting'); fillInProgress = 0; return; }

    // If last message is ours, nothing to reply to
    if (lastMessageIsOutbound(cid)) {
      markAsRead(cid);
      setBadge('⊘ waiting for candidate reply', '#888');
      fillInProgress = 0;
      if (autopilot && !autopilotPaused) {
        if (_lastAutopilotCid === cid) {
          _lastAutopilotCid = null;
          pauseAutopilot('stale unread — check and resume');
        } else {
          _lastAutopilotCid = cid;
          await delay(300);
          autopilotNext();
        }
      }
      return;
    }

    // If last candidate message is blank/empty, skip — likely an image or MMS
    const lastCandMsg = getLastCandidateMessage(cid);
    if (!lastCandMsg || !lastCandMsg.trim()) {
      markAsRead(cid);
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

    // ASB-specific: check if pitch was sent and there's an inbound reply
    if (activeClient.funnelType === 'handoff') {
      const { hasPitch, hasReply, alreadyReplied } = analyzeThreadASB(cid);
      if (!hasPitch || !hasReply || alreadyReplied) {
        markAsRead(cid);
        setBadge('⊘ no action needed', '#888');
        fillInProgress = 0;
        if (autopilot && !autopilotPaused) {
          _lastAutopilotCid = null; _skippedUnsub.clear();
          delete aiCache[cid];
          await delay(300);
          autopilotNext();
        }
        return;
      }
    }

    // Try local pre-filter first
    const msgCount = getMessageCount(cid);
    const cached = aiCache[cid];
    let suggestion;

    if (cached && cached.msgCount === msgCount) {
      suggestion = cached.suggestion;
      setBadge('⟳ cached', '#888');
    } else {
      const localResult = localPreFilter(cid);
      if (localResult) {
        suggestion = localResult;
        console.log('[Local]', '⚡ SKIPPED API —', localResult.note);
      } else {
        const threadText = getThreadText(cid);
        console.log('[MultiClient] local pre-filter → null, calling AI...');
        console.log('[MultiClient] thread text length:', threadText.length);
        const slowTimer = setTimeout(() => {
          if (fillInProgress) setBadge('⟳ AI thinking... (taking a moment)', '#888');
        }, 18000);

        try {
          console.log('[MultiClient] API fetch starting...');
          suggestion = await getAISuggestion(threadText);
          console.log('[MultiClient] API response:', JSON.stringify(suggestion));
        } catch (err) {
          clearTimeout(slowTimer);
          console.error('[SMS AI] API error:', err);
          setBadge('⚠ AI error — navigate away and back', '#f44');
          fillInProgress = 0;
          if (autopilot) pauseAutopilot('AI error');
          return;
        }
        clearTimeout(slowTimer);
      }
      aiCache[cid] = { msgCount, suggestion };
    }

    if (getActiveCid() !== cid) { fillInProgress = 0; return; }

    const ta = getTextarea(cid);
    if (!ta) { fillInProgress = 0; return; }

    // ─── Process the suggestion ─────────────────────────────────────────────
    let template = suggestion.template;

    // Handle unsubscribe (extreme hostility) — auto-skip in autopilot
    if (template === 'unsubscribe') {
      ta.value = '';
      ta.focus();
      lastSuggestion = { addFolders: false, template: 'unsubscribe' };
      markAsRead(cid);
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
    }

    // Handle ignore / no reply
    if (template === 'ignore' || (!suggestion.reply && template !== 'handoff' && template !== 'info_blurb' && template !== 'scheduling_link')) {

      // If AI included a polite close reply, fill it so user can review/send
      if (suggestion.reply) {
        ta.value = suggestion.reply;
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        ta.focus();
        ta.setSelectionRange(ta.value.length, ta.value.length);
        lastSuggestion = { addFolders: false, template: 'ignore' };
        const conf = suggestion.confidence || 'low';
        const confColor = { high: '#4c4', medium: '#fa0', low: '#f84' };
        setBadge(`→ polite close (${conf}) — no folder\n${escHtml(suggestion.note || '')}`, confColor[conf] || '#fa0');
        if (autopilot && !autopilotPaused) {
          if (conf === 'high' || conf === 'medium') {
            await autopilotSend(cid, ta, suggestion);
          } else {
            pauseAutopilot(`${conf} confidence — review before sending`);
          }
        }
        fillInProgress = 0;
        return;
      }

      // No reply — check if opt-out or wrong number
      ta.value = '';
      ta.focus();
      lastSuggestion = { addFolders: false, template: 'ignore' };
      markAsRead(cid);

      // Get the candidate's actual last message for opt-out detection
      const lastMsg = getLastCandidateMessage(cid).toLowerCase();
      const wrongNumberPattern = /\b(wrong number|not my number|wrong person|who is this.*wrong|this is(n't| not) my number)\b/i;
      const isWrongNumber = !isUnsubscribed(cid) && wrongNumberPattern.test(lastMsg);
      const optOutPattern = /\b(stop\b(?! by)|unsubscribe|opt.?out|remove .*(from|off)|take .*(off|from)|don'?t (text|contact|message|call)|off (your|the|this) list|(from|off) .*(list|calling)|no more (texts?|messages?|calls?)|lose my number|leave me alone|cease and desist)\b/i;
      const isOptOut = !isUnsubscribed(cid) && (isWrongNumber || optOutPattern.test(lastMsg));

      if (isOptOut) {
        // Wrong number: auto-unsubscribe via system API + skip
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

      // True ignore — no reply needed
      setBadge(`⊘ ignore — ${escHtml(suggestion.note || 'no reply needed')}`, '#888');
      fillInProgress = 0;
      if (autopilot && !autopilotPaused) {
        _lastAutopilotCid = null; _skippedUnsub.clear();
        delete aiCache[cid];
        await delay(500);
        autopilotNext();
      }
      return;
    }

    // ─── Build the reply text based on template ─────────────────────────────
    let replyText = '';
    let shouldAddFolders = suggestion.addFolders === true;

    // Normalize unexpected template names the AI might return
    const TEMPLATE_ALIASES = {
      'not_interested': 'ignore', 'decline': 'ignore', 'stop': 'ignore',
      'acknowledgment': 'ignore', 'acknowledge': 'ignore',
      'interested': suggestion.reply ? 'custom' : 'ignore',
      'follow_up': suggestion.reply ? 'custom' : 'ignore',
    };
    const VALID_TEMPLATES = ['handoff', 'info_blurb', 'scheduling_link', 'custom', 'ignore'];
    if (!VALID_TEMPLATES.includes(template)) {
      const mapped = TEMPLATE_ALIASES[template];
      if (mapped) {
        console.log(`[MultiClient] Remapped template "${template}" → "${mapped}"`);
        template = mapped;
        suggestion.template = mapped;
      } else {
        console.warn(`[MultiClient] Unknown template "${template}" — treating as ${suggestion.reply ? 'custom' : 'ignore'}`);
        template = suggestion.reply ? 'custom' : 'ignore';
        suggestion.template = template;
      }
    }

    if (template === 'handoff') {
      // ASB: insert handoff text
      replyText = activeClient.templates.handoff;
      shouldAddFolders = true;
    } else if (template === 'info_blurb') {
      // MOO: insert info blurb, optionally prepend AI reply
      if (suggestion.reply) {
        // Strip blurb opening so it flows after the AI's lead-in (avoids "Here are the details:" + "Here is a quick overview:")
        const blurbText = activeClient.templates.infoBlurb.replace(/^Here is a quick overview:\s*this is a\s*/i, 'This is a ');
        replyText = suggestion.reply + '\n\n' + blurbText;
      } else {
        replyText = activeClient.templates.infoBlurb;
      }
      shouldAddFolders = false;
    } else if (template === 'scheduling_link') {
      // MOO: insert account-specific scheduling link
      // If AI answered a question, use the short link (AI reply handles the intro)
      // If no AI reply, use the full template with "Perfect -..." intro
      if (suggestion.reply) {
        const shortLink = activeClient.templates.schedulingLinkShort || activeClient.templates.schedulingLink;
        replyText = suggestion.reply + '\n\n' + shortLink;
      } else {
        replyText = activeClient.templates.schedulingLink;
      }
      shouldAddFolders = true;
    } else if (template === 'custom' && suggestion.reply) {
      // Custom AI reply
      replyText = suggestion.reply;
      shouldAddFolders = false;
    } else if (suggestion.reply) {
      // Fallback: use whatever reply the AI gave
      replyText = suggestion.reply;
    }

    if (!replyText) {
      // Safety: if we somehow have no reply text, treat as ignore
      ta.value = '';
      ta.focus();
      lastSuggestion = { addFolders: false, template: 'ignore' };
      markAsRead(cid);
      setBadge(`⊘ no reply text — ${escHtml(suggestion.note || '')}`, '#888');
      fillInProgress = 0;
      if (autopilot && !autopilotPaused) {
        _lastAutopilotCid = null; _skippedUnsub.clear();
        delete aiCache[cid];
        await delay(500);
        autopilotNext();
      }
      return;
    }

    // Fill textarea
    ta.value = replyText;
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);
    lastSuggestion = { addFolders: shouldAddFolders, template };

    const confColor = { high: '#4c4', medium: '#fa0', low: '#f84' };
    const conf = suggestion.confidence || 'low';
    const folderNote = shouldAddFolders ? ' + folder on ↵' : '';
    const tLabel = template;
    setBadge(`→ ${tLabel} (${conf})${folderNote}\n${escHtml(suggestion.note || '')}`, confColor[conf] || '#fa0');

    // Autopilot: auto-send high/medium, pause on low
    if (autopilot && !autopilotPaused) {
      if (conf === 'high' || conf === 'medium') {
        await autopilotSend(cid, ta, suggestion);
      } else {
        pauseAutopilot(`${conf} confidence — review before sending`);
      }
    }

    } catch (err) {
      console.error('[MultiClient] autoFill error:', err);
      setBadge('⚠ error — click contact again', '#f44');
      if (autopilot) pauseAutopilot('unexpected error');
    } finally {
      fillInProgress = 0;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  AUTOPILOT SEND & ADVANCE
  // ═══════════════════════════════════════════════════════════════════════════

  async function autopilotSend(cid, ta, suggestion) {
    _lastAutopilotCid = null; _skippedUnsub.clear();
    const shouldAddFolders = lastSuggestion?.addFolders === true;
    delete aiCache[cid];

    // Send the message
    try {
      sms.client.main.send(parseInt(cid, 10));
    } catch (err) {
      console.error('[SMS] Send error:', err);
      pauseAutopilot('send failed — try manually');
      return;
    }
    setBadge('⟳ autopilot sending...', '#4af');

    try {
      await waitFor(() => !ta.value.trim(), 35000);
    } catch (_) {
      pauseAutopilot('send not confirmed — check if sent');
      return;
    }

    await delay(400);

    // Handle folders
    if (shouldAddFolders) {
      setBadge('⟳ adding folders...', '#4af');
      folderOpInProgress = true;
      try {
        await addToFolders(cid);
        setBadge('✓ folders added', '#4c4');
        await delay(800);
      } catch (err) {
        console.error('[SMS] Folder error:', err);
        folderOpInProgress = false;
        pauseAutopilot('FOLDER ADD FAILED — add manually');
        return;
      }
      folderOpInProgress = false;
    }

    if (autopilot && !autopilotPaused) {
      await delay(500);
      autopilotNext();
    }
  }

  function autopilotNext() {
    if (!autopilot || autopilotPaused) return;
    const unreads = getUnreads();
    if (!unreads.length) {
      setBadge('✓ caught up — waiting for new unreads...', '#4c4');
      if (!_autopilotPollTimer) {
        _autopilotPollTimer = setInterval(() => {
          if (!autopilot || autopilotPaused) {
            clearInterval(_autopilotPollTimer); _autopilotPollTimer = null; return;
          }
          const newUnreads = getUnreads();
          if (newUnreads.length) {
            if (fillInProgress && (Date.now() - fillInProgress) < FILL_LOCK_MS) return;
            clearInterval(_autopilotPollTimer); _autopilotPollTimer = null;
            setBadge(`▶ ${newUnreads.length} new unread — resuming...`, '#4af');
            lastSuggestion = null;
            navigate('up');
          }
        }, 3000);
      }
      return;
    }
    lastSuggestion = null;
    navigate('up');
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  NAVIGATION
  // ═══════════════════════════════════════════════════════════════════════════

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

  // ═══════════════════════════════════════════════════════════════════════════
  //  BADGE
  // ═══════════════════════════════════════════════════════════════════════════

  const badge = document.createElement('div');
  badge.id = 'smsAIBadge';
  Object.assign(badge.style, {
    fontFamily: 'monospace', fontSize: '11px', padding: '5px 9px',
    background: 'rgba(0,0,0,0.80)', color: '#fff', borderRadius: '4px',
    zIndex: '9999', pointerEvents: 'none', lineHeight: '1.6',
    whiteSpace: 'pre-wrap', maxWidth: '480px'
  });

  const badgeContainer = document.querySelector('.smsViewSettings') || document.querySelector('#smsViewHeader');
  if (badgeContainer) {
    badgeContainer.style.position = 'relative';
    Object.assign(badge.style, { position: 'absolute', top: '32px', right: '0' });
    badgeContainer.appendChild(badge);
  } else {
    Object.assign(badge.style, { position: 'fixed', top: '10px', right: '10px' });
    document.body.appendChild(badge);
  }

  function getModeTag() {
    const acct = activeClient ? ` ${activeClient.name}` : '';
    if (manualMode) return `${acct} | MANUAL`;
    if (autopilot) return autopilotPaused ? `${acct} | ⏸ AP` : `${acct} | ▶ AP`;
    return `${acct} | AI`;
  }

  function setBadge(msg, color) {
    const count = getUnreads().length;
    badge.innerHTML = `<span style="color:#fff">${count} unread${getModeTag()}</span>\n<span style="color:${color || '#fff'}">${msg}</span>`;
  }

  setBadge('Select account to begin...', '#f90');

  // ═══════════════════════════════════════════════════════════════════════════
  //  MODE BUTTONS
  // ═══════════════════════════════════════════════════════════════════════════

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
    { id: 'autopilot', label: 'Autopilot', key: 'Ctrl+Shift+P' }
  ];
  const modeBtnEls = {};

  MODE_BTNS.forEach(btn => {
    const el = document.createElement('button');
    el.textContent = btn.label;
    el.title = btn.key ? `Hotkey: ${btn.key}` : '';
    Object.assign(el.style, {
      padding: '5px 12px', border: 'none', cursor: 'pointer',
      fontSize: '11px', fontFamily: 'sans-serif', fontWeight: '600',
      color: '#fff', background: '#555', transition: 'background 0.15s',
      outline: 'none'
    });
    el.addEventListener('mouseenter', () => { if (!el.classList.contains('active')) el.style.background = '#777'; });
    el.addEventListener('mouseleave', () => { if (!el.classList.contains('active')) el.style.background = '#555'; });
    el.addEventListener('click', () => {
      if (btn.id === 'autopilot' && autopilot && !autopilotPaused) switchMode('ai');
      else switchMode(btn.id);
    });
    modeBar.appendChild(el);
    modeBtnEls[btn.id] = el;
  });

  function highlightModeBtn() {
    const active = manualMode ? 'manual' : (autopilot ? 'autopilot' : 'ai');
    const colors = { manual: '#d68000', ai: '#2a8af6', autopilot: '#22aa44' };
    Object.entries(modeBtnEls).forEach(([id, el]) => {
      const isActive = id === active;
      el.style.background = isActive ? colors[id] : '#555';
      el.style.fontWeight = isActive ? '700' : '600';
      el.classList.toggle('active', isActive);
    });
    if (autopilot && autopilotPaused) {
      modeBtnEls.autopilot.style.background = '#cc8800';
      modeBtnEls.autopilot.textContent = 'Paused';
    } else {
      modeBtnEls.autopilot.textContent = 'Autopilot';
    }
  }

  function switchMode(mode) {
    if (!activeClient && mode !== 'manual') {
      setBadge('⚠ Select an account for AI/Autopilot', '#f44');
      return;
    }
    if (mode === 'manual') {
      if (manualMode) return;
      manualMode = true;
      if (autopilot) {
        autopilot = false; autopilotPaused = false;
        if (_autopilotPollTimer) { clearInterval(_autopilotPollTimer); _autopilotPollTimer = null; }
        if (_pauseReminderTimer) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; }
      }
      lastSuggestion = null;
      setBadge('MANUAL MODE — nav + Enter to send', '#f90');
    } else if (mode === 'ai') {
      const wasManual = manualMode;
      manualMode = false;
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
    } else if (mode === 'autopilot') {
      if (manualMode) manualMode = false;
      if (autopilot && !autopilotPaused) return;
      if (autopilot && autopilotPaused) {
        // Resume
        autopilotPaused = false;
        if (_pauseReminderTimer) { clearInterval(_pauseReminderTimer); _pauseReminderTimer = null; }
        setBadge('▶ AUTOPILOT RESUMED', '#4af');
        const currentCid = getActiveCid();
        const currentTa = currentCid ? getTextarea(currentCid) : null;
        if (!currentTa || !currentTa.value.trim()) setTimeout(() => autopilotNext(), 300);
      } else {
        // Start fresh
        autopilot = true; autopilotPaused = false;
        _lastAutopilotCid = null; _skippedUnsub.clear();
        const unreads = getUnreads();
        if (!unreads.length) {
          setBadge('▶ AUTOPILOT ON — waiting for unreads...', '#4af');
          autopilotNext();
        } else {
          const currentCid = getActiveCid();
          const currentTa = currentCid ? getTextarea(currentCid) : null;
          if (currentTa && currentTa.value.trim()) {
            setBadge('▶ AUTOPILOT ON — press Enter to send', '#4af');
          } else {
            setBadge('▶ AUTOPILOT ON — navigating to first unread...', '#4af');
            lastSuggestion = null;
            navigate('up');
          }
        }
      }
    }
    highlightModeBtn();
    updateMiniMascot();
  }

  highlightModeBtn();

  // ─── Unread count updater ─────────────────────────────────────────────────
  let _lastUnreadCount = -1;
  setInterval(() => {
    const count = getUnreads().length;
    if (count === _lastUnreadCount) return;
    _lastUnreadCount = count;
    const lines = badge.innerHTML.split('\n');
    lines[0] = `<span style="color:#fff">${count} unread${getModeTag()}</span>`;
    badge.innerHTML = lines.join('\n');
  }, 2000);

  // ═══════════════════════════════════════════════════════════════════════════
  //  KEY HANDLER
  // ═══════════════════════════════════════════════════════════════════════════

  document.addEventListener('keydown', e => {
    const key     = e.key;
    const cid     = getActiveCid();
    const ta      = cid ? getTextarea(cid) : null;
    const focused = ta && document.activeElement === ta;
    const hasContent = focused && ta.value.trim().length > 0;

    // ── Enter in reply box ──────────────────────────────────────────────────
    if (key === 'Enter' && focused && hasContent && activeClient) {
      e.stopImmediatePropagation(); // prevent standalone scripts from also handling

      // Shift+Enter → send + add folders + advance (manual override for folder add)
      if (e.shiftKey) {
        e.preventDefault();
        sms.client.main.send(parseInt(cid, 10));
        lastSuggestion = null;
        delete aiCache[cid];
        folderOpInProgress = true;
        (async () => {
          try { await waitFor(() => !ta.value.trim(), 35000); } catch (_) {}
          await delay(400);
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
          folderOpInProgress = false;
          if (autopilot && autopilotPaused) {
            if (foldersOk) setBadge('✓ sent + folders — Ctrl+Shift+P to resume', '#4c4');
            else pauseAutopilot('FOLDER ADD FAILED — add manually');
          } else if (!manualMode) autoAdvance();
        })();
        return;
      }

      // Plain Enter → send, auto-add folders if AI said so, then advance
      const shouldAddFolders = lastSuggestion?.addFolders === true;
      lastSuggestion = null;
      delete aiCache[cid];

      const checkSent = setInterval(() => {
        if (!ta.value.trim()) {
          clearInterval(checkSent);
          if (shouldAddFolders) {
            (async () => {
              folderOpInProgress = true;
              await delay(400);
              setBadge('⟳ adding folders...', '#4af');
              try {
                await addToFolders(cid);
                setBadge('✓ folders added', '#4c4');
                await delay(1200);
              } catch (err) {
                console.error('[SMS] Folder error:', err);
                folderOpInProgress = false;
                if (autopilot) { pauseAutopilot('FOLDER ADD FAILED'); return; }
                setBadge('⚠ folder add failed — use Shift+` to retry', '#f44');
                await delay(2500);
              }
              folderOpInProgress = false;
              if (autopilot && !autopilotPaused) { setTimeout(() => autopilotNext(), 500); }
              else if (autopilot && autopilotPaused) { setBadge('✓ sent — Ctrl+Shift+P to resume', '#4c4'); }
              else if (!manualMode) autoAdvance();
            })();
          } else {
            if (autopilot && !autopilotPaused) { setTimeout(() => autopilotNext(), 500); }
            else if (autopilot && autopilotPaused) {
              markAsRead(cid);
              setBadge('✓ sent — Ctrl+Shift+P to resume', '#4c4');
            }
            else if (!manualMode) autoAdvance();
          }
        }
      }, 100);

      setTimeout(() => {
        clearInterval(checkSent);
        if (ta.value.trim()) {
          setBadge('⚠ send not confirmed — check message', '#fa0');
          if (autopilot) pauseAutopilot('send not confirmed');
        }
      }, 35000);

      return; // let native send handler fire
    }

    // ── Autopilot toggle (Ctrl+Shift+P) ─────────────────────────────────────
    if ((key === 'p' || key === 'P') && e.ctrlKey && e.shiftKey) {
      e.preventDefault();
      if (autopilot && !autopilotPaused) switchMode('ai');
      else switchMode('autopilot');
      return;
    }

    // ── Manual mode toggle (Ctrl+Shift+M) ───────────────────────────────────
    if ((key === 'm' || key === 'M') && e.ctrlKey && e.shiftKey) {
      e.preventDefault();
      switchMode(manualMode ? 'ai' : 'manual');
      return;
    }

    // ── Shift+` → ACE folder add (when client active) ────────────────────
    if (e.code === 'Backquote' && e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (!cid || !activeClient) return;
      if (folderOpInProgress) { setBadge('⟳ folder add already in progress...', '#fa0'); return; }
      folderOpInProgress = true;
      setBadge('⟳ adding folders...', '#4af');
      (async () => {
        try {
          await addToFolders(cid);
          setBadge('✓ folders added', '#4c4');
        } catch (err) {
          console.error('[SMS] Folder error:', err);
          setBadge('⚠ folder add failed — try Shift+` again', '#f44');
        }
        folderOpInProgress = false;
      })();
      return;
    }

    // ── Plain ` → open folder dialog OR confirm OK (works in any mode) ──
    if (e.code === 'Backquote' && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      e.preventDefault();
      e.stopImmediatePropagation();
      // If folder OK button is visible, click it
      const okBtn = document.querySelector('#wsjAddToFolderButtonOK');
      if (okBtn && okBtn.offsetParent !== null) { okBtn.click(); return; }
      // Otherwise open the folder dialog for the active contact
      if (!cid) return;
      const folderIcon = document.querySelector(`#smsContactContainer_${cid} .wsjAddToFolderLink img`);
      if (folderIcon) folderIcon.click();
      return;
    }

    // ── Esc → cancel folder dialog ──────────────────────────────────────
    if (key === 'Escape' && !e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey) {
      const cancelBtn = document.querySelector('#wsjAddToFolderButtonCancel');
      if (cancelBtn && cancelBtn.offsetParent !== null) {
        e.preventDefault();
        e.stopImmediatePropagation();
        cancelBtn.click();
        return;
      }
    }

    // ── Navigation keys (always active — works with or without client) ──
    const navKeys = [UP_KEY, DOWN_KEY, BACK_KEY];
    if (!navKeys.includes(key)) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    e.preventDefault();
    e.stopImmediatePropagation();
    if (key === BACK_KEY) { navigateBack(); return; }
    navigate(key === UP_KEY ? 'up' : 'down');
  });

  // ═══════════════════════════════════════════════════════════════════════════
  //  AUTO-FILL ON SIDEBAR CLICK
  // ═══════════════════════════════════════════════════════════════════════════

  document.addEventListener('click', e => {
    const contact = e.target.closest('li.smsContactContainer');
    if (!contact) return;
    const cid = contact.getAttribute('smscontactid');
    if (!cid) return;
    if (manualMode || !activeClient) return;
    if (autopilot) return;
    setTimeout(() => autoFill(cid), 400);
  });

  // ═══════════════════════════════════════════════════════════════════════════
  //  INITIALIZATION — SHOW ACCOUNT SELECTOR
  // ═══════════════════════════════════════════════════════════════════════════

  // Wait a moment for the page to settle, then show selector
  setTimeout(() => {
    createAccountIndicator();
    createMiniMascot();
    showAccountSelector(client => {
      activeClient = client;
      updateAccountIndicator();
      updateMiniMascot();
      if (client) {
        setBadge(`${client.name} loaded — MANUAL MODE`, '#f90');
        console.log(`[SMS Multi-Client] Active: ${client.fullName}`);
        // If there's an active contact, it's ready to go
        const initCid = getActiveCid();
        if (initCid && !manualMode) setTimeout(() => autoFill(initCid), 1000);
      } else {
        manualMode = true;
        autopilot = false; autopilotPaused = false;
        setBadge('MANUAL ONLY — nav keys active', '#888');
        highlightModeBtn();
        console.log('[SMS Multi-Client] Manual only mode — no client selected');
      }
    });
  }, 800);

})();
