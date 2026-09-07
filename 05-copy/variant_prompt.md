# Variant Prompt

A prompt template for generating copy variants for one cadence node.

**How to use it.** Fill the placeholders in the block below from the completed brain file and
the node map, paste `05-copy/copy-rules.md` in full where marked, and send the whole thing to a
capable language model. Everything above and below the fenced block is instruction for you, not
for the model — send only what is inside the fence.

**One node at a time.** Do not ask for a whole sequence in one call. The model will optimise for
variety across the sequence and produce nodes that are individually weaker, and you lose the
ability to iterate on a single node without regenerating the rest.

**The variants must differ in angle, not in wording.** This is the whole point, and it is the
thing a model will quietly not do unless it is forced to. Three rephrasings of one argument tell
you nothing when you test them: whichever wins, you have learned that a sentence was slightly
better than another sentence. Three genuinely different arguments tell you which argument
works, which is a finding you can use everywhere else.

---

## The prompt

```
You are writing cold outbound copy for one node of a multi-touch sequence.

Produce {{VARIANT_COUNT}} variants. Each must take a DIFFERENT ANGLE, not different wording of
the same angle. This is the primary requirement and it is checked first — see ANGLES below.

=====================================================================
THE CLIENT
=====================================================================

Client:             {{CLIENT_NAME}}
What they sell:     {{OFFER_DESCRIPTION}}
The problem:        {{PROBLEM_STATEMENT}}
What changes:       [ from brain file 2.4 ]

=====================================================================
THE READER
=====================================================================

ICP:                {{ICP_DESCRIPTION}}
Lane:               {{SEGMENT_LANE}}
What is specifically true of this lane and not the others:
                    [ from the segment definition ]
Job titles:         [ from brain file 1.1 ]
Their situation:    [ from brain file 1.3, the trigger, if there is one ]
NOT for:            [ from brain file 1.2 ]

=====================================================================
THIS NODE
=====================================================================

Node:               {{NODE_ID}}
Day:                [ from the node map ]
Channel:            [ email | sms ]
Purpose:            [ from the node map — copy the purpose line verbatim ]
The ask:            {{PRIMARY_CTA}}
Word count:         [ from copy-rules.md section 1, for this node and channel ]

What the reader has already received, if anything:
[ One line per prior node: its purpose and its angle. Give the ANGLE, not the copy — the model
  writing node 4 needs to know node 1 argued from cost and node 3 argued from risk, so it does
  not argue either again. Pasting the earlier copy makes it imitate the phrasing. ]

=====================================================================
MATERIAL YOU MAY USE
=====================================================================

Proof points — you may use ONLY these, exactly as stated, and nothing else:
  1. {{PROOF_POINT_1}}
  2. {{PROOF_POINT_2}}
  3. {{PROOF_POINT_3}}

Objections and the client's real answers:
  1. {{OBJECTION_1}} -> {{REBUTTAL_1}}
  2. {{OBJECTION_2}} -> {{REBUTTAL_2}}
  3. {{OBJECTION_3}} -> {{REBUTTAL_3}}

Sender:             {{SENDER_PERSONA_NAME}}, {{SENDER_PERSONA_TITLE}}
Available tokens:   [ list each token and its fallback, e.g. first_name -> omit greeting ]

=====================================================================
VOICE
=====================================================================

Tone:               {{TONE_CONSTRAINTS}}
Words the client uses for their category and customers:
                    [ from brain file 5.2 ]
Never use:          {{FORBIDDEN_WORDS}}
Never mention:      {{COMPETITOR_EXCLUSION_LIST}}
Required in every message: {{REQUIRED_DISCLAIMER}}

Sample of the client's own writing, for voice only — do not reuse its content or structure:
[ paste from brain file 5.6, or write "none supplied" ]

=====================================================================
ANGLES — THE PRIMARY REQUIREMENT
=====================================================================

An ANGLE is the argument the message makes. Two messages share an angle if they would be
answered by the same objection.

Each variant must use a different angle from this list. State which one you used.

  cost          What the problem costs them, in money or time
  risk          What goes wrong if it continues
  effort        How much manual work it currently takes
  speed         How long it takes now versus how long it could take
  status-quo    Why the current approach made sense once and no longer does
  peer          What comparable organisations have changed
  trigger       Something that has just happened at their company
  contrarian    A common assumption in their situation that is wrong
  specific      One narrow, concrete detail of the problem, in depth
  question      A genuine question you do not know the answer to
  offer         Something concrete you will do for them before any commitment

FAILS the requirement — these are the same angle rephrased:
  "This costs you time"  /  "You're losing hours to this"  /  "Think of the time you'd save"

PASSES — three different angles:
  A (cost)     what the manual process costs per month
  B (risk)     what happens the week it goes wrong
  C (peer)     what a comparable organisation changed, and what happened

=====================================================================
RULES
=====================================================================

[ PASTE THE FULL CONTENTS OF 05-copy/copy-rules.md HERE ]

=====================================================================
HARD CONSTRAINTS
=====================================================================

1. Use ONLY the proof points listed above, stated as they are stated. Invent nothing. If a
   variant needs a proof point that is not listed, do not write that variant — say so instead.
2. Make no claim about the reader's own numbers, systems or situation that is not given above.
3. Every variant must be a different angle. Name the angle.
4. Maximum two personalisation tokens. None in the subject line. Every message must read
   correctly with every token empty — write it that way and check it.
5. No links. No images. No attachments.
6. Stay within the word count. Count the words.
7. No greeting-plus-pleasantry opening. The first line is the preview text and it must say
   something specific to this reader.
8. One ask, phrased as a question.
9. Read each variant aloud in your head. If it sounds like a company wrote it rather than a
   person, rewrite it before returning it.

=====================================================================
OUTPUT FORMAT
=====================================================================

For each of the {{VARIANT_COUNT}} variants:

--- VARIANT [n] ---
ANGLE:      [one of the angle names above]
WHY:        [one sentence on why this angle suits this lane at this node]
SUBJECT:    [3-6 words, sentence case, no token]
BODY:
[the message, no signature, no footer]

WORD COUNT: [number]
TOKENS:     [each token used, and its fallback]
PROOF USED: [which numbered proof point, or "none"]
--- END ---

After all variants:

ANGLE CHECK:  [confirm all {{VARIANT_COUNT}} angles differ; if two are close, say which and why
               you kept both]
FLAGGED:      [anything you could not write without inventing, any rule that conflicted with
               another, anything you were asked for that the material does not support]
```

