"""System tests for complete development workflows without LLM involvement."""

import pytest

from kodx.tools import DockerCodexTools


@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.workflow
class TestWorkflows:
    """Test complete development workflows without LLM involvement."""

    @pytest.mark.asyncio
    async def test_python_development_workflow(self, docker_client):
        """Test complete Python development workflow."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Install required packages
            result = await tools.feed_chars("pip install requests")
            assert "Successfully installed" in result or "already satisfied" in result

            # Create a Python application
            app_code = (
                "import requests\nimport json\n\n"
                "def fetch_data(url):\n    \"\"\"Fetch data from a URL and return JSON.\"\"\"\n    try:\n        response = requests.get(url)\n        response.raise_for_status()\n        return response.json()\n    except requests.RequestException as e:\n        return {'error': str(e)}\n\n"
                "def main():\n    url = 'https://httpbin.org/get'\n    print('Fetching data from:', url)\n    data = fetch_data(url)\n    print('Response received:')\n    print(json.dumps(data, indent=2))\n    print('Application completed successfully!')\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
            tools.copy_text_to_container(app_code, "/workspace/web_app.py")

            # Create test file
            test_code = (
                "import unittest\nfrom unittest.mock import patch, Mock\nimport web_app\n\n"
                "class TestWebApp(unittest.TestCase):\n\n"
                "    @patch('web_app.requests.get')\n    def test_fetch_data_success(self, mock_get):\n        mock_response = Mock()\n        mock_response.json.return_value = {'status': 'ok'}\n        mock_response.raise_for_status.return_value = None\n        mock_get.return_value = mock_response\n        result = web_app.fetch_data('http://test.com')\n        self.assertEqual(result, {'status': 'ok'})\n\n"
                "    @patch('web_app.requests.get')\n    def test_fetch_data_error(self, mock_get):\n        mock_get.side_effect = web_app.requests.RequestException('Connection error')\n        result = web_app.fetch_data('http://test.com')\n        self.assertIn('error', result)\n        self.assertEqual(result['error'], 'Connection error')\n\n"
                "if __name__ == '__main__':\n    unittest.main()\n"
            )
            tools.copy_text_to_container(test_code, "/workspace/test_app.py")

            # Run tests
            result = await tools.feed_chars("python3 -m unittest test_app.py -v")
            assert "test_fetch_data_success" in result
            assert "test_fetch_data_error" in result
            assert "OK" in result or "PASSED" in result

            # Run the application
            result = await tools.feed_chars("python3 web_app.py")
            assert "Fetching data from:" in result
            assert "Response received:" in result
            assert "Application completed successfully!" in result

            # Verify files were created
            result = await tools.feed_chars("ls -la *.py")
            assert "web_app.py" in result
            assert "test_app.py" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_file_operations_workflow(self, docker_client):
        """Test comprehensive file operations workflow."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Create directory structure
            await tools.feed_chars("mkdir -p project/{src,tests,docs,data}")

            # Create source files
            main_code = (
                "#!/usr/bin/env python3\n"
                '"""Main application module."""\n\n'
                "def greet(name):\n    return f'Hello, {name}!'\n\n"
                "def main():\n    print(greet('World'))\n\n"
                "if __name__ == '__main__':\n    main()\n"
            )
            tools.copy_text_to_container(main_code, "/workspace/project/src/main.py")

            utils_code = (
                '"""Utility functions."""\n\n'
                "def add_numbers(a, b):\n    return a + b\n\n"
                "def multiply_numbers(a, b):\n    return a * b\n"
            )
            tools.copy_text_to_container(utils_code, "/workspace/project/src/utils.py")

            # Create test files
            test_code = (
                "import sys\nimport os\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n\n"
                "import main\n\n"
                "def test_greet():\n    result = main.greet('Test')\n    assert result == 'Hello, Test!'\n    print('test_greet: PASSED')\n\n"
                "if __name__ == '__main__':\n    test_greet()\n"
            )
            tools.copy_text_to_container(test_code, "/workspace/project/tests/test_main.py")

            # Create documentation
            readme = (
                "# Test Project\n\nThis is a test project for demonstrating file operations.\n\n"
                "## Structure\n- `src/`: Source code\n- `tests/`: Test files\n- `docs/`: Documentation\n- `data/`: Data files\n\n"
                "## Usage\n\nRun the main application:\n```\npython3 src/main.py\n```\n\nRun tests:\n```\npython3 tests/test_main.py\n```\n"
            )
            tools.copy_text_to_container(readme, "/workspace/project/README.md")

            # Create data file
            await tools.feed_chars("echo 'sample,data,file' > project/data/sample.csv")
            await tools.feed_chars("echo '1,2,3' >> project/data/sample.csv")
            await tools.feed_chars("echo '4,5,6' >> project/data/sample.csv")

            # Test the project structure
            result = await tools.feed_chars("find project -type f | sort")
            expected_files = ["project/README.md", "project/data/sample.csv", "project/src/main.py", "project/src/utils.py", "project/tests/test_main.py"]
            for expected_file in expected_files:
                assert expected_file in result

            # Test file permissions
            await tools.feed_chars("chmod +x project/src/main.py")
            result = await tools.feed_chars("ls -la project/src/main.py")
            assert "rwx" in result

            # Run the application
            result = await tools.feed_chars("cd project && python3 src/main.py")
            assert "Hello, World!" in result

            # Run tests
            result = await tools.feed_chars("cd project && python3 tests/test_main.py")
            assert "PASSED" in result

            # Test file content operations
            result = await tools.feed_chars("wc -l project/data/sample.csv")
            assert "3" in result  # Should have 3 lines

            result = await tools.feed_chars("cat project/data/sample.csv")
            assert "sample,data,file" in result
            assert "1,2,3" in result
            assert "4,5,6" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_package_management_workflow(self, docker_client):
        """Test package management and virtual environment workflow."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Install multiple packages
            packages = ["requests", "click", "pytest"]
            for package in packages:
                result = await tools.feed_chars(f"pip install {package}")
                assert "Successfully installed" in result or "already satisfied" in result

            # Verify all packages are installed
            result = await tools.feed_chars("pip list")
            for package in packages:
                assert package.lower() in result.lower()

            # Create requirements file
            await tools.feed_chars("pip freeze > requirements.txt")

            # Verify requirements file
            result = await tools.feed_chars("cat requirements.txt")
            for package in packages:
                assert package.lower() in result.lower()

            # Create a CLI application using installed packages
            cli_app = """#!/usr/bin/env python3
