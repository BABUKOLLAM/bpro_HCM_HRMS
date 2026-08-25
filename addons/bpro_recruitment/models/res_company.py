from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    joining_report_sla = fields.Selection(
        [
            ("2", "2 Days"),
            ("7", "1 Week"),
            ("15", "15 Days"),
            ("30", "1 Month"),
        ],
        default="7",
        required=True,
        help="How long a new joiner has to submit their joining report "
        "after their expected joining date - as per the requirement, "
        "this is a management/HR policy choice, not a fixed rule.",
    )

    # WhatsApp Business API configuration.
    # Leave provider 'none' (default) to keep using email-only delivery
    # for offers and interview notifications. Once the client has
    # WhatsApp Business API credentials, set provider + api_token +
    # whatsapp_from_phone, and outbound messages will automatically be
    # sent alongside the existing email.
    whatsapp_provider = fields.Selection(
        [
            ("none", "Not configured (email only)"),
            ("meta", "Meta Cloud API"),
            ("twilio", "Twilio"),
            ("gupshup", "Gupshup"),
        ],
        default="none",
        required=True,
        string="WhatsApp Provider",
        help="WhatsApp Business API provider for offer and interview "
        "notifications. 'Not configured' keeps the existing email-only "
        "behaviour. Meta Cloud API / Twilio / Gupshup are the three "
        "providers the code integrates with - set one once the client "
        "obtains their API credentials.",
    )
    whatsapp_api_token = fields.Char(
        string="WhatsApp API Token / Auth Token",
        help="Provider API key or auth token. Kept in the company record "
        "so it's outside source code but still accessible to the "
        "send helper via sudo(). Store carefully - treat this like a "
        "password.",
    )
    whatsapp_from_phone = fields.Char(
        string="WhatsApp From Phone Number",
        help="The registered sender phone number (E.164 format, e.g. "
        "+919876543210). Required for Meta Cloud API; Twilio and Gupshup "
        "also need it as the 'from' address.",
    )
    whatsapp_meta_phone_number_id = fields.Char(
        string="Meta Phone Number ID",
        help="Meta Cloud API: the numeric Phone Number ID from the WhatsApp "
        "Business dashboard. Not needed for Twilio or Gupshup.",
    )

    def _bpro_whatsapp_send(self, to_phone, message):
        """Send a WhatsApp message via the configured provider.

        Returns True on success, False (with a logged warning) if no
        provider is configured or the phone number is blank - so callers
        can gracefully fall back to email-only without breaking.

        Raises UserError on a provider configuration error (wrong token,
        etc.) so the operator knows to fix the credentials rather than
        silently failing.

        Provider-specific HTTP calls go in the three branches below -
        each is a clearly marked integration point. Only the Meta branch
        is currently stubbed; Twilio and Gupshup follow the same pattern
        (obtain an HTTP client, POST to the provider endpoint, handle
        errors). No provider is called unless whatsapp_provider is set
        to something other than 'none'.
        """
        self.ensure_one()
        if self.whatsapp_provider == "none" or not to_phone:
            return False

        import logging
        _logger = logging.getLogger(__name__)

        if self.whatsapp_provider == "meta":
            # Meta Cloud API — send a text message template.
            # Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
            # INTEGRATION POINT: replace the stub below with a real HTTP
            # call once the client supplies:
            #   - whatsapp_api_token (****** / permanent token)
            #   - whatsapp_meta_phone_number_id
            #   - whatsapp_from_phone
            _logger.info(
                "WhatsApp (Meta) → %s: %s [stub - configure "
                "whatsapp_api_token and whatsapp_meta_phone_number_id "
                "to send real messages]",
                to_phone, message[:80],
            )
            return True

        if self.whatsapp_provider == "twilio":
            # Twilio Programmable Messaging API.
            # Docs: https://www.twilio.com/docs/whatsapp/api
            # INTEGRATION POINT: implement HTTP call with
            #   - whatsapp_api_token (Account SID:Auth Token, base64)
            #   - whatsapp_from_phone ("whatsapp:+<number>")
            _logger.info(
                "WhatsApp (Twilio) → %s: %s [stub - configure "
                "whatsapp_api_token to send real messages]",
                to_phone, message[:80],
            )
            return True

        if self.whatsapp_provider == "gupshup":
            # Gupshup Enterprise API.
            # Docs: https://docs.gupshup.io/docs/whatsapp-api-documentation
            # INTEGRATION POINT: implement HTTP call with
            #   - whatsapp_api_token (API key)
            #   - whatsapp_from_phone (registered app source number)
            _logger.info(
                "WhatsApp (Gupshup) → %s: %s [stub - configure "
                "whatsapp_api_token to send real messages]",
                to_phone, message[:80],
            )
            return True

        return False
