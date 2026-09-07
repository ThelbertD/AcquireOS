# Copy Rules

The constraints that apply to every client, in every industry, regardless of voice. The brain
file says what to write; this says what may not be written.

These are not style preferences. Each one exists because breaking it costs deliverability,
replies, or legal exposure — and the reason is stated in every case, because a rule whose
reason is not understood gets broken the first time it is inconvenient.

Where a rule differs by jurisdiction it is marked and branched. Where it differs by channel it
is marked and branched.

---

## 1. Length

Per message, excluding signature and unsubscribe footer.

| Node | Channel | Body words | Subject | Hard ceiling |
|---|---|---|---|---|
| Opening touch | Email | 50–90 | 3–6 words | 120 words |
| Second angle | Email | 50–90 | 3–6 words | 120 words |
| Proof touch | Email | 60–110 | 3–6 words | 130 words |
| Objection touch | Email | 50–90 | 3–6 words | 120 words |
| Closing touch | Email | 25–50 | 2–5 words | 70 words |
| Any nudge | SMS | 20–35 words | n/a | 160 characters total |
| Follow-through acknowledgement | Email | 30–60 | 3–6 words | 90 words |
| Follow-through delivery | Email | 60–150 | 3–6 words | 200 words |

**Why.** A cold message is read on a phone, in a list, in about four seconds. Beyond roughly 120
words the reader is deciding whether to read rather than reading. The follow-through delivery is
the one exception: by then the prospect has asked for something, and length is warranted.

**Subject lines.** Lowercase or sentence case. No title case, which reads as a newsletter. No
colons separating a topic from a subtitle, which reads as a press release. No question marks in
the opening touch — a question in a subject from an unknown sender reads as a hook.

**Sentence length.** Under 20 words average. One idea per sentence.

**Paragraphs.** Maximum three lines each. Maximum four paragraphs per email.

---

## 2. Links and images

### During warmup — weeks 1 to 4

| Element | Rule |
|---|---|
| Links | **None.** In any message, in any node. |
| Images | **None.** Including signature logos and tracking pixels. |
| Attachments | **None.** Ever, at any stage. |
| Tracking | Open tracking off. Click tracking off. |

**Why.** A new domain with no sending history, sending a message containing a link, to a
stranger, is the exact shape of the thing filters are built to catch. The link adds nothing in
week 1 that a reply cannot deliver in week 5.

### After clearance

| Element | Rule |
|---|---|
| Links in the opening touch | **Still none.** This one does not expire. |
| Links in later touches | Maximum one per message |
| Link destination | A page on `{{PRIMARY_DOMAIN}}`. Never a shortener, never a redirect chain. |
| Tracking domain | `{{TRACKING_SUBDOMAIN}}` only. Never the sending platform's shared tracking domain. |
| Images | Maximum one, and only where it carries information a sentence cannot. Never a logo. |
| Attachments | **None.** Ever. |
| Text-to-HTML ratio | Plain text, or HTML that is indistinguishable from plain text |

**Why no link in the opening touch, permanently.** The first message from an unknown sender
containing a link is the single strongest content-based spam signal available, and a prospect
who has not decided whether they trust the sender does not click. The ask in the opening touch
is a reply. A reply is a stronger signal to the mailbox provider than any click, and it is a
better outcome for the client.

**Why no shorteners.** Shortener domains are shared by every user of that shortener, including
the malicious ones, and they are blocklisted accordingly. They also hide the destination, which
is what filters treat them as doing.

**Why no attachments.** Most corporate filters strip, quarantine or score them heavily. An
attachment from an unknown sender is what filters are most cautious about, for good reason.

---

## 3. Spam-trigger patterns

Filters do not work from a banned-word list, and no single word below will send a message to
spam on its own. What they respond to is the accumulation of these patterns alongside a weak
sending reputation. Avoid them because they read as marketing, and marketing from a stranger is
what gets deleted.

### Never

| Pattern | Example of what to avoid |
|---|---|
| Currency amounts in subject lines | Any figure with a currency symbol |
| ALL CAPS in a subject line, or more than one capitalised word in a row | — |
| More than one exclamation mark in a message. Ideally zero. | — |
| Obfuscated spelling to evade filters | Characters substituted inside a word |
| Manufactured urgency | "Act now", "limited time", "expires today", "final notice" |
| Manufactured scarcity that is not real | "Only 3 spots left", where there are not |
| Guarantee language | "Guaranteed", "risk-free", "100%", "no-risk" |
| Financial promises | "Double your", "10x your", "make money" |
| Free-as-a-hook | "Free trial" as a subject line, "100% free", "no cost" |
| Fake reply or forward prefixes | `Re:` or `Fwd:` on a message that is neither |
| Fake personal context | "As discussed", "following up on our conversation", where there was none |
| Fake urgency in the sender name | "URGENT" or similar in the display name |
| Hidden text, white-on-white, zero-size fonts | — |
| Multiple font colours or sizes | — |
| Deceptive subject lines | Anything that misrepresents the message content — a specific CAN-SPAM violation |

