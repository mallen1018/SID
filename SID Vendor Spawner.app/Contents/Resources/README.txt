SID Vendor Spawner — how it works
==================================

What this app does
------------------
- Clones the FBSPL vendor folder into a new folder named after the vendor.
- Rewrites every hard-coded "FBSPL" (title, <h1>, localStorage keys,
  bulletin/postings filenames) to the vendor's name.
- Rewrites the FBSPL OneDrive upload link to the vendor's link.
- Creates empty bulletin_<Vendor>.json and postings_<Vendor>.json at the
  repo root so the portal's bulletin fetch doesn't 404.
- Optionally runs git add / commit / push so the page deploys to sid.rocks.

Install modes
-------------
Download SID (default, current flow)
   Install button downloads the bundled SID.zip + shows the unzip /
   chrome://extensions / Load Unpacked modal. Same flow as the current
   FBSPL page.

Chrome Web Store
   Install button opens the SID listing on the Chrome Web Store
   (https://chromewebstore.google.com/detail/oaejdaekhegedlgoanfkogmoiceelkbc).
   The modal and Section 2 of the vendor guide are rewritten to a short
   "Add to Chrome" flow. SID.zip is not copied into the vendor folder.
   Use this mode once the pending extension update is published.

Where the app must live
-----------------------
The .app has to stay inside the SID repo folder (the one that has
FBSPL/ and the other vendor folders in it) so it can find FBSPL as
the template. Making a Finder alias on the Desktop is fine; moving the
.app itself out is not.

What it never changes
---------------------
It only touches the new vendor's folder + the two JSON stubs. Existing
vendors are never modified.

Rollback
--------
If a spawn goes wrong:
   cd /path/to/SID
   git reset --hard HEAD~1       # if you already pushed, use git revert instead
   rm -rf <VendorName>/
   rm -f bulletin_<VendorName>.json postings_<VendorName>.json
