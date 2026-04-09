import typer
from commands import deploy, status, validate, destroy

app = typer.Typer()

app.add_typer(deploy.app, name="deploy")
app.add_typer(status.app, name="status")
app.add_typer(validate.app, name="validate")

if __name__ == "__main__":
    app()