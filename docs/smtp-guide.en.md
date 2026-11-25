# How to get an SMTP app password

When SubDeck sends reminder emails, it asks for an "app password", not your mailbox login password. This is a separate passcode the mail provider issues for third-party apps. It can only send and receive mail; it cannot sign in to the web mailbox. The benefit: even if this string leaks, nobody can get into your mailbox with it.

Below are step-by-step instructions for each mail provider, plus how to enter the result into SubDeck. Pick the section for the mailbox you actually use.

## QQ Mail

For @qq.com and @foxmail.com addresses.

### Step 1: enable the service and generate the app password

1. Open mail.qq.com in a desktop browser and sign in to your QQ mailbox.
2. Click "Settings" at the top of the page.
3. Click "Account and Security".
4. Scroll down to the section labeled "POP3/IMAP/SMTP/Exchange/CardDAV Services".
5. Click "Enable" next to "IMAP/SMTP Service".
6. Follow the on-page prompt and send a text message from your bound phone number to verify it is you.
7. Once verified, the page shows a 16-character app password.
8. Copy it right away into a note or password manager.

### Step 2: enter it in SubDeck

Open SubDeck, go to "Settings", find "Email reminders", and fill in:

| Field | Value |
| --- | --- |
| SMTP server | smtp.qq.com |
| Port | 465 |
| SSL | Checked |
| Sender email (SMTP username) | Your full QQ address, e.g. 123456789@qq.com |
| SMTP app password | The 16-character code from step 1 |

Click "Send test email". Once it arrives, click "Save reminder settings".

### Notes

- The app password is shown only once. Copy it before leaving the page.
- To review or revoke it later: go back to "Account and Security", open "Device Management", then "App Password Management". You can disable or reset it. A reset invalidates the old code immediately, so update SubDeck with the new one.
- Changing your QQ password invalidates every app password. Sending from SubDeck will fail; go back to step 1 and generate a new one.
- QQ Mail allows roughly 500 messages per day, far more than reminders need.

## 163 / 126 Mail

For @163.com and @126.com addresses. Both follow the same procedure.

### Step 1: enable the service and generate the app password

1. Open mail.163.com in a desktop browser (mail.126.com for 126) and sign in.
2. Click "Settings" at the top of the page.
3. Click "POP3/SMTP/IMAP".
4. Find "SMTP Service" and enable it.
5. Follow the prompt and send a text message from your bound phone number.
6. Once verified, the page shows a "client authorization password". This is the app password.
7. Copy it right away.

### Step 2: enter it in SubDeck

Open SubDeck, go to "Settings", find "Email reminders", and fill in:

| Field | Value |
| --- | --- |
| SMTP server | smtp.163.com (smtp.126.com for 126) |
| Port | 465 |
| SSL | Checked |
| Sender email (SMTP username) | Your full email address |
| SMTP app password | The client authorization password from step 1 |

Click "Send test email". Once it arrives, click "Save reminder settings".

### Notes

- Newly registered accounts may not be able to enable SMTP yet. Some need a bound phone number first; some need to wait a period. Follow the on-page prompt.
- Changing the mailbox password invalidates the app password. Go back to step 1 and generate a new one.
- The app password is shown only once. Copy it before leaving the page.

## Gmail

For @gmail.com addresses.

### Step 1: turn on 2-Step Verification and generate an app password

1. Open myaccount.google.com in a browser and sign in to your Google account.
2. Click "Security" in the left menu.
3. Make sure "2-Step Verification" is on. Turn it on if it is not; the next step's entry point will not appear otherwise.
4. Type app password into the search box at the top and open "App passwords".
5. Enter a name you will recognize, such as SubDeck.
6. Click "Create". The page shows a 16-character password.
7. Copy it right away.

### Step 2: enter it in SubDeck

Open SubDeck, go to "Settings", find "Email reminders", and fill in:

| Field | Value |
| --- | --- |
| SMTP server | smtp.gmail.com |
| Port | 465 |
| SSL | Checked |
| Sender email (SMTP username) | Your full Gmail address |
| SMTP app password | The 16-character app password from step 1 |

Click "Send test email". Once it arrives, click "Save reminder settings".

### Notes

