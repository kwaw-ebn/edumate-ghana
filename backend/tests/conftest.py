import pytest
@pytest.fixture(autouse=True)
def isolate_rate_limits():
    from app.main import rate
    rate.clear()
    yield
    rate.clear()
