## Change train: TODO <goal in one sentence>

**Why:** TODO the need, and the issue it came from.

**Contract:** TODO `contracts_version` x.y → x.(y+1) (additive) | MAJOR (needs a maintainer decision) | unchanged.

## Steps (merge in this order; each must leave everything green)

- [ ] 1. builder: TODO schema / example / CONVENTIONS / renderer / tests. PR: TODO
- [ ] 2. hub: TODO models / responses / fixtures. Red until step 1 merges (installs builder@main). PR: TODO
- [ ] 3. site: TODO image page / hub.ts / lab. PR: TODO
- [ ] 4. control: TODO (or "not needed"). PR: TODO
- [ ] 5. first image using it: TODO. PR: TODO

## Verify the end state

TODO: the API response, the site page and the image that show it.

## Rollback

TODO: what to revert, in which order, and whether any step is irreversible (v1 API fields, store ids, published tags).

<!-- harness
intent: contract-change
harness: {{version}}
-->
