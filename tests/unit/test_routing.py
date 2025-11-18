from core.router import Router


def test_router_default():
    r = Router()
    assert hasattr(r, "route")


def test_router_hybrid_mode():
    r = Router()
    res = r.route("Find me the summary of AI safety")
    assert isinstance(res, dict)
