"""Email sending infrastructure for outreach delivery."""

from __future__ import annotations

import logging
from typing import Any

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender:
    """
    Email sending service supporting multiple providers.
    
    Supports:
    - SendGrid (recommended for MVP)
    - AWS SES (cost-effective, scalable)
    - SMTP (simple, but limited tracking)
    """

    def __init__(self, *, provider: str | None = None):
        """
        Initialize email sender.

        Args:
            provider: Email provider ("sendgrid", "ses", "smtp"). Defaults to config.
        """
        settings = get_settings()
        self.provider = provider or settings.email_provider or "smtp"
        self.settings = settings

    async def send_outreach_email(
        self,
        *,
        lead_id: str,
        to_email: str,
        to_name: str | None = None,
        subject: str,
        body: str,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Send outreach email.

        Args:
            lead_id: Lead ID for tracking
            to_email: Recipient email address
            to_name: Recipient name (optional)
            subject: Email subject line
            body: Email body (can be HTML or plain text)
            from_email: Sender email (defaults to config)
            from_name: Sender name (defaults to config)

        Returns:
            Dictionary with send status and email_id if available
        """
        from_email = from_email or self.settings.email_from_address or "noreply@aoro.ai"
        from_name = from_name or self.settings.email_from_name or "AORO"

        if self.settings.email_send_dry_run:
            logger.info(
                "Dry-run email send for lead %s (provider=%s, to=%s)",
                lead_id,
                self.provider,
                to_email,
            )
            return {
                "status": "sent",
                "provider": "dry-run",
                "email_id": f"dry-run-{lead_id}",
            }

        if self.provider == "sendgrid":
            return await self._send_via_sendgrid(
                lead_id=lead_id,
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                body=body,
                from_email=from_email,
                from_name=from_name,
            )
        elif self.provider == "ses":
            return await self._send_via_ses(
                lead_id=lead_id,
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                body=body,
                from_email=from_email,
                from_name=from_name,
            )
        else:
            return await self._send_via_smtp(
                lead_id=lead_id,
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                body=body,
                from_email=from_email,
                from_name=from_name,
            )

    async def _send_via_sendgrid(
        self,
        *,
        lead_id: str,
        to_email: str,
        to_name: str | None,
        subject: str,
        body: str,
        from_email: str,
        from_name: str,
    ) -> dict[str, Any]:
        """Send email via SendGrid API."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import ClickTracking, Mail, OpenTracking, TrackingSettings

            if not self.settings.sendgrid_api_key:
                raise ValueError("SENDGRID_API_KEY not configured")

            sg = sendgrid.SendGridAPIClient(api_key=self.settings.sendgrid_api_key)

            message = Mail(
                from_email=(from_email, from_name),
                to_emails=(to_email, to_name or ""),
                subject=subject,
                html_content=body,
            )

            # Add tracking
            message.tracking_settings = TrackingSettings(
                click_tracking=ClickTracking(enable=True, enable_text=True),
                open_tracking=OpenTracking(enable=True),
            )

            response = sg.send(message)

            logger.info(f"Email sent via SendGrid for lead {lead_id}: {response.status_code}")

            return {
                "status": "sent",
                "provider": "sendgrid",
                "email_id": response.headers.get("X-Message-Id"),
                "status_code": response.status_code,
            }
        except ImportError:
            logger.error("sendgrid package not installed. Install with: pip install sendgrid")
            raise
        except Exception as e:
            logger.error(f"Error sending email via SendGrid: {e}", exc_info=True)
            return {
                "status": "error",
                "provider": "sendgrid",
                "error": str(e),
            }

    async def _send_via_ses(
        self,
        *,
        lead_id: str,
        to_email: str,
        to_name: str | None,
        subject: str,
        body: str,
        from_email: str,
        from_name: str,
    ) -> dict[str, Any]:
        """Send email via AWS SES."""
        try:
            import boto3
            from botocore.exceptions import ClientError

            if not self.settings.aws_ses_region:
                raise ValueError("AWS_SES_REGION not configured")

            ses_client = boto3.client("ses", region_name=self.settings.aws_ses_region)

            response = ses_client.send_email(
                Source=f"{from_name} <{from_email}>",
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": body, "Charset": "UTF-8"}},
                },
            )

            message_id = response.get("MessageId")

            logger.info(f"Email sent via AWS SES for lead {lead_id}: {message_id}")

            return {
                "status": "sent",
                "provider": "ses",
                "email_id": message_id,
            }
        except ImportError:
            logger.error("boto3 package not installed. Install with: pip install boto3")
            raise
        except ClientError as e:
            logger.error(f"Error sending email via AWS SES: {e}", exc_info=True)
            return {
                "status": "error",
                "provider": "ses",
                "error": str(e),
            }

    async def _send_via_smtp(
        self,
        *,
        lead_id: str,
        to_email: str,
        to_name: str | None,
        subject: str,
        body: str,
        from_email: str,
        from_name: str,
    ) -> dict[str, Any]:
        """Send email via SMTP."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            smtp_host = self.settings.smtp_host or "localhost"
            smtp_port = self.settings.smtp_port or 587
            smtp_user = self.settings.smtp_user
            smtp_password = self.settings.smtp_password

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email

            # Add HTML body
            html_part = MIMEText(body, "html")
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent via SMTP for lead {lead_id}")

            return {
                "status": "sent",
                "provider": "smtp",
                "email_id": None,  # SMTP doesn't provide message IDs
            }
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}", exc_info=True)
            return {
                "status": "error",
                "provider": "smtp",
                "error": str(e),
            }