### Use sparingly

| Pattern | Why |
|---|---|
| The word "opportunity" | Almost always precedes a pitch |
| "Quick question" | So overused as an opener that it now signals a template |
| "I hope this finds you well" | Signals a template; wastes the first line, which is the one shown in preview |
| "Just following up" | Says the message has no new content, which is usually true and always a reason to delete |
| "I'll keep this short" | Then do not spend a line saying so |
| "Circling back" / "touching base" | Filler with no information |
| Percentages and metrics in the subject line | Not banned, but reads as an ad. Better placed in the body with its source. |

**The general test.** Read the message aloud. If it sounds like something a person would send,
it is fine. If it sounds like something a company would send, rewrite it.

---

## 4. Personalisation tokens

Every token must have a fallback that produces a correct, natural sentence when the source field
is empty. This is not defensive coding — it is the most visible failure a prospect can see, and
it is entirely preventable.

| Token | Fallback | Sentence must read correctly both ways |
|---|---|---|
| First name | Omit the greeting entirely, or use "Hi there" | "Hi ," is the single most common cold email failure |
| Company name | "your team", "your side" | Never leave a bare gap |
| Job title | Restructure the sentence to not need it | Never "as a , you..." |
| Industry or sector | Restructure the sentence | Never a bare gap |
| Location | Omit the clause | Never "based in ," |
| Recent event or trigger | **The sentence is removed entirely** | See below |

### Rules

1. **Every token has a fallback, and the fallback is written before the token is used.**
2. **The message must read correctly with every token empty.** Test it that way. This is a
   pre-launch checklist item in `04-cadence/crm-build-checklist.md`.
3. **No token in the subject line.** Subject lines are truncated in preview and a token failure
   there is visible before the message is even opened.
4. **A trigger-based sentence is deleted, not defaulted.** If the copy references something the
   client did — a funding round, a hire, a launch — and the field is empty, the whole sentence
   goes. A generic substitute reads as a template that failed, which is worse than never having
   claimed personalisation.
5. **No token may render as literal `{{TOKEN}}` text.** If the platform can output a raw token
   string on failure, that is a platform defect to work around, not a risk to accept.
6. **Maximum two tokens per message.** Above two, the message reads as a mail merge no matter
   how good the fallbacks are.
7. **Personalisation is not a token.** A sentence that could only have been written to this one
   prospect is worth more than five perfectly-filled fields.

---

## 5. Claims

**No claim goes in the copy that is not in section 3.1 of the brain file.**

| Rule | Detail |
|---|---|
| Every claim is substantiable | The client must be able to produce evidence on request |
| Every metric has a source | "Cut processing time 40%" needs a named source, even if not published |
| Named references are cleared in writing | A customer named without permission is a relationship the client loses |
| No implied claims | "Companies like yours see..." implies a dataset. If there is no dataset, there is no sentence. |
| No comparative claims about competitors | Comparative advertising carries specific rules in several jurisdictions and gains nothing in a cold email |
| No claims about the prospect's own numbers | You do not know their numbers. Guessing them and being wrong ends the conversation. |
| Hedging is not a fix | "Up to", "as much as", "some clients" do not make an unevidenced claim safe |

**Why this is a hard rule.** Unsubstantiated claims in commercial communications are actionable
under the FTC Act in the US and the Consumer Protection from Unfair Trading Regulations in the
UK. Beyond the legal exposure: an unevidenced claim is what turns a message that would have been
ignored into one that gets reported, and complaints damage the domain for everyone on it.

**If the brain file has no proof points**, the copy has no proof, and the correct response is to
go back to the client — not to write around it and not to invent something plausible.

---

## 6. Compliance requirements per message

### Every email, every jurisdiction

- [ ] `{{CLIENT_POSTAL_ADDRESS}}` — a valid physical postal address, in every message
- [ ] A working opt-out mechanism, requiring no login and no account
- [ ] `{{UNSUBSCRIBE_URL}}` in the visible footer
- [ ] `List-Unsubscribe` and `List-Unsubscribe-Post` headers
- [ ] Accurate `From`, `Reply-To` and routing information
- [ ] A subject line that accurately reflects the message
- [ ] Sender identified clearly enough that the recipient knows who is writing
- [ ] `{{REQUIRED_DISCLAIMER}}`, where the client's counsel requires one

### By jurisdiction

