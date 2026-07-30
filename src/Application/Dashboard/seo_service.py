class SEOService:
    """
    Dedicated Search Engine Optimization (SEO) Service.
    Generates dynamic search-friendly meta tags, JSON-LD schemas,
    and constructs sitemap.xml for multi-language indexing.
    """
    def __init__(self) -> None:
        pass

    def generate_meta_tags(self, title: str, description: str, language: str = "en") -> dict:
        """Returns standard metadata tags for HTML page rendering."""
        lang_locale = "fa_IR" if language == "fa" else "en_US"
        return {
            "title": f"{title} | TradeYar AI",
            "description": description,
            "og_locale": lang_locale,
            "og_title": f"{title} — Financial Intelligence",
            "og_description": description,
            "twitter_card": "summary_large_image",
            "robots": "index, follow"
        }

    def generate_json_ld_schema(self, url: str, title: str, description: str) -> str:
        """Compiles standard JSON-LD structured schema for search bots."""
        return f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FinancialService",
  "name": "TradeYar AI",
  "url": "{url}",
  "description": "{description}",
  "headline": "{title}",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "All"
}}
</script>"""

    def generate_sitemap_xml(self, base_url: str = "https://tradeyar.ai") -> str:
        """Dynamically compiles valid XML sitemap containing all public multilinguality pages."""
        # Multi-language URLs
        routes = [
            "", "/fa", "/en",
            "/dashboard", "/fa/dashboard", "/en/dashboard",
            "/terms", "/privacy", "/cookie-policy", "/disclaimer"
        ]

        xml_urls = []
        for r in routes:
            loc = f"{base_url}{r}"
            xml_urls.append(f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>")

        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml_content += "\n".join(xml_urls)
        xml_content += '\n</urlset>'
        return xml_content
