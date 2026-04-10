from importlib import import_module


def test_backend_skeleton_modules_are_importable():
    main = import_module("app.main")
    database = import_module("app.database")
    models = import_module("app.models")
    schemas = import_module("app.schemas")

    assert main.app.title == "国际遗产观察 Web API"
    assert database.Base.__name__ == "Base"
    assert hasattr(models, "User")
    assert hasattr(models, "Conversation")
    assert hasattr(models, "Message")
    assert hasattr(models, "LoginCode")
    assert hasattr(schemas, "HealthResponse")
