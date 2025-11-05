import typer
from queuectl import cli

# The main app is now the cli app directly
app = cli.app

if __name__ == "__main__":
    app()
