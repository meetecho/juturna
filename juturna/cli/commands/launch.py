"""
Pipeline runner module

Execute a pipeline from the CLI. Provide the pipeline configuration file and
the way it should be launched:

- automatic mode is set by passing `auto`, so the launcher will automatically
  launch the pipeline after creation, and will then either wait for the number
  of seconds provided in `timeout` before stopping the pipeline, or run it
  indefinitely
- manual mode will wait for the user to press enter in order to start and stop
  the pipeline execution
- passing `dry-gin` to the launcher will only instantiate the pipeline, thus
  creating all the nodes and fetching all their resources, without running the
  pipeline
"""

import time

import juturna as jt

from juturna.cli.commands import _common_pipe_parser


def setup_parser(subparsers):  # noqa: D103
    common_parser = _common_pipe_parser.common_parser()
    parser = subparsers.add_parser(
        'launch',
        parents=[common_parser],
        help='instantiate and run the pipeline in the configuration file',
    )

    parser.add_argument(
        '--auto',
        '-a',
        action='store_true',
        help='start/stop pipeline automatically without prompting the user',
    )

    parser.add_argument(
        '--timeout',
        '-t',
        type=int,
        default=0,
        help='pipeline execution time (in seconds)',
    )

    parser.add_argument(
        '--dry-gin',
        '-d',
        action='store_true',
        help='Graph Instance oNly, do not execute the pipeline',
    )


def _execute(args) -> int:
    jt.utils.log_utils.jt_logger().setLevel(args.log_level)

    pipeline = jt.components.Pipeline.from_json(args.config)

    pipeline.warmup()

    if args.dry_gin:
        pipeline.destroy()

        return 0

    if not args.auto:
        _ = input('pipeline warmed up, press enter to start...')

    pipeline.start()

    if not args.auto:
        _ = input('pipeline running, press enter to stop...\n')

        pipeline.stop()
        pipeline.destroy()

        return 0

    if args.timeout > 0:
        time.sleep(args.timeout)

        pipeline.stop()
        pipeline.destroy()

        return 0

    while True:
        time.sleep(60)
