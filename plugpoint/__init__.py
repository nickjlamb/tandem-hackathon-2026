"""PlugPoint - closes the loop after outpatient clinic. See README.md."""

try:  # load ANTHROPIC_API_KEY etc. from .env if present
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass
