/**
 * Gmail Triage Auto-Labeler
 *
 * Automatically labels incoming emails using the existing label system:
 *   ! prefix = action labels:  !Action, !Action/Urgent, !FYI, !Read-Review, !Waiting-For
 *   ~ prefix = skip labels:    ~Sales-Pitch, ~Notifications, ~Newsletters, ~Calendar, ~Receipts,
 *                               ~Marketing, ~LinkedIn, ~ErrorMonitor, ~CRM
 *   _ prefix = AI labels:      _ai, _ai/unsure
 *
 * Runs on a time-driven trigger (every 5 min) across all 5 accounts:
 *   justinrsteele@gmail.com, justin@truesteele.com, justin@kindora.co,
 *   justin@outdoorithm.com, justin@outdoorithmcollective.org
 */

// ── Label names (matching existing labels in all accounts) ───────────
var LABEL_ACTION       = '!Action';
var LABEL_ACTION_URGENT = '!Action/Urgent';
var LABEL_FYI          = '!FYI';
var LABEL_READ_REVIEW  = '!Read-Review';
var LABEL_SALES_PITCH  = '~Sales-Pitch';
var LABEL_NOTIFICATIONS = '~Notifications';
var LABEL_NEWSLETTERS  = '~Newsletters';
var LABEL_CALENDAR     = '~Calendar';
var LABEL_RECEIPTS     = '~Receipts';
var LABEL_MARKETING    = '~Marketing';
var LABEL_LINKEDIN     = '~LinkedIn';
var LABEL_ERROR_MONITOR = '~ErrorMonitor';
var LABEL_AI           = '_ai';

// All triage labels we might apply (used for search exclusion + cleanup)
var ALL_TRIAGE_LABELS = [
  LABEL_ACTION, LABEL_ACTION_URGENT, LABEL_FYI, LABEL_READ_REVIEW,
  LABEL_SALES_PITCH, LABEL_NOTIFICATIONS, LABEL_NEWSLETTERS,
  LABEL_CALENDAR, LABEL_RECEIPTS, LABEL_MARKETING, LABEL_LINKEDIN,
  LABEL_ERROR_MONITOR, LABEL_AI,
];

