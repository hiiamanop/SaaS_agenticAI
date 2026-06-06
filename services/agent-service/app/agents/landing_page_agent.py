"""Landing Page Agent.

Generates HTML/CSS landing pages with embedded lead-capture contact forms
and conversion tracking scripts. Publishes deployment events when ready.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.events import publish

logger = logging.getLogger(__name__)

_CSS_BASE = """
/* Landing Page Base Styles */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
       color: #1a202c; background: #f7fafc; }
.hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff; padding: 80px 24px; text-align: center; }
.hero h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 16px; }
.hero p  { font-size: 1.2rem; opacity: .9; max-width: 640px; margin: 0 auto 32px; }
.cta-btn { display: inline-block; background: #fff; color: #764ba2;
           font-weight: 700; padding: 16px 40px; border-radius: 8px;
           text-decoration: none; font-size: 1.1rem; transition: transform .2s; }
.cta-btn:hover { transform: translateY(-2px); }
.benefits { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 24px; padding: 64px 24px; max-width: 1100px; margin: 0 auto; }
.benefit-card { background: #fff; border-radius: 12px; padding: 32px 24px;
                box-shadow: 0 4px 24px rgba(0,0,0,.07); }
.benefit-card h3 { font-size: 1.15rem; margin-bottom: 10px; color: #667eea; }
.contact-section { background: #fff; padding: 64px 24px; text-align: center; }
.contact-section h2 { font-size: 2rem; margin-bottom: 32px; }
.contact-form { max-width: 560px; margin: 0 auto; text-align: left; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-weight: 600; margin-bottom: 6px; }
.form-group input, .form-group select, .form-group textarea {
    width: 100%; padding: 12px 16px; border: 2px solid #e2e8f0;
    border-radius: 8px; font-size: 1rem; transition: border-color .2s; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
    outline: none; border-color: #667eea; }
.submit-btn { width: 100%; background: linear-gradient(135deg, #667eea, #764ba2);
              color: #fff; border: none; padding: 16px; border-radius: 8px;
              font-size: 1.1rem; font-weight: 700; cursor: pointer;
              transition: opacity .2s; }
.submit-btn:hover { opacity: .9; }
footer { text-align: center; padding: 32px 24px; color: #718096; font-size: .9rem; }
"""


class LandingPageAgent:
    """HTML/CSS landing page generator with embedded contact forms."""

    def __init__(self, tenant_id: uuid.UUID, base_url: str = "https://app.meetsin.id") -> None:
        self.tenant_id = tenant_id
        self.base_url = base_url

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate_page(
        self,
        campaign_id: str,
        headline: str,
        subheadline: str,
        value_proposition: str,
        benefits: list[str],
        cta_text: str = "Get Free Demo",
        brand_color: str = "#667eea",
    ) -> dict[str, Any]:
        """Generate a complete landing page HTML document.

        Returns a dict with:
        - campaign_id
        - html (str)          — full HTML document
        - css (str)           — extracted stylesheet
        - form_fields (list)  — field definitions for the embedded form
        - page_url (str)      — deployment URL (slug-based)
        - status: "generated"
        """
        logger.info(
            "LandingPageAgent.generate_page tenant=%s campaign=%s",
            self.tenant_id,
            campaign_id,
        )

        form_fields = self._default_form_fields()
        form_html = self._build_form_html(form_fields=form_fields, campaign_id=campaign_id)
        benefits_html = self._build_benefits_html(benefits)

        html = self._build_html(
            headline=headline,
            subheadline=subheadline,
            cta_text=cta_text,
            benefits_html=benefits_html,
            form_html=form_html,
            campaign_id=campaign_id,
            brand_color=brand_color,
        )

        slug = campaign_id.lower().replace(" ", "-")
        page_url = f"{self.base_url}/lp/{slug}"

        page: dict[str, Any] = {
            "campaign_id": campaign_id,
            "html": html,
            "css": _CSS_BASE,
            "form_fields": form_fields,
            "page_url": page_url,
            "status": "generated",
        }

        await publish(
            "marketing.landing_page.generated",
            "marketing.landing_page.generated",
            str(self.tenant_id),
            {
                "tenant_id": str(self.tenant_id),
                "campaign_id": campaign_id,
                "page_url": page_url,
            },
        )
        return page

    async def generate_contact_form(
        self,
        campaign_id: str,
        fields: list[dict[str, Any]] | None = None,
        submit_endpoint: str = "/api/leads",
    ) -> dict[str, Any]:
        """Generate a standalone contact form component.

        Returns a dict with:
        - campaign_id
        - form_html (str)
        - fields (list)
        - submit_endpoint (str)
        """
        form_fields = fields or self._default_form_fields()
        form_html = self._build_form_html(
            form_fields=form_fields,
            campaign_id=campaign_id,
            action=submit_endpoint,
        )
        return {
            "campaign_id": campaign_id,
            "form_html": form_html,
            "fields": form_fields,
            "submit_endpoint": submit_endpoint,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_form_fields() -> list[dict[str, Any]]:
        return [
            {"name": "full_name", "label": "Full Name", "type": "text", "required": True},
            {"name": "email", "label": "Work Email", "type": "email", "required": True},
            {"name": "phone", "label": "WhatsApp Number", "type": "tel", "required": True},
            {"name": "company", "label": "Company Name", "type": "text", "required": True},
            {"name": "employees", "label": "Number of Employees", "type": "select",
             "options": ["1-10", "11-50", "51-200", "200+"], "required": False},
            {"name": "message", "label": "What challenge are you facing?",
             "type": "textarea", "required": False},
        ]

    @staticmethod
    def _build_form_html(
        form_fields: list[dict[str, Any]],
        campaign_id: str,
        action: str = "/api/leads",
    ) -> str:
        field_html_parts: list[str] = []
        for field in form_fields:
            ftype = field["type"]
            fname = field["name"]
            flabel = field["label"]
            req = "required" if field.get("required") else ""

            if ftype == "select":
                opts = "".join(
                    f'<option value="{o}">{o}</option>'
                    for o in field.get("options", [])
                )
                input_tag = f'<select name="{fname}" id="{fname}" {req}><option value="">Select…</option>{opts}</select>'
            elif ftype == "textarea":
                input_tag = f'<textarea name="{fname}" id="{fname}" rows="4" {req}></textarea>'
            else:
                input_tag = f'<input type="{ftype}" name="{fname}" id="{fname}" {req} />'

            field_html_parts.append(
                f'<div class="form-group">'
                f'<label for="{fname}">{flabel}</label>'
                f'{input_tag}'
                f'</div>'
            )

        fields_html = "\n".join(field_html_parts)
        return (
            f'<form class="contact-form" method="POST" action="{action}" '
            f'data-campaign-id="{campaign_id}">\n'
            f'{fields_html}\n'
            f'<input type="hidden" name="campaign_id" value="{campaign_id}" />\n'
            f'<button type="submit" class="submit-btn">Get Free Demo</button>\n'
            f'</form>'
        )

    @staticmethod
    def _build_benefits_html(benefits: list[str]) -> str:
        cards = "".join(
            f'<div class="benefit-card"><h3>✓ {b}</h3>'
            f'<p>Streamline your operations and reduce costs with our proven solution.</p></div>'
            for b in benefits
        )
        return f'<div class="benefits">{cards}</div>'

    @staticmethod
    def _build_html(
        headline: str,
        subheadline: str,
        cta_text: str,
        benefits_html: str,
        form_html: str,
        campaign_id: str,
        brand_color: str,
    ) -> str:
        return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{headline}</title>
  <style>{_CSS_BASE}
  .hero {{ background: linear-gradient(135deg, {brand_color} 0%, #764ba2 100%); }}
  .benefit-card h3 {{ color: {brand_color}; }}
  .cta-btn {{ color: {brand_color}; }}
  .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{ border-color: {brand_color}; }}
  .submit-btn {{ background: linear-gradient(135deg, {brand_color}, #764ba2); }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>{headline}</h1>
    <p>{subheadline}</p>
    <a href="#contact" class="cta-btn">{cta_text}</a>
  </section>

  {benefits_html}

  <section class="contact-section" id="contact">
    <h2>Get Your Free Demo</h2>
    {form_html}
  </section>

  <footer>
    <p>&copy; 2026 Meetsin.Id — All rights reserved.</p>
  </footer>

  <script>
    // Conversion tracking
    document.querySelector('[data-campaign-id]').addEventListener('submit', function(e) {{
      e.preventDefault();
      const data = Object.fromEntries(new FormData(this));
      fetch(this.action, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(data),
      }}).then(r => r.json()).then(d => {{
        window.location.href = '/thank-you?campaign={campaign_id}';
      }});
    }});
  </script>
</body>
</html>"""
