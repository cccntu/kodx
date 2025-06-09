"""Tests for Docker configuration feature."""

import pytest
from pydantic import ValidationError

from kodx.models import DockerConfig


def test_docker_config_defaults():
    """Test DockerConfig with default values."""
    config = DockerConfig()
    assert config.image == "python:3.11"
    assert config.setup_script is None


def test_docker_config_custom_values():
    """Test DockerConfig with custom values."""
    config = DockerConfig(
        image="python:3.12-slim",
        setup_script="#!/bin/bash\necho 'Hello'",
    )
    assert config.image == "python:3.12-slim"
    assert config.setup_script == "#!/bin/bash\necho 'Hello'"


def test_docker_config_from_dict():
    """Test DockerConfig created from a dictionary."""
    docker_dict = {
        "image": "node:20",
        "setup_script": "#!/bin/bash\nnpm install",
    }
    config = DockerConfig(**docker_dict)
    assert config.image == "node:20"
    assert config.setup_script == "#!/bin/bash\nnpm install"


def test_docker_config_unknown_fields():
    """Test DockerConfig rejects unknown fields."""
    docker_dict = {
        "image": "python:3.11",
        "unknown_field": "value",
    }
    with pytest.raises(ValidationError):
        DockerConfig(**docker_dict)


# Note: The following test requires integration with Click CLI
# and would be part of integration tests rather than unit tests
'''
def test_cli_setup_script_option():
    """Test that --setup-script CLI option works and takes precedence."""
    # This would be an integration test that verifies:
    # 1. --setup-script is accepted as a CLI option
    # 2. --setup-script takes precedence over docker.setup_script in YAML
    pass
'''
