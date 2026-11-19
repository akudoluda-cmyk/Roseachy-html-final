# Roseachy Desk 2.18.3

Open `index.html` in a browser to run the standalone application. The deployment ZIP contains the same HTML. A static HTTPS server can also serve it. Keep the existing browser profile and application location when upgrading so Roseachy can access its IndexedDB records. Export a Full Backup first. Install the upgrade on all participating devices before exchanging new files.

Full Backup is available under **Settings → Data safety → External backup**. Button glint and press feedback follow the Effects and Motion settings.

## Daily use

Open **Smart Sync & Merge** in Settings or Market Desk. The header, buttons and active tab use the palette selected in Appearance.

- **Sync** sends signed updates and receives files for review. Return updates carry confirmations. Expand **Market Advances** to allocate or return cash, or **Stock Receipts** to record a pending delivery.
- **New Device** creates invitations and opens connection files. On each device, export and verify its own full backup in **Confirmation Details**. Exchange invitations and compare device codes. Approve the shared opening records on one device, choose **Save Connection File**, and open that file on the other device to review and confirm. Receive current updates before trading on a newly enrolled device.
- **History** shows recorded exchanges, approvals and errors. Expand **Activity details & recovery** for the underlying activities and recovery exports.

For Cloudflare Pages Direct Upload, use [the deployment ZIP](dist/Roseachy-Desk-2.18.3.zip). Its root contains the standalone HTML. Screenshots show the [updated mobile header](screenshots/mobile-header.png), [Sync on mobile](screenshots/mobile-sync.png), [New Device on tablet](screenshots/tablet-new-device.png), and [History on desktop](screenshots/desktop-history.png).

## Recovery and confidentiality

- For a damaged file, create a fresh export on the sender. For a missing activity, choose **All connected devices** on a peer that holds the earlier work and send that file first.
- A still-valid received file can be reopened through **Resume update review** or **Resume connection review**. A failed database commit can be retried after the reported storage issue is resolved.
- For competing records, review the differences and the underlying receipts. When two apparent payments represent one real payment, reverse the duplicate in the originating ledger and exchange the revised activities.
- An additional device with an independent trading history requires supervised reconciliation. Keep both verified backups. Restoring another store’s backup over active records would replace that store’s data.
- A replacement device needs a new verified connection. A changed signing key requires identity review. Keep recovery backups outside the device.
- Update files contain readable customer and business records. Use a private transfer channel. The private Financial Desk vault and signing secrets stay outside the update format.

[Implementation audit and test results](SMART-SYNC.md)