// ── Classification rules ─────────────────────────────────────────────
// Each rule maps to a specific existing label. Order matters — first match wins.
var RULES = [

  // ── ~ErrorMonitor (check BEFORE ~Notifications so error emails from same sender get tagged correctly) ──
  { from: /notifications@vercel\.com/i,     subject: /fail|error/i,          label: LABEL_ERROR_MONITOR, reason: 'Vercel error notification', markRead: false },
  { from: /noreply@outdoorithm\.com/i,      subject: /\[Error Report\]|\[INCIDENT\]|\[UNHEALTHY\]/i, label: LABEL_ERROR_MONITOR, reason: 'Outdoorithm error monitor', markRead: false },
  { from: /@kindora\.co$/i,                 subject: /\[Error Report\]|\[Daily Digest\].*(?:error|issue)/i, label: LABEL_ERROR_MONITOR, reason: 'Kindora error monitor', markRead: false },
  { from: /alert@kindora\.co/i,             subject: /stuck-task report/i,   label: LABEL_ERROR_MONITOR, reason: 'Kindora stuck-task alert', markRead: false },

  // ── ~LinkedIn ──
  { from: /@linkedin\.com$/i,               subject: null,                   label: LABEL_LINKEDIN, reason: 'LinkedIn notification', markRead: true },

  // ── ~Receipts ──
  { from: /receipts@mercury\.com/i,          subject: null,                   label: LABEL_RECEIPTS, reason: 'Mercury receipt forwarding', markRead: false },
  { from: /billing@apify\.com/i,             subject: null,                   label: LABEL_RECEIPTS, reason: 'Apify billing', markRead: false },
  { from: /hello@apify\.com/i,              subject: /usage|invoice|billing/i, label: LABEL_RECEIPTS, reason: 'Apify usage notice', markRead: false },
  { from: /noreply@order\.eventbrite\.com/i, subject: null,                   label: LABEL_RECEIPTS, reason: 'Eventbrite order', markRead: false },
  { from: /help@paddle\.com/i,              subject: /receipt/i,             label: LABEL_RECEIPTS, reason: 'Paddle receipt', markRead: false },
  { from: /invoice.*@vercel\.com/i,          subject: null,                   label: LABEL_RECEIPTS, reason: 'Vercel invoice', markRead: false },
  { from: /no-reply@toasttab\.com/i,        subject: /receipt|order/i,       label: LABEL_RECEIPTS, reason: 'Restaurant receipt', markRead: false },

  // ── ~Notifications (system/automated) ──
  { from: /^info@kindora\.co$/i,            subject: /New User Signup/i,     label: LABEL_NOTIFICATIONS, reason: 'Kindora system notification', markRead: true },
  { from: /notifications@vercel\.com/i,     subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Vercel deploy notification', markRead: true },
  { from: /noreply@tickets\./i,             subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Ticket confirmation', markRead: false },
  { from: /no-?reply@.*amazonses\.com/i,    subject: /New User Signup|Welcome to Kindora|organization profile|Intel Brief/i, label: LABEL_NOTIFICATIONS, reason: 'System notification via SES', markRead: true },
  { from: /@kindora\.co$/i,                 subject: /Your Intel Brief.*is ready/i, label: LABEL_NOTIFICATIONS, reason: 'Kindora intel brief', markRead: true },
  { from: /@kindora\.co$/i,                 subject: /Welcome to Kindora/i,        label: LABEL_NOTIFICATIONS, reason: 'Kindora welcome email', markRead: true },
  { from: /@kindora\.co$/i,                 subject: /organization profile is ready/i, label: LABEL_NOTIFICATIONS, reason: 'Kindora profile notification', markRead: true },
  { from: /billing@.*openai\.com/i,         subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'OpenAI billing notification', markRead: false },
  { from: /notification@slack\.com/i,       subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Slack notification', markRead: true },
  { from: /no-reply.*@slack\.com/i,         subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Slack notification', markRead: true },
  { from: /chat-noreply@google\.com/i,      subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Google Chat notification', markRead: true },
  { from: /workspace-noreply@google\.com/i, subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Google Workspace notification', markRead: false },
  { from: /families-noreply@google\.com/i,  subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Google family notification', markRead: false },
  { from: /noreply@.*supabase\./i,          subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Supabase notification', markRead: false },
  { from: /sc-noreply@google\.com/i,        subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Google Search Console', markRead: false },
  { from: /noreply@collective\.com/i,       subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Collective (accounting) notification', markRead: false },
  { from: /no-reply@email\.claude\.com/i,   subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Claude notification', markRead: false },
  { from: /noreply@mail\.cloud\.scansnap/i, subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'ScanSnap notification', markRead: true },
  { from: /no-reply@amazonaws\.com/i,       subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'AWS notification', markRead: false },
  { from: /no-reply-aws@amazon\.com/i,      subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'AWS notification', markRead: false },
  { from: /health@aws\.com/i,              subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'AWS health notification', markRead: false },
  { from: /no-reply@otter\.ai/i,           subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Otter.ai notification', markRead: false },
  { from: /notifications@calendly\.com/i,  subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Calendly notification', markRead: false },
  { from: /hello@gofarmhand\.com/i,        subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Farmhand notification', markRead: false },
  { from: /support@zerobounce\.net/i,      subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'ZeroBounce notification', markRead: false },
  { from: /hello@sanity\.io/i,            subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Sanity.io notification', markRead: true },
  { from: /no-reply@dropbox\.com/i,       subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Dropbox sign-in/security alert', markRead: true },
  { from: /no-reply@zoom\.us/i,           subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Zoom sign-in/security code', markRead: true },
  { from: /notifications@mailerlite\.com/i, subject: null,                 label: LABEL_NOTIFICATIONS, reason: 'MailerLite verification code', markRead: true },
  // ── !Action/Urgent: Inbound sales leads (MUST be before generic notification rules) ──
  { from: /noreply@blackbaud\.com/i,       subject: /Marketplace inquiry/i,  label: LABEL_ACTION_URGENT, reason: 'Blackbaud Marketplace inbound lead', markRead: false },
  { from: /noreply@blackbaud\.com/i,       subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Blackbaud notification', markRead: false },
  { from: /drive-shares-dm-noreply@google\.com/i, subject: null,            label: LABEL_NOTIFICATIONS, reason: 'Google Drive share', markRead: false },
  { from: /comments-noreply@docs\.google\.com/i,  subject: null,            label: LABEL_NOTIFICATIONS, reason: 'Google Docs comment', markRead: false },
  { from: /(?:notifications|noreply)@github\.com/i, subject: null,           label: LABEL_NOTIFICATIONS, reason: 'GitHub notification', markRead: false },
  { from: /notifications@taxdome\.com/i,   subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'TaxDome notification', markRead: false },
  { from: /azure-noreply@microsoft\.com/i, subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Azure notification', markRead: false },
  { from: /no-reply@anveo\.com/i,          subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Anveo VoIP notification', markRead: false },
  { from: /no\.reply\.alerts@chase\.com/i, subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Chase banking alert', markRead: false },
  { from: /account-noreply@united\.com/i,  subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'United Airlines notification', markRead: false },
  { from: /noreply@mail\.smapply\.net/i,   subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'SurveyMonkey Apply notification', markRead: false },
  { from: /community@theonevalley\.com/i,  subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'OneValley notification', markRead: false },
  { from: /venmo@venmo\.com/i,            subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Venmo notification', markRead: false },
  { from: /alert@phyn\.com/i,            subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Phyn smart water alert', markRead: false },
  { from: /no-reply@imagequix\.com/i,    subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'School photo notification', markRead: true },
  { from: /noreply@amazon\.com/i,        subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Amazon notification', markRead: false },
  { from: /help@ridwell\.com/i,          subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'Ridwell service notification', markRead: false },
  { from: /mailer-daemon@google(mail)?\.com/i, subject: null,             label: LABEL_NOTIFICATIONS, reason: 'Bounce/delivery notification', markRead: true },
  { from: /noreply@api\.data\.gov/i,     subject: null,                   label: LABEL_NOTIFICATIONS, reason: 'API key delivery', markRead: true },

  // ── ~Calendar ──
  { from: /noreply@luma-mail\.com/i,       subject: null,                   label: LABEL_CALENDAR, reason: 'Luma event reminder', markRead: false },
  { from: null,                             subject: /^Accepted:/i,          label: LABEL_CALENDAR, reason: 'Calendar acceptance', markRead: true },
  { from: null,                             subject: /^Declined:/i,          label: LABEL_CALENDAR, reason: 'Calendar decline', markRead: true },
  { from: null,                             subject: /^Tentative:/i,        label: LABEL_CALENDAR, reason: 'Calendar tentative', markRead: true },
  { from: null,                             subject: /^Updated invitation:/i, label: LABEL_CALENDAR, reason: 'Calendar update', markRead: false },
  { from: null,                             subject: /^Invitation:.*\d{4}/i, label: LABEL_CALENDAR, reason: 'Calendar invitation', markRead: false },

  // ── ~Receipts (generic) ──
  { from: /noreply@/i,                      subject: /Confirmed/i,           label: LABEL_RECEIPTS, reason: 'Confirmation receipt', markRead: false },

  // ── ~Newsletters ──
  { from: /@mail\.beehiiv\.com$/i,          subject: null,                   label: LABEL_NEWSLETTERS, reason: 'Newsletter platform', markRead: true },
  { from: /convertkit-mail/i,              subject: null,                   label: LABEL_NEWSLETTERS, reason: 'Newsletter platform', markRead: true },
  { from: /comms@ellabakercenter\.org/i,    subject: null,                   label: LABEL_NEWSLETTERS, reason: 'Ella Baker Center newsletter', markRead: false },
  { from: /@practicalfounders\.com/i,      subject: null,                   label: LABEL_NEWSLETTERS, reason: 'Practical Founders newsletter', markRead: true },
  { from: /@.*ccsend\.com$/i,            subject: null,                   label: LABEL_NEWSLETTERS, reason: 'Constant Contact newsletter', markRead: true },
  { from: /hello@instrumentl\.com/i,     subject: null,                   label: LABEL_NEWSLETTERS, reason: 'Instrumentl newsletter', markRead: true },

  // ── ~Marketing ──
  { from: /@partnernotification\.capitalone\.com/i, subject: null,           label: LABEL_MARKETING, reason: 'Capital One marketing', markRead: true },
  { from: /mail@update\.strava\.com/i,     subject: null,                   label: LABEL_MARKETING, reason: 'Strava marketing', markRead: true },
  { from: /jacksonfordc\.com/i,            subject: null,                   label: LABEL_MARKETING, reason: 'Political campaign email', markRead: false },
  { from: /livefreeusa\.org/i,             subject: null,                   label: LABEL_MARKETING, reason: 'Organization mass email', markRead: false },

  // ── ~Sales-Pitch (known domains) ──
  { from: /@(useclaritymail|oursprintops|joinforge|prpodpitch|upscalepulselab|boostbnxt|readingbrandlane)\./i,
                                            subject: null,                   label: LABEL_SALES_PITCH, reason: 'Known cold sales domain', markRead: true },
  { from: /dataforseo\.com/i,              subject: null,                   label: LABEL_SALES_PITCH, reason: 'DataForSEO vendor outreach', markRead: true },
  { from: /trestleiq\.com/i,              subject: null,                   label: LABEL_SALES_PITCH, reason: 'Trestle vendor outreach', markRead: true },
  { from: /tegus\.com/i,                  subject: null,                   label: LABEL_SALES_PITCH, reason: 'Tegus/AlphaSense consulting cold outreach', markRead: true },
  { from: /dialecticanet\.com/i,         subject: null,                   label: LABEL_SALES_PITCH, reason: 'Dialectica expert network cold outreach', markRead: true },
  { from: /handwritingocr\.com/i,        subject: null,                   label: LABEL_SALES_PITCH, reason: 'HandwritingOCR cold outreach', markRead: true },

  // ── !FYI ──
  { from: /@bishopodowd\.org$/i,            subject: null,                   label: LABEL_FYI, reason: 'School notification', markRead: false },
  { from: /@oaklandmontessori\.com$/i,      subject: null,                   label: LABEL_FYI, reason: 'School notification', markRead: false },
  { from: /no-reply@.*mybrightwheel\.com/i, subject: null,                   label: LABEL_FYI, reason: 'School notification (Brightwheel)', markRead: false },
  { from: /mailer@email\.naviance\.com/i,   subject: null,                   label: LABEL_FYI, reason: 'School notification (Naviance)', markRead: false },
  { from: /@leiya\.com$/i,                 subject: null,                   label: LABEL_FYI, reason: 'School notification (Leiya)', markRead: false },
  { from: /no-reply@documents\.powerschool\.com/i, subject: null,            label: LABEL_FYI, reason: 'School notification (PowerSchool)', markRead: false },
  { from: /^info@outdoorithm\.com$/i,       subject: /available|campsite/i,  label: LABEL_FYI, reason: 'Campsite availability alert', markRead: false },
  { from: /txt\.voice\.google\.com/i,      subject: null,                   label: LABEL_FYI, reason: 'Google Voice text', markRead: false },
  { from: /voice-noreply@google\.com/i,    subject: null,                   label: LABEL_FYI, reason: 'Google Voice voicemail', markRead: false },
  { from: /@hnhsoakland\.org$/i,          subject: null,                   label: LABEL_FYI, reason: 'School notification (Holy Names)', markRead: false },
  { from: /@fsenrollment\.com$/i,         subject: null,                   label: LABEL_FYI, reason: 'School enrollment notification', markRead: false },
  { from: /@parentsquare\.com$/i,         subject: null,                   label: LABEL_FYI, reason: 'School notification (ParentSquare)', markRead: false },
  { from: /Do_NotReply@.*dmvonline\.ca\.gov/i, subject: null,              label: LABEL_FYI, reason: 'CA DMV notification', markRead: false },
];

// ── Cold sales subject patterns (aggressive) ─────────────────────────
// These subjects from unknown senders strongly indicate cold outreach → ~Sales-Pitch
var COLD_SALES_SUBJECTS = [
  /^(?:re:\s*)?(?:a\s+)?gentle\s+nudge/i,
  /^(?:re:\s*)?(?:last\s+)?follow\s*-?\s*up\b/i,
  /^(?:re:\s*)?(?:just\s+)?following\s+up\b/i,
  /^(?:re:\s*)?(?:quick|one)\s+question/i,
  /^(?:re:\s*)?can\s+I\s+help/i,
  /^(?:re:\s*)?win\s+back\b/i,
  /^(?:re:\s*)?save\s+(?:time|hours?)\b/i,
  /^(?:re:\s*)?checking\s+in\b/i,
  /^(?:re:\s*)?circling\s+back\b/i,
  /^(?:re:\s*)?touching\s+base\b/i,
  /win\s+back\s+\d+\s+hours?/i,
  /UVA\s+Summer\s+Interns?\s+for/i,
  /^(?:re:\s*)?How\s+are\s+our\s+APIs/i,
];

// ── Cold sales domain keywords ───────────────────────────────────────
var COLD_DOMAIN_KEYWORDS = [
  'claritymail', 'sprintops', 'pulselab', 'brandlane', 'podpitch',
  'boostbnxt', 'forge.co', 'reachout', 'growthlab', 'funnelmail',
  'pipelinemail', 'hubreach', 'engagemail', 'convertlab', 'nurturemail',
  'salesreach', 'prospectmail', 'leadmail',
];

// ── Universal cold recruiter subjects (run even for known-good domains) ──
var UNIVERSAL_COLD_SUBJECTS = [
  /^(?:re:\s*)?Confidential\s+Opportunity/i,
  /^(?:re:\s*)?Strategic\s+Role\s+Alignment/i,
  /^Chief\s+Executive\s+Officer$/i,
];

// ── Cold recruiter username keywords (for personal email domains) ────
var COLD_RECRUITER_USERNAMES = [
  'recruiting', 'talentacquisition', 'executivesearch', 'headhunter',
];

var PERSONAL_EMAIL_DOMAINS = [
  'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com',
];

// ── Known good domains (never auto-skip these) ──────────────────────
var KNOWN_GOOD_DOMAINS = [
  'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com',
  'truesteele.com', 'kindora.co', 'outdoorithm.com', 'outdoorithmcollective.org',
  'google.com', 'andela.com', 'bridgespan.org', 'camelbackventures.org',
  'sff.org', 'ed.gov', 'blackbaud.com', 'uptogether.org', 'tenstrands.org',
  'collectivemoxie.com', 'measuresforjustice.org', 'sojo.net', 'omidyar.com',
  'learnupcenters.org', 'verizon.net', 'delta.com', 'goldenstate.com',
  'fullscale.ph', 'olegreensgroup.com', 'philanthropyforum.org',
  'rcenterprises.org', 'appsnxt.com', 'codepath.org', 'boyznthewood.org',
];

// ══════════════════════════════════════════════════════════════════════
// MAIN FUNCTIONS
// ══════════════════════════════════════════════════════════════════════

/**
 * Run on a time-driven trigger (every 5 minutes).
 * Processes unread threads from the last 2 days that don't already have triage labels.
 */
function triageNewEmails() {
  var exclusionParts = ALL_TRIAGE_LABELS.map(function(l) { return '-label:"' + l + '"'; }).join(' ');
  var query = 'is:unread newer_than:2d -category:{promotions social updates forums} ' + exclusionParts;

  var threads = GmailApp.search(query, 0, 100);
  if (threads.length === 0) return;

  var labelCache = {};
  var stats = {};

  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    var msgs = thread.getMessages();
    var lastMsg = msgs[msgs.length - 1];

    var from = lastMsg.getFrom();
    var subject = lastMsg.getSubject();
    var fromEmail = extractEmail(from);
    var fromDomain = extractDomain(fromEmail);

    var result = classifyEmail(fromEmail, fromDomain, subject);

    var gmailLabel = getLabel(result.label, labelCache);
    thread.addLabel(gmailLabel);

    if (result.markRead) {
      thread.markRead();
    }

    stats[result.label] = (stats[result.label] || 0) + 1;
  }

  var summary = Object.keys(stats).map(function(k) { return k + ': ' + stats[k]; }).join(', ');
  Logger.log('Triaged ' + threads.length + ' threads — ' + summary);
}

/**
 * Classify a single email. Returns { label, reason, markRead }.
 */
function classifyEmail(fromEmail, fromDomain, subject) {
  // Check explicit rules first
  for (var i = 0; i < RULES.length; i++) {
    var rule = RULES[i];
    var fromMatch = !rule.from || rule.from.test(fromEmail);
    var subjMatch = !rule.subject || rule.subject.test(subject);
    if (fromMatch && subjMatch) {
      return { label: rule.label, reason: rule.reason, markRead: rule.markRead };
    }
  }

  // Universal cold recruiter subject patterns (run for ALL domains)
  for (var s = 0; s < UNIVERSAL_COLD_SUBJECTS.length; s++) {
    if (UNIVERSAL_COLD_SUBJECTS[s].test(subject)) {
      return { label: LABEL_SALES_PITCH, reason: 'Cold recruiter subject pattern', markRead: true };
    }
  }

  // Cold recruiter usernames on personal email domains (gmail, yahoo, etc.)
  if (PERSONAL_EMAIL_DOMAINS.indexOf(fromDomain) !== -1) {
    var username = fromEmail.split('@')[0];
    for (var u = 0; u < COLD_RECRUITER_USERNAMES.length; u++) {
      if (username.indexOf(COLD_RECRUITER_USERNAMES[u]) !== -1) {
        return { label: LABEL_SALES_PITCH, reason: 'Recruiter keyword in email username', markRead: true };
      }
    }
  }

  // Check cold sales patterns (only for non-known-good domains)
  if (!isKnownGoodDomain(fromDomain)) {
    for (var k = 0; k < COLD_SALES_SUBJECTS.length; k++) {
      if (COLD_SALES_SUBJECTS[k].test(subject)) {
        return { label: LABEL_SALES_PITCH, reason: 'Cold sales subject pattern', markRead: true };
      }
    }

    // Check cold domain keywords
    for (var d = 0; d < COLD_DOMAIN_KEYWORDS.length; d++) {
      if (fromDomain.indexOf(COLD_DOMAIN_KEYWORDS[d]) !== -1) {
        return { label: LABEL_SALES_PITCH, reason: 'Cold sales domain keyword', markRead: true };
      }
    }

    // Justin's name as personalization token from unknown sender
    if (/\bjustin\b/i.test(subject) && /follow|nudge|check|touch|reach/i.test(subject)) {
      return { label: LABEL_SALES_PITCH, reason: 'Personalization token in subject', markRead: true };
    }
  }

  // Default: !Action (genuine emails pass through)
  return { label: LABEL_ACTION, reason: 'No skip/fyi rule matched', markRead: false };
}

// ══════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════

function extractEmail(fromHeader) {
  var match = fromHeader.match(/<([^>]+)>/);
  return match ? match[1].toLowerCase() : fromHeader.toLowerCase().trim();
}

function extractDomain(email) {
  var parts = email.split('@');
  return parts.length > 1 ? parts[1] : '';
}

function isKnownGoodDomain(domain) {
  for (var i = 0; i < KNOWN_GOOD_DOMAINS.length; i++) {
    if (domain === KNOWN_GOOD_DOMAINS[i]) return true;
  }
  if (domain.match(/\.(gov|edu|mil)$/)) return true;
  return false;
}

function getLabel(labelName, cache) {
  if (cache[labelName]) return cache[labelName];
  var label = GmailApp.getUserLabelByName(labelName);
  if (!label) {
    label = GmailApp.createLabel(labelName);
  }
  cache[labelName] = label;
  return label;
}

// ══════════════════════════════════════════════════════════════════════
// SETUP & MANAGEMENT
// ══════════════════════════════════════════════════════════════════════

/**
 * Run once to set up the time-driven trigger.
 */
function setupTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'triageNewEmails') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  ScriptApp.newTrigger('triageNewEmails')
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log('Trigger set up: triageNewEmails every 5 minutes');
}

/**
 * Run once to backfill labels on recent unread emails.
 */
function backfillLabels() {
  var exclusionParts = ALL_TRIAGE_LABELS.map(function(l) { return '-label:"' + l + '"'; }).join(' ');
  var query = 'is:unread newer_than:21d -category:{promotions social updates forums} ' + exclusionParts;

  var threads = GmailApp.search(query, 0, 200);

  var labelCache = {};
  var stats = {};

  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    var msgs = thread.getMessages();
    var lastMsg = msgs[msgs.length - 1];

    var from = lastMsg.getFrom();
    var subject = lastMsg.getSubject();
    var fromEmail = extractEmail(from);
    var fromDomain = extractDomain(fromEmail);

    var result = classifyEmail(fromEmail, fromDomain, subject);

    var gmailLabel = getLabel(result.label, labelCache);
    thread.addLabel(gmailLabel);

    if (result.markRead) {
      thread.markRead();
    }

    stats[result.label] = (stats[result.label] || 0) + 1;
  }

  var summary = Object.keys(stats).map(function(k) { return k + ': ' + stats[k]; }).join(', ');
  Logger.log('Backfilled ' + threads.length + ' threads — ' + summary);
}

/**
 * Re-process emails currently labeled !Action using updated rules.
 * Run after adding new rules to re-classify emails that were previously
 * labeled !Action but should now be ~Notifications, ~ErrorMonitor, etc.
 */
function reprocessActionEmails() {
  var actionLabel = GmailApp.getUserLabelByName(LABEL_ACTION);
  if (!actionLabel) {
    Logger.log('No !Action label found');
    return;
  }

  // Use label object directly — GmailApp.search() doesn't handle '!' in label names reliably
  var threads = actionLabel.getThreads(0, 500);
  var labelCache = {};
  var stats = { kept: 0, reclassified: 0 };
  var reclassDetails = {};

  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    var msgs = thread.getMessages();
    var lastMsg = msgs[msgs.length - 1];

    var from = lastMsg.getFrom();
    var subject = lastMsg.getSubject();
    var fromEmail = extractEmail(from);
    var fromDomain = extractDomain(fromEmail);

    var result = classifyEmail(fromEmail, fromDomain, subject);

    if (result.label !== LABEL_ACTION) {
      // Remove !Action, apply new label
      thread.removeLabel(actionLabel);
      var newLabel = getLabel(result.label, labelCache);
      thread.addLabel(newLabel);

      if (result.markRead) {
        thread.markRead();
      }

      stats.reclassified++;
      reclassDetails[result.label] = (reclassDetails[result.label] || 0) + 1;
    } else {
      stats.kept++;
    }
  }

  var detail = Object.keys(reclassDetails).map(function(k) { return k + ': ' + reclassDetails[k]; }).join(', ');
  Logger.log('Reprocessed ' + threads.length + ' !Action threads — kept ' + stats.kept + ', reclassified ' + stats.reclassified + ' (' + detail + ')');
}

/**
 * Remove AI-applied triage labels (useful for resetting after rule changes).
 * Only removes labels that were applied by this script, not manually applied ones.
 */
function removeAllTriageLabels() {
  var labelCache = {};
  var allTriaged = GmailApp.search('label:_ai', 0, 500);

  for (var i = 0; i < allTriaged.length; i++) {
    for (var j = 0; j < ALL_TRIAGE_LABELS.length; j++) {
      var label = getLabel(ALL_TRIAGE_LABELS[j], labelCache);
      allTriaged[i].removeLabel(label);
    }
  }

  Logger.log('Removed triage labels from ' + allTriaged.length + ' threads');
}
