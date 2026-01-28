"""Test San Antonio Open Data (CKAN) Building Permits dataset."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    base_url = "https://data.sanantonio.gov"
    dataset_name = "building-permits"

    # Fetch dataset metadata
    pkg_url = f"{base_url}/api/3/action/package_show?{urllib.parse.urlencode({'id': dataset_name})}"
    pkg = _get_json(pkg_url)
    if not pkg.get("success"):
        raise RuntimeError("Failed to load CKAN dataset metadata")

    resources = pkg.get("result", {}).get("resources", [])
    print(f"Found {len(resources)} resources for {dataset_name}")

    # Print resource list
    for res in resources:
        print(f"- {res.get('name')} | id={res.get('id')} | format={res.get('format')}")

    # Pick the first datastore-backed resource
    datastore_resource = next((r for r in resources if r.get("datastore_active")), None)
    if not datastore_resource:
        print("No datastore-backed resource found.")
        return

    resource_id = datastore_resource["id"]
    print(f"\nUsing datastore resource: {datastore_resource.get('name')} ({resource_id})")

    # Fetch sample records
    data_url = f"{base_url}/api/3/action/datastore_search?{urllib.parse.urlencode({'resource_id': resource_id, 'limit': 5})}"
    data = _get_json(data_url)
    if not data.get("success"):
        raise RuntimeError("Failed to fetch CKAN records")

    records = data.get("result", {}).get("records", [])
    fields = data.get("result", {}).get("fields", [])
    print(f"Fields: {[f.get('id') for f in fields]}")
    print("\nSample records:")
    for rec in records:
        print(rec)


if __name__ == "__main__":
    main()