---

## After generation

The model's output is a draft, not copy. Run this before anything reaches `{{CRM_NAME}}`.

### 1. Check the angles are genuinely different

For each pair of variants, ask: **would the same objection kill both?** If yes, they are the
same angle and one of them is wasting a test slot. Regenerate the weaker one with an explicit
instruction naming an angle from the list.

This is the check that gets skipped. A model will return three variants that look different
because the sentences differ, and unless you apply this test, you will test three phrasings of
one argument and learn nothing about which argument works.

### 2. Verify every claim

Every factual statement traces to a numbered proof point, stated as the brain file states it.
Anything that does not trace, comes out. Models produce plausible specifics — a percentage, a
timeframe, a customer count — and plausible specifics that nobody can evidence are the exact
exposure `copy-rules.md` section 5 exists to prevent.

Read for it specifically. It is the failure mode that survives every other check, because
invented numbers read as confident writing.

### 3. Run the pre-send checklist

Section 8 of `copy-rules.md`, every line, every variant.

### 4. Test the empty-token rendering

Strip every token and read it. "Hi ," and "as a , you" are what this catches, and they are what
a prospect sees.

### 5. Have a person rewrite the first line

The opening line is the preview text and it decides whether the message is opened. It is also
the line a model writes most generically, because it is the line that most benefits from
knowing something the model was not told. Rewriting it by hand is usually the difference between
a 2% and a 5% reply rate, and it takes a minute per variant.

### 6. Read it aloud

If it sounds like a company wrote it, it did.

---

## Testing the variants

- **One node at a time.** Testing variants at two nodes simultaneously means neither result is
  attributable.
- **Split evenly at the lane level**, not across the whole list. A variant that wins in one lane
  and loses in another is a finding, and pooling the lanes hides it.
- **Reply rate is the metric.** Not opens — open data is unreliable enough to produce a
  confident wrong answer.
- **Wait for enough replies to mean something.** Two replies against one is not a result. Under
  roughly 30 replies per variant, the difference you are looking at is noise.
- **The winning angle transfers.** If `cost` wins at the opening node, it is worth trying at the
  proof node too, and it is worth telling the client, because it is a fact about their buyers
  rather than about their email.
- **Keep the losers.** A variant that lost this quarter against this list may win against the
  next segment. Record the angle, the lane, the node and the reply rate — the log of what has
  been tried is worth more after six months than any individual message in it.

---

## Common failures

| Failure | How it shows up | Fix |
|---|---|---|
| Variants differ in wording only | All three answered by the same objection | Regenerate with an explicit angle named per variant |
| Invented proof | A specific number that is not in the brain file | Delete it. Check every number against section 3.1. |
| Claims about the reader's situation | "You're probably spending 10 hours a week on this" | Remove. You do not know that. |
| Generic opening line | "I hope this finds you well", "Quick question" | Rewrite by hand |
| Two asks | A question plus "or just reply if you'd like the guide" | Cut one |
| Token with no fallback | "Hi ," in the empty-token test | Add the fallback, retest |
| Over the word count | 140 words for a 90-word node | Cut. The last two sentences are usually the ones. |
| Sounds like a company | Obvious when read aloud | Rewrite in the sender's actual voice |
| Model refused a rule to satisfy another | Usually length versus proof | The word count wins. Cut the proof point and move it to another node. |
