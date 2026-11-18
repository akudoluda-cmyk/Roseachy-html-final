# Smart Sync audit and validation

The supplied standalone HTML is preserved in Git commit `49f88a5`. The upgraded source is `index.html`. Both run on the existing Roseachy store and use its business transaction functions.

## What the audit found

| Area | Finding and implementation |
|---|---|
| Identity and trust | The original persists a device ID and P-256 key and pins the peer key after fingerprint review. The upgrade serializes first-use key generation and verifies the proposed opening proof, cut, and receiving key. A higher membership version previously could overwrite existing members’ starting positions during routine import. Enrollment extensions now preserve those entries. |
| Event capture | The existing storage commit observer journals stock movements, changes to shared records, and dependencies alongside business writes. A device ID and monotonic sequence identify each event. Imported events retain their origin and signature when forwarded. Conflicting copies of the same ID block the import. Confirmation digests cover the opening checkpoint, canonical activity contents and shared decisions. Randomized signatures are excluded from content equality. |
| First exchange | Both peers previously needed separate evidence of enrollment before exporting routine updates. Connected peers can now exchange an update immediately. Starting a third device from an independent nonempty store stops for reconciliation. A verified new installation can join through a signed invitation and connection file. |
| Storage and recovery | IndexedDB commits the derived stock, ledger, supplier records, events and sync metadata together. The storage layer also has a journal-based localStorage fallback. Duplicate-only imports can record receipt without rewriting the business projection. Reviewed changes are rechecked for intervening writes. Successful commits clear the resumable file. |
| Inventory | Stock starts from verified quantities and replays movements and final transaction revisions. Deficits retain a signed balance while available stock stops at zero. The upgrade retains batch allocation IDs on new records, distinguishes concurrent from causal counts, and handles catalogue removals and independent product field edits. |
| Operational accounts | Cash, POS, customer debt and supplier positions use opening amounts and identified ledger transactions. Payments remain linked to customer or supplier records. Supplier-payment and accounting-record checks run before commit. Similar independently recorded payments with matching account, date, method and amount require receipt review. |
| Conflicts | Replaying events in dependency order compares before and after values. Operators choose disputed values and explicitly verify absolute counts. Prior decisions travel in updates. Competing decisions return to review. The event log retains the underlying activity. |
| Private records | The existing shareable-field allowlist excludes the local bank vault. The business’s designated bank verification authority and cash custody rules continue to apply. Connector membership gives every device access to normal sales, purchases, inventory and credit workflows. |
| Operator workflow | The original exposed routine operations, pairing, recovery, confirmations and diagnostic history together. The four views now guide transfers, display receive and commit outcomes separately, and show the actual error on failure. Exchange history retains the latest 50 entries; the business event journal is separate. |

## Executed checks

`python tests/smart_sync.py` runs the integration suite in Chromium with Python Playwright. Run it from a Git checkout that contains the original upload commit. The harness serves the application to independent browser contexts, checks IndexedDB mode, and exposes fixture builders only in the test response. Fixture transactions use the application’s inventory and ledger save paths. The supplier payment, exchange-file and mobile pairing checks exercise form controls.

| Requested scenario | Expected | Observed |
|---|---|---|
| 1. Initial pairing | Independently verify a common opening position | Two seeded devices accepted one checkpoint. A separate 390 px pairing run completed with downloaded recovery files, invitations, fingerprint checks and the returned connection file. |
| 2. Offline sales | Count each device’s sale once | The 15-unit and 10-unit cash sales produced ₦250 retail cash on both devices. |
| 3. Sales and receipt | Reconcile movements from 100 units | Both devices held 105 after the two sales and a 30-unit externally funded purchase. |
| 4. Repeated import | No duplicate transactions | Replay reported zero new activities. Replaying a supplier payment kept one accounting row. |
| 5. Three devices | Relay signed events without direct routine exchanges | B forwarded A’s history to C. C sold two units and B relayed the sale back to A. All three held 103 units. |
| 6. Product conflict | Require a decision, propagate it | Independent prices of 21 and 33 blocked merge until reviewed. Both devices then displayed the same approved price. |
| 7. Concurrent credit | Preserve a sale and an independent repayment | Both balances equalled 50 opening credit plus the sale price less the 20 repayment. Two further equal payments required explicit confirmation that both receipts were genuine. |
| 8. Supplier payment | Keep purchase, payment and liability linked | The payment form reduced a 100 credit invoice to 75 on both devices. A repeat import preserved that balance. |
| 9. Oversale | Retain sales and identify the deficit | Concurrent 70-unit sales against 102 units produced a balance of −38 and a 38-unit shortage on both devices. |
| 10. Interrupted import | Commit all stores or roll back | Injected IndexedDB aborts on both storage write attempts preserved stock, transactions and the event frontier. Reload confirmed rollback. Retry succeeded. |
| 11. Missing dependency | Refuse a later signed event until its predecessor arrives | An isolated later event was refused. A complete file restored progress and all devices reached price 38. |
| 12. Repeated exchanges | Exchange activities and confirmations repeatedly | Three devices reached identical known-event digests. A return cycle applied zero new activities and recorded that digest as each recipient’s confirmed exchange. The file picker, review, Apply and return download also succeeded. |
| 13. Refresh | Retain identity and progress | Device IDs and known-event digests survived reload in independent contexts. |
| 14. Upgrade | Preserve an existing paired installation | Two profiles ran the actual original HTML, paired and recorded a sale before upgrading in place. The IDs and checkpoint survived and both devices accounted for the sale. |
| 15. Authenticity | Reject altered or unauthorized updates | Changing a signed field failed authentication. A fresh, unconnected profile rejected the original signed update. |

The suite also verified that adding a nonempty independent third store stopped without changing its 100 units of stock.

## Scope and remaining limits

Testing covered Chromium with isolated databases and synthetic store records. Native Android file-sharing bridges, Safari, Firefox, localStorage fallback, physical device power loss and long-running production volumes have not been exercised. The receipt test used the application’s externally funded purchase path. The supplier test combined a Market Desk credit-purchase fixture with the actual payment form.

The existing 32 MiB file limit applies to the exchange. Recipient-specific exports can reduce file size. Activity chunking is unavailable if a recipient’s missing history alone exceeds the limit. Devices that independently extend membership while disconnected may need to exchange and approve enrollment files before exchanging transactions. An existing business with incompatible opening data needs an operator-led reconciliation.

Legacy signed activities retain their original contents. Batch identifiers omitted by the old exporter cannot be recovered from those exports alone. Full Backup and private bank recovery retain their existing application workflows.

The deployment ZIP passed its archive integrity check and contained a byte-identical copy of the tested source. The extracted HTML started from a local static HTTP server with external requests blocked and saved a device-name change after Chromium’s network was disconnected. The managed browser blocked direct file-URL navigation, so double-click launch in that browser remains unverified.
