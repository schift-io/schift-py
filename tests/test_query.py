from schift.buckets import BucketsModule
from schift.query import QueryModule


class FakeHttp:
    def __init__(self):
        self.calls = []

    def post(self, path, data=None):
        self.calls.append(("post", path, data))
        return {"results": []}

    def get(self, path, params=None):
        self.calls.append(("get", path, params))
        return []

    def _post_form_with_files(self, path, form_data, files):
        self.calls.append(("form", path, form_data, files))
        return {"jobs": []}


def test_query_prefers_bucket_search_endpoint():
    http = FakeHttp()
    query = QueryModule(http)

    query("hello", bucket="docs", top_k=3)

    assert http.calls == [
        ("post", "/buckets/docs/search", {"query": "hello", "top_k": 3}),
    ]


def test_query_keeps_collection_alias_for_bucket_search():
    http = FakeHttp()
    query = QueryModule(http)

    query("hello", collection="legacy-docs")

    assert http.calls[0][1] == "/buckets/legacy-docs/search"


def test_query_keeps_external_db_passthrough_shape():
    http = FakeHttp()
    query = QueryModule(http)

    query("hello", collection="legacy-docs", db="external")

    assert http.calls == [
        (
            "post",
            "/query",
            {
                "query": "hello",
                "top_k": 10,
                "collection": "legacy-docs",
                "db": "external",
            },
        ),
    ]


def test_bucket_upload_accepts_collection_id():
    http = FakeHttp()
    buckets = BucketsModule(http)
    files = [("files", ("doc.pdf", b"pdf", "application/pdf"))]

    buckets.upload("bucket_1", files, collection_id="collection_1")

    assert http.calls == [
        (
            "form",
            "/buckets/bucket_1/upload",
            {"collection_id": "collection_1"},
            files,
        ),
    ]


def test_bucket_collection_helpers_call_bucket_collection_endpoints():
    http = FakeHttp()
    buckets = BucketsModule(http)

    buckets.list_collections("bucket_1")
    buckets.create_collection("bucket_1", "support", description="Support docs")
    buckets.grant_collection_access(
        "bucket_1",
        "collection_1",
        subject_type="role",
        subject_id="support",
    )

    assert http.calls == [
        ("get", "/buckets/bucket_1/collections", None),
        (
            "post",
            "/buckets/bucket_1/collections",
            {"name": "support", "description": "Support docs"},
        ),
        (
            "post",
            "/buckets/bucket_1/collections/collection_1/grants",
            {
                "subject_type": "role",
                "subject_id": "support",
                "permission": "search",
            },
        ),
    ]
