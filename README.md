# Roseachy Desk 2.18.0

Open `index.html` in a browser to run the standalone application. The deployment ZIP contains the same HTML. A static HTTPS server can also serve it. Keep the existing browser profile and application location when upgrading so Roseachy can access its IndexedDB records. Export a Full Backup first. Install the upgrade on all participating devices before exchanging new files.

## Daily use

Open **Smart Sync & Merge** in Settings or Market Desk. **Home** shows this device’s exchange activity. **Send** creates a signed update for a chosen recipient or all connected devices. **Receive** verifies a file, shows the changes, and lets an operator apply them. The next outgoing file carries confirmation information, including when there are zero new activities.

For a first connection, open **Devices → Connect another device** on both devices. Export and read back each device’s own full backup, exchange invitations, and compare the displayed codes with the other operator. Approve the shared opening records on one device. Send the resulting connection file to the other to review and confirm. Trading recorded after the initial two-device snapshots is replayed separately. A new device joining an established store should finish enrollment and receive the current updates before trading.

## Recovery and confidentiality

- For a damaged file, create a fresh export on the sender. For a missing activity, choose **All connected devices** on a peer that holds the earlier work and send that file first.
- A still-valid received file can be reopened through **Resume saved review**. A failed database commit can be retried after the reported storage issue is resolved.
- For competing records, review the differences and the underlying receipts. When two apparent payments represent one real payment, reverse the duplicate in the originating ledger and exchange the revised activities.
- An additional device with an independent trading history requires supervised reconciliation. Keep both verified backups. Restoring another store’s backup over active records would replace that store’s data.
- A replacement device needs a new verified connection. A changed signing key requires identity review. Keep recovery backups outside the device.
- Update files contain readable customer and business records. Use a private transfer channel. The private Financial Desk vault and signing secrets stay outside the update format.

[Implementation audit and test results](SMART-SYNC.md)
