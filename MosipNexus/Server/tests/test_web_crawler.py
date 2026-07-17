import unittest
from unittest.mock import Mock, patch

from crawler.web_crawler import crawl_fallback, get_all_page_urls


class TestWebCrawler(unittest.TestCase):
    @patch("crawler.web_crawler.requests.get")
    def test_follows_sitemap_index(self, mock_get):
        sitemap_index = """
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
        </sitemapindex>
        """
        child_sitemap = """
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page-1</loc></url>
            <url><loc>https://example.com/page-2</loc></url>
        </urlset>
        """

        def response_for(url, **kwargs):
            response = Mock()
            response.raise_for_status.return_value = None
            response.text = (
                sitemap_index
                if url == "https://example.com/sitemap.xml"
                else child_sitemap
            )
            return response

        mock_get.side_effect = response_for

        urls = get_all_page_urls("https://example.com/sitemap.xml")

        self.assertEqual(
            urls,
            [
                "https://example.com/page-1",
                "https://example.com/page-2",
            ],
        )

    @patch("crawler.web_crawler.time.sleep")
    @patch("crawler.web_crawler.requests.get")
    def test_fallback_crawls_same_origin_links(self, mock_get, mock_sleep):
        home_html = """
        <html>
            <head><title>Home</title></head>
            <body>
                <main>
                    This is enough documentation content to exceed one hundred
                    characters for the fallback crawler test and be collected.
                    <a href="/guide">Guide</a>
                    <a href="https://other.example.com/external">External</a>
                </main>
            </body>
        </html>
        """
        guide_html = """
        <html>
            <head><title>Guide</title></head>
            <body>
                This guide also contains enough documentation content to exceed
                one hundred characters and be collected by the fallback crawler.
            </body>
        </html>
        """

        def response_for(url, **kwargs):
            response = Mock()
            response.raise_for_status.return_value = None
            response.text = (
                guide_html
                if url == "https://example.com/guide"
                else home_html
            )
            return response

        mock_get.side_effect = response_for

        docs = crawl_fallback("https://example.com", depth=2)

        self.assertEqual(
            [doc["url"] for doc in docs],
            [
                "https://example.com",
                "https://example.com/guide",
            ],
        )
        mock_sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