- 2-Step Verification must be on first; otherwise the "App passwords" entry does not appear.
- If the 16-character password contains spaces, paste it as is. Do not remove them.
- Changing your Google password revokes all app passwords. Sending from SubDeck will fail; go back to step 1 and generate a new one.
- Gmail allows roughly 500 messages per day, far more than reminders need.

## iCloud Mail

For @icloud.com, @me.com and @mac.com addresses.

### Step 1: generate an app-specific password

1. Open account.apple.com in a browser and sign in with your Apple Account.
2. Click "Sign-In and Security".
3. Click "App-Specific Passwords".
4. Click "+", enter a label you will recognize such as SubDeck.
5. Click "Done". The page shows a password.
6. Copy it right away. It contains hyphens, in the form xxxx-xxxx-xxxx-xxxx. **Copy the hyphens too; the whole string is 16 letters.**

### Step 2: enter it in SubDeck

Open SubDeck, go to "Settings", find "Email reminders", and fill in the following. **This provider differs from the others. Read carefully.**

| Field | Value |
| --- | --- |
| SMTP server | **smtp.mail.me.com** (not icloud.com) |
| Port | **587** (not 465) |
| SSL | **Unchecked** (off) |
| Sender email (SMTP username) | Your full iCloud address |
| SMTP app password | The app-specific password from step 1, hyphens included |

Click "Send test email". Once it arrives, click "Save reminder settings".

### Notes

- Two-factor authentication must be on for your Apple Account. Most people already have it; if not, turn it on under "Sign-In and Security" first.
- Server, port and SSL are different from the other providers. Follow the table above, not the QQ section.
- Changing your Apple Account password invalidates every app-specific password. Go back to step 1 and generate a new one.

## Outlook Mail (no longer available on some accounts)

For @outlook.com, @hotmail.com, @live.com and @msn.com addresses.

### Step 1: generate an app password

1. Open account.microsoft.com in a browser and sign in to your Microsoft account.
2. Click "Security".
3. Find "Advanced security options" and open it.
4. Make sure two-step verification is on. Turn it on if it is not.
5. Scroll to "App passwords" and click "Create a new app password".
6. The page shows a password. Copy it right away.

### Step 2: enter it in SubDeck

Open SubDeck, go to "Settings", find "Email reminders", and fill in:

| Field | Value |
| --- | --- |
| SMTP server | smtp-mail.outlook.com |
| Port | 587 |
| SSL | **Unchecked** (off) |
| Sender email (SMTP username) | Your full Outlook address |
| SMTP app password | The app password from step 1 |

Click "Send test email". Once it arrives, click "Save reminder settings".

### Notes

- **Microsoft is gradually retiring "sign in to SMTP with an app password". Your account may already be unable to send mail this way.** If the test send fails with an error such as authentication unsuccessful, this is why.
- This is a change to Microsoft's account security policy and is not related to SubDeck. There is no setting in SubDeck that can work around it.
- If this happens, switch to one of the providers above (QQ, 163, Gmail) for reminder emails.

## FAQ

**The app password looks wrong when pasted, or the test send fails**

Check for spaces before or after the pasted code. Selecting one extra space makes the provider reject it as a wrong password. Copy again and select only the code itself.

**SubDeck stopped sending after I changed my mailbox password**

Every provider works the same way: changing the login password invalidates the app password. Go back to the section for your provider, generate a new one, and enter it in SubDeck.

**It says sent, but nothing arrived**

Check the spam, promotions and subscriptions folders first. Reminder emails often land there. Mark one as "not spam" and the rest will go to the inbox.

**Test send fails and the app password is definitely correct**

Compare the "Step 2" table for your provider line by line, especially three items: SMTP server, port, and the SSL switch. iCloud and Outlook are the easiest to get wrong. They use port 587 with SSL off, the opposite of QQ, 163 and Gmail (465 with SSL on).

**Can the sender and recipient be different addresses?**

Yes. Fill the sender with whichever account you generated the app password for, and use that account's app password. Recipients can be anything; separate multiple addresses with commas.

**How soon will I get a reminder after setting this up?**

Once enabled, SubDeck checks once a day at the time you set and sends one digest email covering subscriptions due in the coming days. To verify the configuration right away, use "Send test email" instead of waiting for the scheduled time.
