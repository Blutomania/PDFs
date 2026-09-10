# icons/suspect/ — provenance

## The 15 SVGs (added playtest InterrogationSept8/ResultSept8)

Source: SVG Repo (svgrepo.com), pulled by the owner and handed over as a zip —
this sandbox's network policy blocks svgrepo.com directly, so these were never
fetched or license-checked from inside a session. SVG Repo's own claim is CC0
(public domain) per upload, checked at the page for each icon at the time it
was pulled. **That claim has not been independently re-verified from this
repo** — SVG Repo is an aggregator of many uploaders' work, not a single
rights-holder, so before this ships anywhere public, re-check each icon's own
license tag at its SVG Repo page one more time:

- businessman-person-2-svgrepo-com.svg
- detective-face-svgrepo-com.svg
- detective-svgrepo-com.svg
- dictator-svgrepo-com.svg
- evil-combatant-svgrepo-com.svg
- gentleman-person-svgrepo-com.svg
- m-i-b-svgrepo-com.svg
- male-person-2-svgrepo-com.svg
- male-student-1-svgrepo-com.svg
- masquerade-gentleman-svgrepo-com.svg
- mug-shot-svgrepo-com.svg
- person-silhouette-svgrepo-com.svg
- policeman-svgrepo-com.svg
- thief-svgrepo-com.svg
- woman-silhouette-svgrepo-com.svg

## What the owner's batch also contained, and was NOT added

The owner's zip held 22 SVG Repo files total. Seven were left out:

- **`stalin-svgrepo-com.svg`** — a caricature of a specific real historical
  figure (named as such in the filename itself). Excluded outright: these are
  meant to be anonymous, generic "suspect" placeholders, and a real person's
  likeness — especially this one — has no place standing in for a fictional
  murder suspect, independent of any copyright question.
- `female-toilet-svgrepo-com.svg` — a restroom pictogram, unrelated to this set.
- `high-school-girl-who-cut-her-bangs-too-short-5-svgrepo-com.svg`,
  `icon-for-people-who-love-money-dollar-edition-svgrepo-com.svg` — off-theme
  novelty icons, not generic figures.
- `female-lawyer-upper-body-svgrepo-com.svg`,
  `female-programmer-upper-body-svgrepo-com.svg`,
  `female-worker-upper-body-svgrepo-com.svg` — detailed 5-color illustrations,
  not flat silhouettes. Stylistically inconsistent with the rest of this set
  and everything else `Icons.gd` tints (a single `modulate` multiply only
  reads right on flat single-tone art), and closer to a specific portrait than
  an anonymous placeholder. Worth reconsidering as a *different* asset class
  later (real per-suspect portraits) rather than folded into this one.

**Worth flagging on its own:** excluding those three leaves this set skewed
toward masculine-presenting archetypes (businessman, gentleman, policeman,
thief, detective, ...) against one explicitly feminine-presenting silhouette
(`woman-silhouette`) and a few gender-neutral entries (`person-silhouette`,
`mug-shot`, `dictator`, `evil-combatant`). `Icons.gd`'s own picking rule never
correlates a specific icon to a specific suspect's identity — assignment is
seeded on name + game id, not on any trait of the character — but the set's
*composition* is still worth a second pass if a more balanced cast look
matters before this goes further than FPO.

## The gender-skew follow-up batch (18 files, not added except one)

The owner sent a second SVG Repo zip aimed at the skew flagged above. Of 18 files, only one was
added: `woman-svgrepo-com.svg`, a flat single-fill (`#000000`-equivalent, one `<style>` block)
full-body silhouette in the same visual language as the existing set. `woman-silhouette-svgrepo-com.svg`
in this batch is **byte-identical** to the file already in this folder — not a new asset, skipped.

**The other 16 were not added, on both the style ground this folder already applies and a license
ground this session's re-check turned up:**

- **Style:** each one carries `class="iconify iconify--twemoji"` and 4–12 distinct `fill="#..."`
  values — the same "detailed, multi-colour, closer to a portrait than an anonymous placeholder"
  shape that got the female-lawyer/programmer/worker trio excluded above, not the flat single-tone
  silhouette the rest of this set (and `Icons.gd`'s tint-by-modulate mechanism) is built around.
- **License (new finding, this is the re-check item 2 of the Sept-9 to-do asked for):** that
  `iconify--twemoji` class name is not cosmetic — these are Twemoji, Twitter/X's emoji artwork,
  which is licensed **CC-BY 4.0, not CC0**. CC-BY requires attribution; this whole set was pulled
  on the assumption (SVG Repo's own per-page tag) that everything here is CC0 and needs none. SVG
  Repo re-hosting a CC-BY work under its own CC0 badge does not change the original artist's
  actual terms. None of the 15 files in the first batch showed this marker — this is specific to
  the new batch. **Do not add any `iconify--twemoji`-tagged SVG Repo file to this set without
  either attributing Twemoji explicitly or getting a license the game can ship under.**

Excluded files (all Twemoji, all `-skin-tone` variants of the same handful of archetypes —
detective, astronaut, elf, fairy, farmer, mage, vampire, one wearing a turban, one in a veil, one a
zombie — plus one ungendered non-Twemoji `woman-dark-skin-tone` that turned out to carry the same
marker):

- woman-astronaut-light-skin-tone-svgrepo-com.svg
- woman-dark-skin-tone-svgrepo-com.svg
- woman-detective-light-skin-tone-svgrepo-com.svg
- woman-detective-medium-light-skin-tone-svgrepo-com.svg
- woman-detective-medium-skin-tone-svgrepo-com.svg
- woman-elf-medium-dark-skin-tone-svgrepo-com.svg
- woman-elf-medium-light-skin-tone-svgrepo-com.svg
- woman-fairy-light-skin-tone-svgrepo-com.svg
- woman-fairy-medium-light-skin-tone-svgrepo-com.svg
- woman-farmer-medium-skin-tone-svgrepo-com.svg
- woman-mage-medium-light-skin-tone-svgrepo-com.svg
- woman-mage-svgrepo-com.svg
- woman-svgrepo-com-2.svg
- woman-vampire-medium-light-skin-tone-svgrepo-com.svg
- woman-wearing-turban-light-skin-tone-svgrepo-com.svg
- woman-with-veil-svgrepo-com.svg
- woman-zombie-svgrepo-com.svg

**Net effect on the skew:** one more flat feminine-presenting silhouette (2 of 19 now), not the
larger rebalance the batch was hoping for. The skew this folder flagged is still real. Closing it
properly likely means sourcing flat, CC0-or-clearly-permissive, non-costumed body/portrait
silhouettes specifically — the same brief as the original set, filtered by gender presentation —
rather than an emoji character pack, which is a different asset class (see the "upper-body"
exclusions above) independent of its license.
