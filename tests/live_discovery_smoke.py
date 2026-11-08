"""Opt-in public-feed smoke probe; excluded from normal offline discovery."""
import json
import os
import unittest

from content_machine.workflow.safe_rss import fetch


@unittest.skipUnless(os.environ.get('CONTENT_MACHINE_LIVE_DISCOVERY') == '1', 'Live public-feed probe is opt-in')
class LiveDiscoverySmoke(unittest.TestCase):
    def test_supervised_public_feed(self):
        source = {'source_id': 'public-smoke', 'name': 'Public engineering feed', 'kind': 'rss',
                  'url': os.environ.get('CONTENT_MACHINE_LIVE_DISCOVERY_URL', 'https://hnrss.org/newest?count=1')}
        result = fetch(source)
        self.assertTrue(result.items, 'The public feed returned no usable items')
        self.assertTrue(all(item.url.startswith(('https://', 'http://')) and item.title for item in result.items))
        print(json.dumps({'source_url': source['url'], 'items': len(result.items),
            'first_title': result.items[0].title, 'first_url': result.items[0].url,
            'fetched_at': result.items[0].fetched_at.isoformat()}, ensure_ascii=True))
