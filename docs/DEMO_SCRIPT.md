# Judge demo script (2:30)

## 0:00–0:20 — Problem

“After a care transition, patients may hold a discharge note, a newer prescription, and a pharmacy
label. When wording or instructions differ, the patient is forced to reconcile them. CareAlign is a
safety net: it finds what needs clarification without deciding which order is correct.”

## 0:20–0:40 — Safety boundary

Show the synthetic-only notice and medical disclaimer. State: “This demonstration contains no real
patient data. CareAlign never recommends starting, stopping, or changing medication.”

## 0:40–1:15 — Longitudinal comparison

Load the safe demo. Point out that both records say **metoprolol tartrate**, avoiding a false
salt/form comparison. Run analysis. Show the collapsed frequency difference and the possible
atorvastatin omission. Read the source spans—not just the AI summary.

## 1:15–1:40 — Human handoff

Open “Ask your care team,” copy the question, and show Print/Download. Enter a fictional care-team
response. Point to “User-entered · not verified by CareAlign” and state that AI cannot resolve a flag.

## 1:40–2:05 — Teach-back

Explain the non-conflicted lisinopril instruction in plain language. Show that unresolved metoprolol
and atorvastatin items are excluded from the checklist. Emphasize supportive feedback rather than a
patient test.

## 2:05–2:20 — Safe failure

Show an unsupported PRN/taper example or invalid chronology. Explain that uncertainty is surfaced,
never converted into “no conflict.”

## 2:20–2:30 — Close

“AI understands language; deterministic rules enforce the safety boundary; every alert keeps its
source; and a human closes the loop.”
