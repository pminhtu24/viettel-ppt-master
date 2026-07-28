import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.image_sources.provider_common import (
    LICENSE_TIER_ATTRIBUTION_REQUIRED,
    classify_license,
    detect_image_extension,
    download_image,
)


class ImageDownloadTest(unittest.TestCase):
    def test_cc_by_requires_attribution(self):
        self.assertEqual(
            classify_license("CC BY 4.0"),
            LICENSE_TIER_ATTRIBUTION_REQUIRED,
        )

    def test_download_png_without_network(self):
        payload = b"\x89PNG\r\n\x1a\npayload"
        response = Mock(content=payload, headers={"Content-Type": "image/png"})
        response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "image.png"
            with patch("scripts.image_sources.provider_common.requests.get", return_value=response):
                self.assertEqual(download_image("https://example.test/image", str(target)), str(target))
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(detect_image_extension(payload), ".png")


if __name__ == "__main__":
    unittest.main()
