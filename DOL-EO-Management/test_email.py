from src.email.godaddy_client import GoDaddyEmailClient

client = GoDaddyEmailClient()
client.connect()

emails = client.fetch_unread_emails()
print(f"Fetched {len(emails)} unread emails")
for msg in emails:
    print(f"From: {msg['From']}, Subject: {msg['Subject']}")

client.send_email(
    to="your-email@example.com",
    subject="Test from GoDaddy client",
    body="This is a test email from your email integration system."
)

client.close()
