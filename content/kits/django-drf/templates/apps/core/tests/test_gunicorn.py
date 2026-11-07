from config import gunicorn


def test_gunicorn_logs_json_through_the_app_logging_config() -> None:
    config = gunicorn.logconfig_dict

    assert config["formatters"]["json"] == {"()": "apps.core.logging.json_formatter"}
    assert config["root"]["handlers"] == ["stdout"]


def test_gunicorn_own_lines_use_the_json_handler() -> None:
    error = gunicorn.logconfig_dict["loggers"]["gunicorn.error"]

    assert error["handlers"] == ["stdout"]
    assert error["propagate"] is False


def test_gunicorn_leaves_request_logging_to_the_middleware() -> None:
    access = gunicorn.logconfig_dict["loggers"]["gunicorn.access"]

    assert access["handlers"] == []
    assert access["level"] == "WARNING"


def test_gunicorn_serves_the_container_port_behind_the_platform_proxy() -> None:
    assert gunicorn.bind == "0.0.0.0:8000"
    assert gunicorn.forwarded_allow_ips == "*"
