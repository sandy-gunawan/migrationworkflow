import pytest

from demo_common.endpoints import require_demo_app_url


@pytest.mark.parametrize(
    "url",
    [
        "https://existing.azurewebsites.net",
        "https://kppdemo-data-48254cc6.evil.example",
        "https://kppdemo-data-48254cc6.azurewebsites.net@evil.example",
        "https://kppdemo-data-48254cc6.azurewebsites.net/api/private",
        "http://kppdemo-data-48254cc6.azurewebsites.net",
    ],
)
def test_dependency_cannot_be_redirected_to_existing_or_untrusted_data(url):
    with pytest.raises(ValueError, match="non-demo"):
        require_demo_app_url(url, "kppdemo-data-48254cc6")
