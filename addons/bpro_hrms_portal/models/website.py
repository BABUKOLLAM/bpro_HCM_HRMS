from odoo import models

BRAND_NAME = "bpro HCM | HRMS"

# Top-nav items that come bundled with apps this suite depends on
# (website_sale, website_forum, website_slides) but don't belong on an
# HR product's public site - a live audit found them exposed on
# www.bprohrms.com's actual public nav (Shop, Forum, Courses),
# alongside Jobs (bpro_recruitment's real, wanted careers page) and
# Home/Contact us, which stay. Matched by name, not id - the ids are
# whatever sequence they happened to get on this particular install,
# not a stable identifier across a fresh install elsewhere.
UNWANTED_TOP_MENU_ITEMS = {"Shop", "Forum", "Courses"}

# Odoo's own demo social links, confirmed still live on production
# (facebook.com/Odoo, twitter.com/Odoo, linkedin.com/company/odoo) -
# nobody had ever replaced them, so visitors clicking any of them
# landed on Odoo's own accounts instead of bpro's. Cleared rather than
# guessed at real replacements - only bpro knows those.
SOCIAL_FIELDS = ["social_facebook", "social_twitter", "social_linkedin",
                  "social_youtube", "social_github", "social_instagram", "social_tiktok"]


class Website(models.Model):
    _inherit = "website"

    def _register_hook(self):
        super()._register_hook()
        # website.default_website ships with noupdate="1" (native Odoo
        # protects it from being reset by module upgrades), so a plain
        # XML data record can never update its name - confirmed the
        # hard way, it's silently skipped on both install and upgrade.
        # _register_hook runs on every registry load instead (install,
        # upgrade, and every server start), unaffected by noupdate,
        # which is what actually keeps this from drifting again.
        default_website = self.env.ref("website.default_website", raise_if_not_found=False)
        if default_website and default_website.name != BRAND_NAME:
            default_website.sudo().write({"name": BRAND_NAME})

        for website in self.sudo().search([]):
            stale = {f: False for f in SOCIAL_FIELDS if website[f]}
            if stale:
                website.write(stale)

            root = self.env["website.menu"].sudo().search(
                [("website_id", "=", website.id), ("parent_id", "=", False)], limit=1
            )
            if root:
                root.child_id.filtered(
                    lambda m: m.name in UNWANTED_TOP_MENU_ITEMS
                ).unlink()

        # res.company has its own, separate set of social_* fields
        # (used outside the website context) - confirmed both company
        # and website carried the exact same stale Odoo defaults, so
        # both need clearing, not just the website-facing one.
        company_social_fields = [f for f in SOCIAL_FIELDS if f in self.env["res.company"]._fields]
        for company in self.env["res.company"].sudo().search([]):
            stale = {f: False for f in company_social_fields if company[f]}
            if stale:
                company.write(stale)

        # The "Powered by Odoo" badge in the footer's bottom bar comes
        # from two different templates depending on which optional
        # apps are installed - deactivating only website_sale's
        # eCommerce-flavored one (confirmed live) revealed a second,
        # always-present one from the core website module underneath
        # ("Create a free website"), not tied to any optional app.
        # Both need deactivating for the badge to actually disappear.
        for xmlid in ["website_sale.brand_promotion", "website.brand_promotion"]:
            brand_promo = self.env.ref(xmlid, raise_if_not_found=False)
            if brand_promo and brand_promo.active:
                brand_promo.sudo().write({"active": False})
