export const meta = {
  name: 'cpi-item-review-part',
  description: 'Item review part: diagnose (if not precomputed) and verify a subset of batches; returns verified item entries',
  phases: [
    { title: 'Diagnose', detail: 'one agent per batch not yet diagnosed' },
    { title: 'Verify', detail: 'one adversarial verifier per batch (data + method lenses combined), returns the final entries' },
  ],
}
const DIR = '/tmp/claude-0/-home-user-CPI-Web-Scarping/60ceec26-2c73-59ee-8091-dd0a0c8d8ad5/scratchpad/agents/itemreview'
const batches = args.batches

const DIAGS = ['ok','shop_effect','promo_price','unit_or_pack','wrong_product','one_shop_only','out_of_stock_online','brand_not_online','no_barcode_loose','set_estimate_drift','spec_ambiguous','other']
const FIXES = ['keep','regular_price','pin_product','fix_unit_or_pack','fixed_sample','substitute_brand','other_source','ask_office','none','rejected']
const PRODUCT = { type: 'object', properties: { outlet: { type: 'string' }, title: { type: 'string' }, url: { type: 'string' }, oct_regular: { type: ['number', 'null'] } }, required: ['outlet', 'title', 'url', 'oct_regular'] }
const ITEM_PROPS = {
  code: { type: 'string' }, diagnosis: { type: 'string', enum: DIAGS }, explanation: { type: 'string' }, fix_type: { type: 'string', enum: FIXES },
  fix_products: { type: 'array', items: PRODUCT }, rule_change: { type: 'string' },
  expected_price_after: { type: ['number', 'null'] }, expected_pct_after: { type: ['number', 'null'] },
  within10_after: { type: 'boolean' }, covered_after: { type: 'boolean' }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  user_decision: { type: 'string' }, calibration_only: { type: 'boolean' } }
const ITEM_REQ = ['code', 'diagnosis', 'explanation', 'fix_type', 'fix_products', 'rule_change', 'expected_price_after', 'expected_pct_after', 'within10_after', 'covered_after', 'confidence', 'user_decision', 'calibration_only']
const DIAG_SCHEMA = { type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: ITEM_PROPS, required: ITEM_REQ } } }, required: ['items'] }
const FINAL_SCHEMA = { type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: { ...ITEM_PROPS, verdict: { type: 'string', enum: ['accept', 'modify', 'reject'] }, verifier_notes: { type: 'string' } }, required: [...ITEM_REQ, 'verdict', 'verifier_notes'] } } }, required: ['items'] }

const common = `Read ${DIR}/brief.md completely first: it holds the goal, the facts, the policy limits, the data format, the diagnosis and fix vocabularies and the arithmetic rule. Work OFFLINE and READ-ONLY (no web requests, no repo edits, write nothing outside ${DIR}/scratch_<yourlabel>/ if you need scratch files).`

function diagnosePrompt(b) {
  return `${common}

You are the DIAGNOSER for batch ${b.batch} (${b.group}, ${b.n} items): ${DIR}/${b.file}
For EVERY item in the batch, produce one entry (all ${b.n} codes, none skipped). Work item by item:
1. Read the official spec (desc, unit, brand, barcode, origin, qty), our status and comparison, our_october (what we matched per shop, statuses), and the catalogue_candidates.
2. Decide the single diagnosis. For exact_match items within ±10% (pct_vs_sep or pct_regular) the diagnosis is "ok" and fix_type "keep" — do not invent work.
3. Propose the single most effective fix within policy, naming the exact listing(s) (title, url, oct_regular from the candidates or our_october). For fresh/loose goods propose a fixed_sample of 2-4 listings per shop that match the spec (type, size basis, origin where the official says so). For items whose official brand is not sold online, propose substitute_brand with a named alternative of the same type and size and set user_decision. If the right product is simply absent online, say other_source or none.
4. Compute expected_price_after (2-shop mean of regular prices, converted to the official unit), expected_pct_after vs official September, within10_after, covered_after. Show conversions in the explanation. Never choose a product because its price matches the official; if you did, set calibration_only=true.
Also use the deeper sources (CPI_basket_12-29_Oct.csv rows for the item, the catalogue history) when the batch record is not enough — e.g. to see why a barcode search returned not_found, or to find a listing the candidates missed (grep the catalogue titles).
Return the structured items array only.`
}
function verifyPrompt(b, diagRef) {
  return `${common}

You are the VERIFIER for batch ${b.batch} (${b.group}, ${b.n} items): ${DIR}/${b.file}
The diagnoser's proposals are ${diagRef}.
Check every proposed fix with two lenses and default to skepticism ("accept" only what you checked):
DATA lens: (a) every fix_product exists in our data (title+url in catalogue_candidates, our_october, or the catalogue history) with the stated oct_regular; (b) the arithmetic: expected_price_after = 2-shop mean of regular prices in the official unit, expected_pct_after = price/official_sep − 1, within10_after consistent; (c) the diagnosis matches the evidence ("one_shop_only" only if the other shop really has an equivalent listing; "out_of_stock_online" only if statuses/notes show it).
METHOD/POLICY lens: (d) pinned/sampled products really match the official spec: same product type, same size or a clean unit conversion, brand when the official names one (else an explicit substitute_brand with user_decision), origin when the official names one, no premium/organic/value-pack variant unless the official is; (e) no cheapest-picking and no circular choice (a product chosen only because its price equals the official) → set calibration_only=true or reject; (f) policy: no bypass of blocks, no carried prices, no invented prices; (g) "ok" items left alone; (h) fix_type is the right category (fresh/loose → fixed_sample; missing brand → substitute_brand or other_source).
Return the FINAL entry for every code (all ${b.n}): copy the diagnoser's entry and apply your corrections in place (recomputed numbers, a better-matching listing from the candidates, corrected diagnosis/fix_type). Set verdict = accept (unchanged), modify (you changed fields), or reject (the fix is unusable: then set fix_type="rejected", within10_after=false, covered_after=false, and explain in verifier_notes). verifier_notes = one or two sentences on what you checked and changed.`
}

log(`Part: batches ${batches.map(b => b.batch).join(',')} (${batches.filter(b => b.diag_file).length} precomputed)`)
const results = await pipeline(
  batches,
  (b) => b.diag_file ? Promise.resolve({ file: `${DIR}/${b.diag_file}` }) : agent(diagnosePrompt(b), { label: `diagnose:${b.batch} ${b.group}`, phase: 'Diagnose', schema: DIAG_SCHEMA }),
  async (diag, b) => {
    if (!diag) return null
    const ref = diag.file ? `in the file ${diag.file} (read it)` : `(JSON):\n${JSON.stringify(diag.items)}`
    const v = await agent(verifyPrompt(b, ref), { label: `verify:${b.batch}`, phase: 'Verify', schema: FINAL_SCHEMA })
    if (!v) return null
    return v.items.map(it => ({ ...it, batch: b.batch, group: b.group }))
  },
)
return { items: results.filter(Boolean).flat() }