import click
import requests

@click.command()
@click.option('--url', default='https://httpbin.org/get', help='URL to fetch')
def fetch_url(url):
    '''Simple CLI tool to fetch a URL.'''
    try:
        response = requests.get(url)
        response.raise_for_status()
        click.echo(f"Status: {response.status_code}")
        click.echo(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        click.echo("Fetch successful!")
    except requests.RequestException as e:
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    fetch_url()
"""
            tools.copy_text_to_container(cli_app, "/workspace/cli_app.py")

            # Make it executable
            await tools.feed_chars("chmod +x cli_app.py")

            # Test the CLI application
            result = await tools.feed_chars("python3 cli_app.py --help")
            assert "Simple CLI tool" in result
            assert "--url" in result

            # Run the CLI application
            result = await tools.feed_chars("python3 cli_app.py")
            assert "Status: 200" in result
            assert "Fetch successful!" in result

            # Test package import verification
            for package in packages:
                result = await tools.feed_chars(f"python3 -c 'import {package}; print(\"{package} imported successfully\")'")
                assert f"{package} imported successfully" in result

        finally:
            await tools.cleanup()

    @pytest.mark.asyncio
    async def test_development_environment_setup(self, docker_client):
        """Test setting up a complete development environment."""
        tools = DockerCodexTools(container_image="python:3.11")

        try:
            await tools.initialize()

            # Install development tools
            dev_packages = ["black", "flake8", "mypy"]
            for package in dev_packages:
                result = await tools.feed_chars(f"pip install {package}")
                assert "Successfully installed" in result or "already satisfied" in result

            # Create a Python project with various code quality issues
            messy_code = (
                "import sys,os\nimport json\n\n"
                "def badly_formatted_function(x,y,z):\n    if x>y:\n        result=x*y+z\n    else:\n        result=y*z-x\n    return result\n\n"
                "class MyClass:\n    def __init__(self,name):\n        self.name=name\n\n    def get_info(self):\n        return f'Name: {self.name}'\n\n"
                "def unused_function():\n    pass\n\n"
                "# Long line that exceeds recommended length and should be split into multiple lines for better readability\nvery_long_variable_name_that_makes_the_line_too_long = 'This is a very long string that makes the line exceed the recommended length limit'\n\n"
                "if __name__=='__main__':\n    obj=MyClass('test')\n    print(obj.get_info())\n    result=badly_formatted_function(1,2,3)\n    print(f'Result: {result}')\n"
            )
            tools.copy_text_to_container(messy_code, "/workspace/messy_code.py")

            # Run code quality checks

            # Check with flake8 (style guide enforcement)
            result = await tools.feed_chars("flake8 messy_code.py")
            # Should find style issues (output will contain warnings/errors)

            # Format with black
            await tools.feed_chars("black messy_code.py")

            # Verify black formatted the code
            result = await tools.feed_chars("cat messy_code.py")
            # Should now have proper formatting
            assert "def badly_formatted_function(x, y, z):" in result  # Proper spacing
            assert "if x > y:" in result  # Proper operator spacing

            # Create a type-annotated version
            typed_code = (
                "from typing import Union\n\n"
                "def add_numbers(a: int, b: int) -> int:\n    return a + b\n\n"
                "def divide_numbers(a: float, b: float) -> Union[float, str]:\n    if b == 0:\n        return 'Cannot divide by zero'\n    return a / b\n\n"
                "class Calculator:\n    def __init__(self, precision: int = 2) -> None:\n        self.precision = precision\n\n"
                "    def format_result(self, value: float) -> str:\n        return f'{value:.{self.precision}f}'\n\n"
                "if __name__ == '__main__':\n    calc = Calculator()\n    result = add_numbers(10, 5)\n    print(f'Addition result: {calc.format_result(result)}')\n    division_result = divide_numbers(10.0, 3.0)\n    if isinstance(division_result, float):\n        print(f'Division result: {calc.format_result(division_result)}')\n    else:\n        print(f'Error: {division_result}')\n"
            )
            tools.copy_text_to_container(typed_code, "/workspace/typed_code.py")

            # Run mypy type checking
            result = await tools.feed_chars("mypy typed_code.py")
            # Should pass type checking or show minimal issues

            # Test the final code
            result = await tools.feed_chars("python3 typed_code.py")
            assert "Addition result:" in result
            assert "Division result:" in result

            # Create a simple test suite
            test_suite = (
                "import unittest\nfrom typed_code import add_numbers, divide_numbers, Calculator\n\n"
                "class TestCalculator(unittest.TestCase):\n\n"
                "    def test_add_numbers(self):\n        self.assertEqual(add_numbers(2, 3), 5)\n        self.assertEqual(add_numbers(-1, 1), 0)\n\n"
                "    def test_divide_numbers(self):\n        self.assertEqual(divide_numbers(10.0, 2.0), 5.0)\n        self.assertEqual(divide_numbers(10.0, 0.0), 'Cannot divide by zero')\n\n"
                "    def test_calculator_formatting(self):\n        calc = Calculator(precision=2)\n        self.assertEqual(calc.format_result(3.14159), '3.14')\n\n        calc_precise = Calculator(precision=4)\n        self.assertEqual(calc_precise.format_result(3.14159), '3.1416')\n\n"
                "if __name__ == '__main__':\n    unittest.main()\n"
            )
            tools.copy_text_to_container(test_suite, "/workspace/test_calculator.py")

            # Run the test suite
            result = await tools.feed_chars("python3 -m unittest test_calculator.py -v")
            assert "test_add_numbers" in result
            assert "test_divide_numbers" in result
            assert "test_calculator_formatting" in result
            assert "OK" in result or "PASSED" in result

        finally:
            await tools.cleanup()
