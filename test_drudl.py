#!/usr/bin/env python3
"""Tests for Drupal downloader with mocks."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from drudl import DrupalDownloader


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


if __name__ == "__main__":
    unittest.main()
