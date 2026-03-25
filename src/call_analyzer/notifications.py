import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from call_analyzer.config import settings
from call_analyzer.models import AnalysisResult, Call

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


async def send_fraud_alert(call: Call, result: AnalysisResult) -> None:
    if not settings.smtp_password:
        logger.error("SMTP not configured (smtp_password is empty), cannot send fraud alert for %s", call.filename)
        return

    to_addr = settings.alert_email_to or settings.smtp_user

    categories = ", ".join(result.fraud_categories) if result.fraud_categories else "N/A"
    reasons_text = "\n".join(f"  - {r}" for r in result.reasons) if result.reasons else "  N/A"
    reasons_html = "".join(f"<li>{r}</li>" for r in result.reasons) if result.reasons else "<li>N/A</li>"
    transcript = result.transcript or "N/A"

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_user
    msg["To"] = to_addr
    msg["Subject"] = f"Fraud detected: {call.filename}"

    text_body = (
        f"Fraud detected in call: {call.filename}\n"
        f"\n"
        f"Score: {result.fraud_score:.2f}\n"
        f"Categories: {categories}\n"
        f"\n"
        f"Reasons:\n{reasons_text}\n"
        f"\n"
        f"Transcript:\n{transcript}\n"
    )

    html_body = f"""\
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
  <h2 style="color: #dc2626;">Fraud Detected</h2>
  <table style="border-collapse: collapse; margin-bottom: 16px;">
    <tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">File</td><td>{call.filename}</td></tr>
    <tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Score</td><td style="color: #dc2626; font-size: 1.2em;">{result.fraud_score:.0%}</td></tr>
    <tr><td style="padding: 4px 12px 4px 0; font-weight: bold;">Categories</td><td>{categories}</td></tr>
  </table>
  <h3>Reasons</h3>
  <ul>{reasons_html}</ul>
  <h3>Transcript</h3>
  <pre style="background: #f3f4f6; padding: 12px; border-radius: 6px; white-space: pre-wrap;">{transcript}</pre>
</body>
</html>"""

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    for attempt in range(MAX_RETRIES):
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                start_tls=True,
                username=settings.smtp_user,
                password=settings.smtp_password,
            )
            logger.info("Fraud alert email sent for call %s", call.filename)
            return
        except Exception:
            if attempt < MAX_RETRIES - 1:
                logger.warning("Email send attempt %d failed, retrying...", attempt + 1)
                await asyncio.sleep(1)
            else:
                raise
