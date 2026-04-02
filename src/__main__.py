"""Entry point: python -m src"""

import sys

# If no subcommand given, launch interactive mode
if len(sys.argv) == 1:
    from src.interactive import main
    main()
else:
    from src.cli import cli
    cli()