| Requirement | US (CAN-SPAM) | UK / EU (GDPR + PECR) | Canada (CASL) |
|---|---|---|---|
| Basis needed before first message | None; opt-out model | Legitimate interest with a documented balancing test, corporate subscribers only | Consent: express, or implied within its window |
| Implied consent window | n/a | n/a | 6 months from an inquiry; 2 years from the end of a business relationship |
| Physical postal address | Required | Required in practice as sender identification | Required |
| Opt-out honoured within | 10 business days | Without undue delay | 10 business days |
| Opt-out must remain functional for | 30 days after sending | No fixed period | 60 days after sending |
| Sender identification | No deceptive headers or subject lines | Controller identity and processing purpose disclosed | Sender identified with contact details valid for 60 days |
| Right of access / erasure on request | n/a | Yes, within one month | n/a |
| Personal addresses and sole traders | Permitted | **Not permitted** under PECR without consent — includes sole traders and partnerships in the UK | Consent required as for any recipient |

**Build to the strictest reading and the differences stop mattering.** Suppress immediately
rather than within 10 days. Keep the opt-out live permanently rather than for 30 or 60 days.
Identify the sender fully in every message. There is no operational cost to any of these, and it
removes a whole class of jurisdiction-tracking from the build.

**The one place you cannot build to the strictest reading and move on is Canada.** CASL requires
a basis *before* the first message, so it cannot be satisfied retroactively by good opt-out
handling. Either the basis exists and is recorded per contact, or Canada is excluded from the
list. See `04-cadence/cadence-spec.md`, gate G2.

### Every SMS

- [ ] `sms_consent = true` on the contact, with a recorded source
- [ ] Sender identified in the message body — an SMS from an unknown number is a complaint
- [ ] `{{SMS_STOP_KEYWORD}}` honoured, and propagated to email suppression
- [ ] `{{SMS_HELP_KEYWORD}}` returns the client's identity and contact details
- [ ] Sent only 09:00–18:00 recipient local time, weekdays
- [ ] Under 160 characters, so it arrives as one message

> Cold SMS to a number the prospect did not supply carries statutory per-message damages under
> the TCPA in the US, and is a PECR breach in the UK. This is the highest-risk item in the whole
> system and the one most often waved through.

---

## 7. Structure

The shape every cold message follows, regardless of node or client.

| Position | Content | Words |
|---|---|---|
| Line 1 | Why this person, specifically. Never a greeting-plus-pleasantry. | 10–20 |
| Line 2–3 | The problem, in their language, as an observation rather than a claim about them | 20–35 |
| Line 4–5 | What the client does about it, concretely. One proof point if the node calls for it. | 20–40 |
| Line 6 | The ask. One thing. Ending in a question mark. | 8–15 |
| Signature | Name, title, company, postal address | — |
| Footer | Unsubscribe link | — |

**Rules**

- The first line is the preview text. It is read before the message is opened, and it decides
  whether the message is opened. Never spend it on "I hope this finds you well."
- One ask per message. Two asks get neither.
- The ask ends in a question mark. A statement is easier to not answer than a question.
- No postscript in a cold email. A P.S. is a direct-mail device and reads as one.
- Never open with the sender's own name, company, or role. The prospect does not yet care.
- Never open with a compliment about the prospect's company. It reads as research performed by
  a machine, because it usually was.

---

## 8. Pre-send checklist

Every message, every node, before it goes into `{{CRM_NAME}}`.

**Length and structure**

- [ ] Within the word count for its node
- [ ] Subject 3–6 words, sentence case, no token
- [ ] Maximum four paragraphs, maximum three lines each
- [ ] First line is specific to the recipient, not a pleasantry
- [ ] Exactly one ask, phrased as a question

**Content**

- [ ] Every claim traces to a proof point in the brain file
- [ ] No competitor from `{{COMPETITOR_EXCLUSION_LIST}}` is named
- [ ] No word from `{{FORBIDDEN_WORDS}}` appears
- [ ] No spam-trigger pattern from section 3
- [ ] No claim about the prospect's own numbers
- [ ] Reads as something a person would send, when read aloud

**Tokens**

- [ ] Maximum two
- [ ] None in the subject line
- [ ] Every token has a fallback
- [ ] The message reads correctly with all tokens empty — tested, not assumed
- [ ] Trigger-based sentences are deleted when their field is empty, not defaulted

**Links and images**

- [ ] No links in the opening touch
- [ ] No links at all during warmup
- [ ] Maximum one link after clearance, pointing at `{{PRIMARY_DOMAIN}}`
- [ ] No shorteners, no redirect chains, no shared tracking domain
- [ ] No attachments
- [ ] No images during warmup; maximum one after, and never a logo

**Compliance**

- [ ] `{{CLIENT_POSTAL_ADDRESS}}` present
- [ ] `{{UNSUBSCRIBE_URL}}` present and working
- [ ] `List-Unsubscribe` header configured
- [ ] Subject accurately reflects the message
- [ ] Sender identification accurate
- [ ] `{{REQUIRED_DISCLAIMER}}` present where required
- [ ] Correct for every jurisdiction in `{{JURISDICTIONS}}`

**Final**

- [ ] Sent to yourself first, and read on a phone
- [ ] Someone other than the writer has read it
