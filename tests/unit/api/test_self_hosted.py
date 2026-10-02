from apps.api.routes.self_hosted import _version_tuple


def test_self_hosted_version_parser() -> None:
    assert _version_tuple("v0.3.0") == (0, 3, 0)
    assert _version_tuple("1.2.3") == (1, 2, 3)


def test_invalid_version_is_not_ordered_as_release() -> None:
    assert _version_tuple("preview") == (0,)
