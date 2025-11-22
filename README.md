# drudl

A command-line tool for downloading Drupal site content with CAS authentication support. Enumerates content via `/admin/content` and converts pages to Markdown.

## Features

- **CAS Authentication**: Automatically detects CAS authentication and opens a browser for interactive login
- **Content Enumeration**: Paginates through `/admin/content` to find all site content
- **Markdown Conversion**: Converts HTML pages to clean Markdown format
- **Section Trimming**: Configurable removal of navigation, menus, and other boilerplate sections
- **Progress Indicator**: Visual progress bar during download
- **Safety First**: Filters out dangerous action links (edit, delete, replicate, etc.)

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/drudl.git
cd drudl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- Chrome browser (for Selenium-based authentication)

## Usage

### Basic Usage

```bash
python drudl https://your-drupal-site.com -o output_directory
```

### With Section Trimming

Remove specific sections from the downloaded Markdown:

```bash
# Using individual flags
python drudl https://example.com \
  --trim-section "## Footer" \
  --trim-section "## Main Menu" \
  --trim-section "## Sidebar"

# Using a file
python drudl https://example.com --trim-file trim_sections.txt
```

### Trim File Format

Create a text file with one section name per line (matches any heading level):

```
# Comments start with hash
Footer
Main Menu
Navigation
Sidebar
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `url` | Base URL of the Drupal site (required) |
| `-o, --output` | Output directory (default: `downloaded_site`) |
| `--trim-section` | Markdown header to remove (can be used multiple times) |
| `--trim-file` | File containing headers to trim, one per line |

## How It Works

1. **Connection Test**: Verifies the site is accessible
2. **Authentication**: If CAS authentication is detected, opens Chrome for interactive login
3. **Cookie Transfer**: Transfers authenticated session cookies from browser to requests
4. **Enumeration**: Paginates through `/admin/content` to collect all content URLs
5. **Download**: Fetches each page, converts to Markdown, and saves to output directory

## Permissions Required

The authenticated user must have permission to access `/admin/content`. This typically requires:

- "Administer content" permission, or
- "Access content overview" permission

## Security Notes

- The script only makes GET requests (never POST/DELETE)
- Dangerous action URLs are filtered out (edit, delete, replicate, unpublish, etc.)
- Uses a standard browser User-Agent to avoid bot detection
- Session cookies are stored in memory only (not persisted to disk)

## Running Tests

```bash
source venv/bin/activate
python -m pytest test_drudl.py -v
```

### Docker

```bash
docker build -t drudl .
docker run drudl
```

## License

MIT License - see [LICENSE.md](LICENSE.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
