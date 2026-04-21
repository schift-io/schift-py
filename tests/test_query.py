from schift.query import QueryModule


class FakeHttp:
    def __init__(self):
        self.calls = []

    def post(self, path, data=None):
        self.calls.append((path, data))
        return {"results": []}


def test_query_prefers_bucket_search_endpoint():
    http = FakeHttp()
    query = QueryModule(http)

    query("hello", bucket="docs", top_k=3)

    assert http.calls == [
        ("/buckets/docs/search", {"query": "hello", "top_k": 3}),
    ]


def test_query_keeps_collection_alias_for_bucket_search():
    http = FakeHttp()
    query = QueryModule(http)

    query("hello", collection="legacy-docs")

    assert http.calls[0][0] == "/buckets/legacy-docs/search"


def test_query_keeps_external_db_passthrough_shape():
    http = FakeHttp()
    query = QueryModule(http)

    query("hello", collection="legacy-docs", db="external")

    assert http.calls == [
        (
            "/query",
            {
                "query": "hello",
                "top_k": 10,
                "collection": "legacy-docs",
                "db": "external",
            },
        ),
    ]
