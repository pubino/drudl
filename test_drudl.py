#!/usr/bin/env python3
"""Tests for Drupal downloader with mocks."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from drudl import DrupalDownloader, extra_http_headers


class TestExtraHttpHeaders(unittest.TestCase):
    """Header configuration, matching the convention bsp uses."""

    def setUp(self):
        self._saved = {
            key: os.environ.pop(key, None)
            for key in ("EXTRA_HTTP_HEADERS", "DRUDL_BYPASS_HEADER")
        }

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_no_configuration(self):
        self.assertEqual(extra_http_headers(), {})

    def test_blank_configuration(self):
        os.environ["EXTRA_HTTP_HEADERS"] = "   "
        self.assertEqual(extra_http_headers(), {})

    def test_json_object(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"x-wdsoit-bot-bypass": "true"}'
        self.assertEqual(extra_http_headers(), {"x-wdsoit-bot-bypass": "true"})

    def test_multiple_headers(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"a": "1", "b": "2"}'
        self.assertEqual(extra_http_headers(), {"a": "1", "b": "2"})

    def test_scalar_values_are_stringified(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"x-flag": true, "x-count": 3}'
        self.assertEqual(extra_http_headers(), {"x-flag": "True", "x-count": "3"})

    def test_non_scalar_values_dropped(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"good": "1", "bad": {"nested": true}}'
        self.assertEqual(extra_http_headers(), {"good": "1"})

    def test_invalid_json_ignored(self):
        os.environ["EXTRA_HTTP_HEADERS"] = "x-header: true"
        self.assertEqual(extra_http_headers(), {})

    def test_non_object_json_ignored(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '["x-header"]'
        self.assertEqual(extra_http_headers(), {})

    def test_legacy_single_header_still_works(self):
        os.environ["DRUDL_BYPASS_HEADER"] = "X-My-Header: true"
        self.assertEqual(extra_http_headers(), {"X-My-Header": "true"})

    def test_legacy_header_without_colon_ignored(self):
        os.environ["DRUDL_BYPASS_HEADER"] = "X-My-Header"
        self.assertEqual(extra_http_headers(), {})

    def test_legacy_value_may_contain_colons(self):
        os.environ["DRUDL_BYPASS_HEADER"] = "X-Url: https://example.com"
        self.assertEqual(extra_http_headers(), {"X-Url": "https://example.com"})

    def test_both_forms_combine(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"a": "1"}'
        os.environ["DRUDL_BYPASS_HEADER"] = "b: 2"
        self.assertEqual(extra_http_headers(), {"a": "1", "b": "2"})

    def test_headers_reach_the_session(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"x-wdsoit-bot-bypass": "true"}'
        downloader = DrupalDownloader("https://example.com", output_dir=tempfile.mkdtemp())
        self.assertEqual(downloader.session.headers["x-wdsoit-bot-bypass"], "true")

    def test_values_are_not_printed(self):
        os.environ["EXTRA_HTTP_HEADERS"] = '{"x-secret": "super-secret-value"}'
        with patch("builtins.print") as printed:
            extra_http_headers()
        logged = " ".join(str(call) for call in printed.call_args_list)
        self.assertIn("x-secret", logged)
        self.assertNotIn("super-secret-value", logged)


class TestDrupalDownloader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = DrupalDownloader(
            "https://example.com",
            output_dir=self.temp_dir
        )

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.downloader.base_url, "https://example.com")
        self.assertEqual(self.downloader.session.headers["User-Agent"],
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    def test_detect_cas_auth_in_url(self):
        """Test CAS detection via URL."""
        mock_response = MagicMock()
        mock_response.history = []
        mock_response.url = "https://cas.example.com/login"
        mock_response.status_code = 200
        mock_response.text = ""

        self.assertTrue(self.downloader.detect_cas_auth(mock_response))

    def test_detect_cas_auth_no_auth(self):
        """Test no CAS detection for normal page."""
        mock_response = MagicMock()
        mock_response.history = []
        mock_response.url = "https://example.com/admin/content"
        mock_response.status_code = 200
        mock_response.text = "<html><body>Content</body></html>"

        self.assertFalse(self.downloader.detect_cas_auth(mock_response))

    def test_detect_cas_auth_in_history(self):
        """Test CAS detection via redirect history."""
        redirect = MagicMock()
        redirect.url = "https://cas.university.edu/login"

        mock_response = MagicMock()
        mock_response.history = [redirect]
        mock_response.url = "https://example.com"
        mock_response.status_code = 200
        mock_response.text = ""

        self.assertTrue(self.downloader.detect_cas_auth(mock_response))

    @patch.object(DrupalDownloader, 'get_page')
    def test_enumerate_content(self, mock_get_page):
        """Test content enumeration from admin page."""
        html = """
        <html>
        <body>
        <table class="views-table">
            <tr>
                <td class="views-field-title">
                    <a href="/node/1">Page 1</a>
                </td>
            </tr>
            <tr>
                <td class="views-field-title">
                    <a href="/node/2">Page 2</a>
                </td>
            </tr>
        </table>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_get_page.return_value = mock_response

        urls = self.downloader.enumerate_content()

        self.assertEqual(len(urls), 2)
        self.assertIn("https://example.com/node/1", urls)
        self.assertIn("https://example.com/node/2", urls)

    @patch.object(DrupalDownloader, 'get_page')
    def test_enumerate_content_pagination(self, mock_get_page):
        """Test pagination handling."""
        page1_html = """
        <html>
        <body>
        <table class="views-table">
            <tr><td class="views-field-title"><a href="/node/1">Page 1</a></td></tr>
        </table>
        <li class="pager-next"><a href="/admin/content?page=1" rel="next">Next</a></li>
        </body>
        </html>
        """
        page2_html = """
        <html>
        <body>
        <table class="views-table">
            <tr><td class="views-field-title"><a href="/node/2">Page 2</a></td></tr>
        </table>
        </body>
        </html>
        """

        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.text = page1_html

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.text = page2_html

        mock_get_page.side_effect = [mock_response1, mock_response2]

        urls = self.downloader.enumerate_content()

        self.assertEqual(len(urls), 2)
        self.assertEqual(mock_get_page.call_count, 2)

    def test_save_page_converts_to_markdown(self):
        """Test saving HTML as markdown."""
        content = "<html><body><h1>Test</h1><p>Hello world</p></body></html>"
        url = "https://example.com/node/1"

        file_path = self.downloader.save_page(url, content)

        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.suffix == ".md")
        self.assertIn("Test", file_path.read_text())

    def test_save_page_creates_directories(self):
        """Test that save_page creates nested directories."""
        content = "<html><body>Test</body></html>"
        url = "https://example.com/sites/default/files/page"

        file_path = self.downloader.save_page(url, content)

        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.parent.exists())

    def test_external_links_filtered(self):
        """Test that external links are not included."""
        html = """
        <html>
        <body>
        <table class="views-table">
            <tr><td class="views-field-title"><a href="/node/1">Internal</a></td></tr>
            <tr><td class="views-field-title"><a href="https://other.com/page">External</a></td></tr>
        </table>
        </body>
        </html>
        """

        with patch.object(self.downloader, 'get_page') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html
            mock_get.return_value = mock_response

            urls = self.downloader.enumerate_content()

            self.assertEqual(len(urls), 1)
            self.assertIn("https://example.com/node/1", urls)

    def test_edit_links_skipped(self):
        """Test that edit/delete links are skipped."""
        html = """
        <html>
        <body>
        <table class="views-table">
            <tr>
                <td class="views-field-title"><a href="/node/1">View</a></td>
                <td><a href="/node/1/edit">Edit</a></td>
                <td><a href="/node/1/delete">Delete</a></td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch.object(self.downloader, 'get_page') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html
            mock_get.return_value = mock_response

            urls = self.downloader.enumerate_content()

            self.assertEqual(len(urls), 1)
            self.assertNotIn("https://example.com/node/1/edit", urls)


    @patch.dict(os.environ, {"DRUDL_BYPASS_HEADER": "X-Bypass-Token: my-secret-value"})
    def test_bypass_header_from_env(self):
        """Test that DRUDL_BYPASS_HEADER env var sets a custom header on the session."""
        downloader = DrupalDownloader("https://example.com", output_dir=self.temp_dir)
        self.assertEqual(downloader.session.headers["X-Bypass-Token"], "my-secret-value")

    @patch.dict(os.environ, {"DRUDL_BYPASS_HEADER": ""})
    def test_bypass_header_empty(self):
        """Test that empty DRUDL_BYPASS_HEADER is ignored."""
        downloader = DrupalDownloader("https://example.com", output_dir=self.temp_dir)
        self.assertNotIn("X-Bypass-Token", downloader.session.headers)

    @patch.dict(os.environ, {}, clear=False)
    def test_bypass_header_unset(self):
        """Test that missing DRUDL_BYPASS_HEADER is ignored."""
        os.environ.pop("DRUDL_BYPASS_HEADER", None)
        downloader = DrupalDownloader("https://example.com", output_dir=self.temp_dir)
        # Should have only the default headers
        self.assertIn("User-Agent", downloader.session.headers)


if __name__ == "__main__":
    unittest.main()
