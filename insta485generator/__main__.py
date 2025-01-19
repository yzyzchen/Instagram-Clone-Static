"""Build static HTML site from directory of HTML templates and plain files."""
import sys
import json
import pathlib
import shutil

import click
import jinja2


def validate_output_path(output_root):
    """Check if output directory exists."""
    if output_root.exists():
        click.echo("Path already exists")
        sys.exit(1)


def configure_environment(input_path):
    """Configure Jinja2 environment."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(input_path / "templates")),
        autoescape=jinja2.select_autoescape(['html', 'xml']),
        # Automatically escapes certain characters (e.g., <, >, &)
    )


def load_config(config_path):
    """Load configuration file."""
    try:
        with config_path.open() as json_file:
            # config_filename is open within this code block
            return json.load(json_file)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            (
                f"'{config_path}'\n"
                f"{e.msg} (line {e.lineno} column {e.colno})"
            ),
            e.doc,
            e.pos
        )


def copy_static_files(static_path, output_root, verbose):
    """Copy static files."""
    if static_path.exists():
        try:
            shutil.copytree(
                str(static_path),
                str(output_root),
                dirs_exist_ok=True
            )
            if verbose:
                click.echo(f"Copied {static_path} -> {output_root}")
        except OSError as e:
            click.echo(f"Error copying static files: {e}")
            sys.exit(1)


def render_templates(data, env, output_root, verbose):
    """Render templates and save output."""
    for key in data:
        url = key["url"].lstrip("/")
        # this will load as a template object
        try:
            template = env.get_template(key["template"].lstrip("/"))
        except jinja2.exceptions.TemplateNotFound as e:
            raise FileNotFoundError(f"'{key['template']}' not found.") from e
        except jinja2.exceptions.TemplateSyntaxError as e:
            raise jinja2.exceptions.TemplateSyntaxError(
                f"'{key['template']}'\n{e.message}", e.filename, e.lineno
            )
        # Render HTML
        try:
            rendered_html = template.render(key["context"])
        except jinja2.exceptions.TemplateError as e:
            raise jinja2.exceptions.TemplateError(
                f"Error rendering template '{key['template']}': {e}"
            )
        # Save rendered output
        output_file = output_root / url / "index.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w") as f:
            f.write(rendered_html)
        # Optional verbose output
        if verbose:
            click.echo(f"Rendered {key['template']} -> {output_file}")


@click.command()
@click.argument("input_dir", nargs=1, type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory.")
@click.option("-v", "--verbose", is_flag=True, help="Print more output.")
def main(input_dir, output, verbose):
    """Templated static website generator."""
    input_path = pathlib.Path(input_dir)

    # check if output available
    output_root = (
        input_path / "html"
        if output is None
        else pathlib.Path(output)
    )
    try:
        validate_output_path(output_root)

        # Configure Jinja2 environment
        env = configure_environment(input_path)

        # Load configuration file
        data = load_config(input_path / "config.json")

        output_root.mkdir(parents=True, exist_ok=True)

        # Copy static files
        copy_static_files(input_path / "static", output_root, verbose)

        # Render templates and save output
        render_templates(data, env, output_root, verbose)

    except (FileNotFoundError, FileExistsError, json.JSONDecodeError,
            jinja2.exceptions.TemplateError, OSError) as e:
        click.echo(f"insta485generator error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
